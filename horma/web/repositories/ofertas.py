"""Único lugar donde se escribe SQL sobre ofertas y su origen. El catálogo se escribe en modo sistema."""
import json
import re

from pydantic import HttpUrl, TypeAdapter, ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from horma.schemas.oferta import Auditoria, Oferta, Salario
from horma.schemas.taxonomia import Taxonomia
from horma.tools.normalizar import huella
from horma.tools.normalizar_oferta import normalizar_oferta
from horma.tools.normalizar_titulo import normalizar_titulo, variantes_genero

COLUMNAS_LISTA = (
    "o.id, o.estado, o.motivo_error, o.titulo, o.empresa, o.ubicacion, o.remoto, o.modalidad, o.contrato, "
    "o.salario_minimo, o.salario_maximo, o.salario_moneda, o.idiomas, o.fecha_publicacion, o.url, "
    "o.instrucciones_embebidas, o.fantasma, o.motivos_fantasma, o.fraude, o.senales_fraude, "
    "o.dominio_empresa, o.empresa_validada, o.salario_publicado, o.salario_rango, "
    "o.frase_pedir_salario, o.sector, o.familia, o.nivel, o.stack, o.recomendable, o.creada_en, "
    "o.usuaria_id is not null as propia, f.nombre as fuente")


def _dominio(url: str | None) -> str | None:
    m = re.match(r"https?://([^/:?#]+)", url or "", re.I)
    return re.sub(r"^www\.", "", m.group(1).lower()) if m else None


def marcar_fuente_desconocida(filas: list[dict], s_sistema: Session) -> list[dict]:
    """RF-8.3f: una oferta propia es de «fuente no reconocida» si su dirección no es de ninguna fuente del
    banco de Horma (dominio o subdominio) o si no tiene dirección. `fuentes` solo la lee el sistema."""
    dominios = {d for (w,) in s_sistema.execute(text("select web from fuentes")).all() if (d := _dominio(w))}
    for f in filas:
        d = _dominio(f.get("url"))
        f["fuente_desconocida"] = bool(f.get("propia")) and not (
            d and any(d == x or d.endswith("." + x) for x in dominios))
    return filas


def _existente(s: Session, fuente_id, clave_id, id_externo) -> dict | None:
    if not id_externo or not (fuente_id or clave_id):
        return None
    if fuente_id:
        sql = "select id, estado from ofertas where fuente_id=:f and id_externo=:e"
    else:
        sql = "select id, estado from ofertas where fuente_id is null and clave_id=:c and id_externo=:e"
    fila = s.execute(text(sql), {"f": fuente_id, "c": clave_id, "e": id_externo}).mappings().first()
    return dict(fila) if fila else None


def _propia_igual(s: Session, usuaria_id: int, texto: str) -> dict | None:
    """Oferta propia de esa usuaria con el mismo texto (por huella). Una que falló no cuenta: se reintenta."""
    fila = s.execute(text("select id, estado from ofertas where usuaria_id=:u and huella=:h "
                          "and estado <> 'error' order by id limit 1"),
                     {"u": usuaria_id, "h": huella(texto)}).mappings().first()
    return dict(fila) if fila else None


def propias_con_url(s: Session, usuaria_id: int) -> list[dict]:
    """Las ofertas propias que tienen dirección (para reconocer una URL ya añadida, RF-11.29)."""
    return [dict(r) for r in s.execute(text(
        "select id, url, titulo, creada_en from ofertas where usuaria_id=:u and url is not null order by id"),
        {"u": usuaria_id}).mappings()]


def actualizar_texto(s: Session, oferta_id: int, texto: str) -> None:
    """Una relectura trajo otro texto: se vuelve a analizar, sin su análisis ni sus notas (RF-11.29)."""
    s.execute(text("update ofertas set texto_crudo=:t, huella=:h, estado='pendiente', motivo_error=null "
                   "where id=:i"), {"t": texto, "h": huella(texto), "i": oferta_id})


def borrar_notas(s: Session, oferta_id: int) -> None:
    """Las notas de compatibilidad de una oferta propia (sesión suya: la RLS de `matches` es suya)."""
    s.execute(text("delete from matches where oferta_id=:i"), {"i": oferta_id})


