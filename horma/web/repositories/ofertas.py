"""Único lugar donde se escribe SQL sobre ofertas y su origen. El catálogo se escribe en modo sistema."""
import json

from pydantic import HttpUrl, TypeAdapter, ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from horma.schemas.oferta import Auditoria, Oferta, Salario
from horma.schemas.taxonomia import Taxonomia
from horma.tools.normalizar import huella
from horma.tools.normalizar_oferta import normalizar_oferta

COLUMNAS_LISTA = (
    "o.id, o.estado, o.motivo_error, o.titulo, o.empresa, o.ubicacion, o.remoto, o.contrato, "
    "o.salario_minimo, o.salario_maximo, o.salario_moneda, o.idiomas, o.fecha_publicacion, o.url, "
    "o.instrucciones_embebidas, o.fantasma, o.motivos_fantasma, o.fraude, o.senales_fraude, "
    "o.dominio_empresa, o.empresa_validada, o.salario_publicado, o.salario_rango, "
    "o.frase_pedir_salario, o.sector, o.familia, o.nivel, o.stack, o.recomendable, o.creada_en, "
    "f.nombre as fuente")


def _existente(s: Session, fuente_id, clave_id, id_externo) -> dict | None:
    if not id_externo or not (fuente_id or clave_id):
        return None
    if fuente_id:
        sql = "select id, estado from ofertas where fuente_id=:f and id_externo=:e"
    else:
        sql = "select id, estado from ofertas where fuente_id is null and clave_id=:c and id_externo=:e"
    fila = s.execute(text(sql), {"f": fuente_id, "c": clave_id, "e": id_externo}).mappings().first()
    return dict(fila) if fila else None


def crear(s: Session, texto: str, *, fuente_id: int | None = None, clave_id: int | None = None,
          id_externo: str | None = None, url: str | None = None) -> tuple[int, str, bool]:
    """Guarda la oferta cruda. Devuelve (id, estado, nueva); idempotente por origen + id_externo."""
    if (previa := _existente(s, fuente_id, clave_id, id_externo)):
        return previa["id"], previa["estado"], False
    try:
        with s.begin_nested():
            oid = s.execute(text(
                "insert into ofertas (texto_crudo, fuente_id, clave_id, id_externo, url, huella) "
                "values (:t, :f, :c, :e, :u, :h) returning id"),
                {"t": texto, "f": fuente_id, "c": clave_id, "e": id_externo, "u": url,
                 "h": huella(texto)}).scalar_one()
    except IntegrityError:  # otra petición la insertó a la vez
        previa = _existente(s, fuente_id, clave_id, id_externo)
        return previa["id"], previa["estado"], False
    return oid, "pendiente", True


def para_procesar(s: Session, oferta_id: int) -> dict:
    """Lo que necesita el flujo: texto, fuente, url y si el mismo texto ya entró antes."""
    fila = s.execute(text(
        "select o.texto_crudo, o.url, f.nombre as fuente, exists(select 1 from ofertas p "
        "where p.huella = o.huella and p.id < o.id) as repetida "
        "from ofertas o left join fuentes f on f.id = o.fuente_id where o.id=:i"),
        {"i": oferta_id}).mappings().one()
    return {"texto": fila["texto_crudo"], "url": fila["url"], "fuente": fila["fuente"],
            "repetida": fila["repetida"]}


def guardar(s: Session, oferta_id: int, o: Oferta, origenes: list[tuple[str, str]]) -> None:
    sal, a, t = o.salario, o.auditoria, o.taxonomia
    j = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731
    texto = s.execute(text("select texto_crudo from ofertas where id=:i"), {"i": oferta_id}).scalar_one()
    n = normalizar_oferta(o, texto)  # país, contrato, idiomas y sueldo anual para filtrar (P16)
    s.execute(text(
        "update ofertas set estado='procesada', motivo_error=null, procesada_en=now(), "
        "titulo=:titulo, empresa=:empresa, ubicacion=:ubicacion, remoto=:remoto, "
        "contrato=:contrato, salario_minimo=:smin, salario_maximo=:smax, salario_moneda=:smon, "
        "idiomas=cast(:idiomas as jsonb), requisitos=cast(:req as jsonb), fecha_publicacion=:fecha, "
        "url=coalesce(:url, url), instrucciones_embebidas=cast(:instr as jsonb), "
        "fantasma=:fantasma, motivos_fantasma=cast(:motivos as jsonb), fraude=:fraude, "
        "senales_fraude=cast(:senales as jsonb), dominio_empresa=:dominio, "
        "empresa_validada=:validada, salario_publicado=:publicado, salario_rango=:rango, "
        "frase_pedir_salario=:frase, sector=:sector, familia=:familia, nivel=:nivel, "
        "stack=cast(:stack as jsonb), pais=:pais, tipo_contrato=:tcontrato, "
        "idiomas_norm=cast(:idiomas_norm as text[]), salario_anual_eur_min=:anual_min, "
        "salario_anual_eur_max=:anual_max where id=:id"),
        {"id": oferta_id, "titulo": o.titulo, "empresa": o.empresa, "ubicacion": o.ubicacion,
         "remoto": o.remoto, "contrato": o.contrato, "smin": sal.minimo if sal else None,
         "smax": sal.maximo if sal else None, "smon": sal.moneda if sal else None,
         "idiomas": j(o.idiomas), "req": j(o.requisitos), "fecha": o.fecha_publicacion,
         "url": str(o.url) if o.url else None, "instr": j(o.instrucciones_embebidas),
         "fantasma": a.fantasma, "motivos": j(a.motivos_fantasma), "fraude": a.fraude,
         "senales": j(a.senales_fraude), "dominio": a.dominio_empresa,
         "validada": a.empresa_validada, "publicado": a.salario_publicado, "rango": a.salario_rango,
         "frase": a.frase_pedir_salario, "sector": t.sector, "familia": t.familia,
         "nivel": t.nivel, "stack": j(t.stack), "pais": n.pais, "tcontrato": n.tipo_contrato,
         "idiomas_norm": n.idiomas, "anual_min": n.salario_anual_eur_min,
         "anual_max": n.salario_anual_eur_max})
    s.execute(text("delete from origen where entidad='oferta' and entidad_id=:i and usuaria_id is null"),
              {"i": oferta_id})
    for campo, fragmento in origenes:
        s.execute(text("insert into origen (entidad, entidad_id, campo, fragmento) "
                       "values ('oferta', :i, :c, :f)"),
                  {"i": oferta_id, "c": campo, "f": fragmento})


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
        "select id, titulo, empresa, ubicacion, remoto, contrato, salario_minimo, salario_maximo, "
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
            remoto=f["remoto"], contrato=f["contrato"], salario=salario, idiomas=f["idiomas"],
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


def marcar_error(s: Session, oferta_id: int, motivo: str) -> None:
    s.execute(text("update ofertas set estado='error', motivo_error=:m where id=:i"),
              {"i": oferta_id, "m": motivo[:500]})


def listar(s: Session, limite: int = 200) -> list[dict]:
    """El catálogo común, de la más nueva a la más antigua."""
    filas = s.execute(text(
        f"select {COLUMNAS_LISTA} from ofertas o left join fuentes f on f.id = o.fuente_id "
        "order by o.id desc limit :l"), {"l": limite}).mappings().all()
    return [dict(f) for f in filas]


def por_estado(s: Session) -> dict[str, int]:
    return {e: n for e, n in s.execute(text(
        "select estado, count(*) from ofertas group by estado order by estado")).all()}


def errores_recientes(s: Session, n: int = 10) -> list[dict]:
    filas = s.execute(text(
        "select o.id, o.titulo, o.motivo_error, f.nombre as fuente, o.creada_en from ofertas o "
        "left join fuentes f on f.id = o.fuente_id where o.estado='error' "
        "order by o.id desc limit :n"), {"n": n}).mappings().all()
    return [dict(f) for f in filas]