def huella_y_estado_propia(s: Session, oferta_id: int, usuaria_id: int) -> tuple[str, str] | None:
    """(huella, estado) de la oferta propia, o None si no existe o no es suya."""
    fila = s.execute(text("select huella, estado from ofertas where id=:i and usuaria_id=:u"),
                     {"i": oferta_id, "u": usuaria_id}).first()
    return (fila[0], fila[1]) if fila else None


def crear(s: Session, texto: str, *, fuente_id: int | None = None, clave_id: int | None = None,
          id_externo: str | None = None, url: str | None = None,
          usuaria_id: int | None = None, caduca_en=None,
          atribucion: str | None = None) -> tuple[int, str, bool]:
    """Guarda la oferta cruda. Devuelve (id, estado, nueva); idempotente por origen + id_externo."""
    if (previa := _existente(s, fuente_id, clave_id, id_externo)):
        return previa["id"], previa["estado"], False
    if usuaria_id is not None and (previa := _propia_igual(s, usuaria_id, texto)):
        return previa["id"], previa["estado"], False  # la misma oferta pegada otra vez: no se duplica
    try:
        with s.begin_nested():
            oid = s.execute(text(
                "insert into ofertas (texto_crudo, fuente_id, clave_id, id_externo, url, huella, usuaria_id, "
                "caduca_en, atribucion) values (:t, :f, :c, :e, :u, :h, :d, :x, :a) returning id"),
                {"t": texto, "f": fuente_id, "c": clave_id, "e": id_externo, "u": url,
                 "h": huella(texto), "d": usuaria_id, "x": caduca_en, "a": atribucion}).scalar_one()
    except IntegrityError:  # otra petición la insertó a la vez
        previa = _existente(s, fuente_id, clave_id, id_externo)
        return previa["id"], previa["estado"], False
    return oid, "pendiente", True


def borrar_caducadas(s: Session) -> int:
    """Borra del catálogo las ofertas cuya fuente las da por caducadas (RF-5.5d, Himalayas), con sus
    notas. Se conservan las que ya tienen una candidatura: son trabajo de una usuaria."""
    ids = ("(select id from ofertas o where usuaria_id is null and caduca_en < now() and not exists "
           "(select 1 from candidaturas c where c.oferta_id = o.id))")
    s.execute(text(f"delete from matches where oferta_id in {ids}"))
    return s.execute(text(f"delete from ofertas where id in {ids}")).rowcount


def para_procesar(s: Session, oferta_id: int) -> dict:
    """Lo que necesita el flujo: texto, fuente, url y si el mismo texto ya entró antes. Solo cuenta
    dentro de la misma dueña (o dentro del catálogo común): la oferta de otra usuaria no la hace repetida."""
    fila = s.execute(text(
        "select o.texto_crudo, o.url, f.nombre as fuente, o.usuaria_id is not null as propia, "
        "exists(select 1 from ofertas p "
        "where p.huella = o.huella and p.id < o.id "
        "and p.usuaria_id is not distinct from o.usuaria_id) as repetida "
        "from ofertas o left join fuentes f on f.id = o.fuente_id where o.id=:i"),
        {"i": oferta_id}).mappings().one()
    return {"texto": fila["texto_crudo"], "url": fila["url"], "fuente": fila["fuente"],
            "repetida": fila["repetida"], "propia": fila["propia"]}


def guardar(s: Session, oferta_id: int, o: Oferta, origenes: list[tuple[str, str]]) -> None:
    sal, a, t = o.salario, o.auditoria, o.taxonomia
    j = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731
    texto = s.execute(text("select texto_crudo from ofertas where id=:i"), {"i": oferta_id}).scalar_one()
    n = normalizar_oferta(o, texto)  # país, contrato, idiomas y sueldo anual para filtrar (P16)
    s.execute(text(
        "update ofertas set estado='procesada', motivo_error=null, procesada_en=now(), "
        "titulo=:titulo, empresa=:empresa, ubicacion=:ubicacion, remoto=:remoto, modalidad=:modalidad, "
        "contrato=:contrato, salario_minimo=:smin, salario_maximo=:smax, salario_moneda=:smon, "
        "idiomas=cast(:idiomas as jsonb), requisitos=cast(:req as jsonb), fecha_publicacion=:fecha, "
        "url=coalesce(:url, url), instrucciones_embebidas=cast(:instr as jsonb), "
        "fantasma=:fantasma, motivos_fantasma=cast(:motivos as jsonb), fraude=:fraude, "
        "senales_fraude=cast(:senales as jsonb), dominio_empresa=:dominio, "
        "empresa_validada=:validada, salario_publicado=:publicado, salario_rango=:rango, "
        "frase_pedir_salario=:frase, sector=:sector, familia=:familia, nivel=:nivel, "
        "stack=cast(:stack as jsonb), pais=:pais, tipo_contrato=:tcontrato, "
        "idiomas_norm=cast(:idiomas_norm as text[]), salario_anual_eur_min=:anual_min, "
        "salario_anual_eur_max=:anual_max, titulo_norm=:titulo_norm where id=:id"),
        {"id": oferta_id, "titulo": o.titulo, "empresa": o.empresa, "ubicacion": o.ubicacion,
         "remoto": o.remoto, "modalidad": o.modalidad,
         "contrato": o.contrato, "smin": sal.minimo if sal else None,
         "smax": sal.maximo if sal else None, "smon": sal.moneda if sal else None,
         "idiomas": j(o.idiomas), "req": j(o.requisitos), "fecha": o.fecha_publicacion,
         "url": str(o.url) if o.url else None, "instr": j(o.instrucciones_embebidas),
         "fantasma": a.fantasma, "motivos": j(a.motivos_fantasma), "fraude": a.fraude,
         "senales": j(a.senales_fraude), "dominio": a.dominio_empresa,
         "validada": a.empresa_validada, "publicado": a.salario_publicado, "rango": a.salario_rango,
         "frase": a.frase_pedir_salario, "sector": t.sector, "familia": t.familia,
         "nivel": t.nivel, "stack": j(t.stack), "pais": n.pais, "tcontrato": n.tipo_contrato,
         "idiomas_norm": n.idiomas, "anual_min": n.salario_anual_eur_min,
         "anual_max": n.salario_anual_eur_max,
         "titulo_norm": normalizar_titulo(o.titulo)})
    s.execute(text("delete from origen where entidad='oferta' and entidad_id=:i and usuaria_id is null"),
              {"i": oferta_id})
    for campo, fragmento in origenes:
        s.execute(text("insert into origen (entidad, entidad_id, campo, fragmento) "
                       "values ('oferta', :i, :c, :f)"),
                  {"i": oferta_id, "c": campo, "f": fragmento})


_GRUPOS = {"familias": "familia", "sectores": "sector", "niveles": "nivel", "contratos": "tipo_contrato",
           "paises": "pais"}
_BASE = "from ofertas where estado = 'procesada' and recomendable"


def contadores(s: Session) -> tuple[int, dict[str, dict[str, int]]]:
    """Cuántas ofertas recomendables hay en total y por valor de cada filtro (las casillas)."""
    total = s.execute(text(f"select count(*) {_BASE}")).scalar_one()
    grupos: dict[str, dict[str, int]] = {}
    for grupo, columna in _GRUPOS.items():
        filas = s.execute(text(f"select {columna}, count(*) {_BASE} and {columna} is not null "
                               f"group by {columna}")).all()
        grupos[grupo] = {v: n for v, n in filas}
    filas = s.execute(text(f"select i, count(*) from (select unnest(idiomas_norm) as i {_BASE}) t "
                           "group by i")).all()
    grupos["idiomas"] = {v: n for v, n in filas}
    return total, grupos


def contar_por_puesto(s: Session, titulos: list[str]) -> dict[str, int]:
    """Cuántas ofertas recomendables casan con cada puesto (frase completa del título, RF-9.3d)."""
    cuentas = {}
    for t in titulos:
        norm = normalizar_titulo(t)
        cuentas[t] = 0 if not norm else s.execute(text(
            f"select count(*) {_BASE} and (' ' || coalesce(titulo_norm, '') || ' ') like any(:p)"),
            {"p": [f"% {v} %" for v in variantes_genero(norm)]}).scalar_one()
    return cuentas


def titulos_que_contienen(s: Session, q: str, limite: int = 8) -> list[str]:
    """Títulos de ofertas recomendables que contienen lo escrito, los más frecuentes primero.

    Sirve para autocompletar.
    """
    norm = normalizar_titulo(q)
    if not norm:
        return []
    filas = s.execute(text(
        f"select min(titulo) t, count(*) n {_BASE} and titulo is not null "
        "and (' ' || coalesce(titulo_norm, '') || ' ') like :p group by titulo_norm "
        "order by n desc, t limit :l"), {"p": f"%{norm}%", "l": limite}).all()
    return [f[0] for f in filas]


def _url_valida(url: str | None) -> str | None:
    try:
        return str(TypeAdapter(HttpUrl).validate_python(url)) if url else None
    except ValidationError:
        return None


def completas(s: Session, ids: list[int]) -> dict[int, Oferta]:
    """Las ofertas procesadas con ese id, como `Oferta` (para el matcher)."""
    if not ids:
        return {}
    filas = s.execute(text(
        "select id, titulo, empresa, ubicacion, remoto, modalidad, contrato, salario_minimo, salario_maximo, "
        "salario_moneda, idiomas, requisitos, fecha_publicacion, url, instrucciones_embebidas, "
        "fantasma, motivos_fantasma, fraude, senales_fraude, dominio_empresa, empresa_validada, "
        "salario_publicado, salario_rango, frase_pedir_salario, sector, familia, nivel, stack "
        "from ofertas where estado = 'procesada' and id = any(cast(:ids as int[]))"),
        {"ids": list(ids)}).mappings().all()
    salida: dict[int, Oferta] = {}
    for f in filas:
        salario = None
        if f["salario_minimo"] is not None or f["salario_maximo"] is not None:
            salario = Salario(
                minimo=None if f["salario_minimo"] is None else float(f["salario_minimo"]),
                maximo=None if f["salario_maximo"] is None else float(f["salario_maximo"]),
                moneda=f["salario_moneda"])
        salida[f["id"]] = Oferta(
            titulo=f["titulo"] or "sin título", empresa=f["empresa"], ubicacion=f["ubicacion"],
            remoto=f["remoto"], modalidad=f["modalidad"], contrato=f["contrato"], salario=salario,
            idiomas=f["idiomas"],
            requisitos=f["requisitos"], fecha_publicacion=f["fecha_publicacion"],
            url=_url_valida(f["url"]), instrucciones_embebidas=f["instrucciones_embebidas"],
            auditoria=Auditoria(
                fantasma=bool(f["fantasma"]), motivos_fantasma=f["motivos_fantasma"],
                fraude=bool(f["fraude"]), senales_fraude=f["senales_fraude"],
                dominio_empresa=f["dominio_empresa"], empresa_validada=f["empresa_validada"],
                salario_publicado=bool(f["salario_publicado"]), salario_rango=f["salario_rango"],
                frase_pedir_salario=f["frase_pedir_salario"]),
            taxonomia=Taxonomia(sector=f["sector"] or "otros", familia=f["familia"] or "otros",
                                nivel=f["nivel"] or "sin_especificar", stack=f["stack"] or []))
    return salida


def dueña(s: Session, oferta_id: int) -> int | None:
    """La usuaria que añadió la oferta, o None si es del catálogo común."""
    return s.execute(text("select usuaria_id from ofertas where id=:i"),
                     {"i": oferta_id}).scalar_one_or_none()


def titulo(s: Session, oferta_id: int) -> str | None:
    return s.execute(text("select titulo from ofertas where id=:i"), {"i": oferta_id}).scalar_one_or_none()


def hay_propias(s: Session) -> bool:
    """¿La usuaria de la sesión tiene ofertas propias ya procesadas? (la RLS deja ver solo las suyas)"""
    return s.execute(text("select 1 from ofertas where usuaria_id is not null and estado = 'procesada' "
                          "limit 1")).first() is not None


def propias_sin_nota(s: Session, usuaria_id: int, huella: str, limite: int) -> list[int]:
    """Las propias procesadas que aún no tienen nota para esa huella del perfil (RF-10.10c)."""
    return list(s.execute(text(
        "select o.id from ofertas o where o.usuaria_id = :u and o.estado = 'procesada' "
        "and not exists (select 1 from matches m where m.oferta_id = o.id and m.huella_perfil = :h) "
        "and not exists (select 1 from descartes d where d.oferta_id = o.id) "
        "order by o.id limit :l"), {"u": usuaria_id, "h": huella, "l": limite}).scalars())


def marcar_error(s: Session, oferta_id: int, motivo: str) -> None:
    s.execute(text("update ofertas set estado='error', motivo_error=:m where id=:i"),
              {"i": oferta_id, "m": motivo[:500]})


def listar(s: Session, limite: int = 200) -> list[dict]:
    """El catálogo común, de la más nueva a la más antigua."""
    filas = s.execute(text(
        f"select {COLUMNAS_LISTA} from ofertas o left join fuentes f on f.id = o.fuente_id "
        "order by o.id desc limit :l"), {"l": limite}).mappings().all()
    return [dict(f) for f in filas]


def urls_catalogo(s: Session) -> list[str | None]:
    """La dirección de cada oferta del catálogo común (sin las propias de las usuarias)."""
    filas = s.execute(text("select url from ofertas where usuaria_id is null order by id")).all()
    return [u for (u,) in filas]


def por_estado(s: Session) -> dict[str, int]:
    return {e: n for e, n in s.execute(text(
        "select estado, count(*) from ofertas group by estado order by estado")).all()}


def errores_recientes(s: Session, n: int = 10) -> list[dict]:
    filas = s.execute(text(
        "select o.id, o.titulo, o.motivo_error, f.nombre as fuente, o.creada_en from ofertas o "
        "left join fuentes f on f.id = o.fuente_id where o.estado='error' and o.usuaria_id is null "
        "order by o.id desc limit :n"), {"n": n}).mappings().all()
    return [dict(f) for f in filas]


def propias(s: Session, usuaria_id: int, limite: int = 10) -> list[dict]:
    """Las ofertas añadidas por la usuaria, de la más nueva a la más antigua."""
    filas = s.execute(text(
        f"select {COLUMNAS_LISTA} from ofertas o left join fuentes f on f.id = o.fuente_id "
        "where o.usuaria_id = :u order by o.id desc limit :l"), {"u": usuaria_id, "l": limite}).mappings().all()  # noqa: E501
    return [dict(f) for f in filas]


def progreso_de_analisis(s: Session, ids: list[int]) -> dict[int, int]:
    """El avance de la última tarea `procesar_oferta` de cada oferta (sesión de sistema)."""
    if not ids:
        return {}
    filas = s.execute(text(
        "select distinct on (entidad_id) entidad_id, estado, progreso from tareas "
        "where tipo = 'procesar_oferta' and entidad_id = any(cast(:ids as int[])) "
        "order by entidad_id, id desc"), {"ids": list(ids)}).all()
    return {e: (100 if estado == "hecha" else p) for e, estado, p in filas}


def original(s: Session, oferta_id: int) -> dict | None:
    """El texto completo y su origen; la URL solo si es http(s) (RF-8.3b)."""
    f = s.execute(text(
        "select o.titulo, o.empresa, o.atribucion, o.usuaria_id is not null as propia, "
        "o.fecha_publicacion, o.url, o.texto_crudo as texto, f.nombre as fuente "
        "from ofertas o left join fuentes f on f.id = o.fuente_id where o.id = :i"),
        {"i": oferta_id}).mappings().first()
    if f is None:
        return None
    url = f["url"] if f["url"] and f["url"].lower().startswith(("http://", "https://")) else None
    return {"titulo": f["titulo"], "empresa": f["empresa"], "atribucion": f["atribucion"],
            "fuente": f["fuente"], "propia": f["propia"], "fecha_publicacion": f["fecha_publicacion"],
            "url": url, "texto": f["texto"]}


def visible(s: Session, oferta_id: int) -> bool:
    """¿La oferta existe y la usuaria de la sesión puede verla? (RLS: catálogo o propia)"""
    return s.execute(text("select 1 from ofertas where id = :i"), {"i": oferta_id}).first() is not None


def propias_sin_tarea(s: Session) -> list[tuple[int, int]]:
    """(oferta, usuaria) de las ofertas propias guardadas sin presupuesto: pendientes y sin ninguna tarea
    de análisis (RF-10.9e). Solo en modo sistema."""
    filas = s.execute(text(
        "select o.id, o.usuaria_id from ofertas o where o.usuaria_id is not null and o.estado = 'pendiente' "
        "and not exists (select 1 from tareas t where t.tipo = 'procesar_oferta' and t.entidad_id = o.id) "
        "order by o.id")).all()
    return [(f[0], f[1]) for f in filas]


def ids_recomendables_comunes(s: Session, limite: int) -> list[int]:
    """Las ofertas recomendables y ya procesadas del catálogo común, las más recientes primero."""
    return [f[0] for f in s.execute(text(
        "select id from ofertas where estado = 'procesada' and recomendable "
        "and usuaria_id is null order by fecha_publicacion desc nulls last, id desc limit :n"),
        {"n": limite})]
