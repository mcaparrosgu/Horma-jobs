"""SQL de los CV, los perfiles con versiones, las preferencias y los CV base. Todo es de una usuaria:
la sesión (RLS «propia») ya filtra, aquí no se repite el filtro por usuaria salvo al escribir."""
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from horma.schemas.perfil import CAMPO_PROPUESTA, Perfil
from horma.schemas.preferencias import MAX_LARGO_TERMINO, MAX_TERMINOS, Preferencias
from horma.schemas.taxonomia import Taxonomia
from horma.tools.comparar_versiones import comparar_versiones
from horma.tools.cv_base_afectado import lineas_cambiadas
from horma.tools.normalizar_titulo import casa_con_puestos
from horma.tools.visibilidad_cv import clave_experiencia, nombre_experiencia

_j = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731
GRUPOS_DEL_CV = ("puestos", "sectores", "idiomas")   # el área ya no se rellena ni se elige
_COLUMNAS_PREFS = ("familias", "puestos", "puestos_sugeridos", "excluidos", "sectores", "contratos",
                   "niveles", "paises", "idiomas", "solo_remoto",
                   "solo_salario", "sueldo_minimo", "incluir_propias", "orden", "rango_min", "rango_max",
                   "origen")


# --- CV ----------------------------------------------------------------------------------------
def cvs_fuente(s: Session) -> list[dict]:
    """Los CV que se procesan (no los estéticos), con su texto, en orden de subida."""
    filas = s.execute(text(
        "select id as cv_id, nombre, texto from cv_archivos "
        "where clase = 'fuente' and texto is not null order by id")).mappings().all()
    return [dict(f) for f in filas]


# --- perfiles ----------------------------------------------------------------------------------
def perfil_fila(s: Session, perfil_id: int) -> dict | None:
    fila = s.execute(text("select * from perfiles where id = :i"), {"i": perfil_id}).mappings().first()
    return dict(fila) if fila else None


def perfil_modelo(fila: dict) -> Perfil:
    """Reconstruye el `Perfil` de una fila: los datos más lo que vive en columnas propias."""
    taxonomia = None
    if fila["sector"] and fila["familia"] and fila["nivel"]:
        taxonomia = Taxonomia(sector=fila["sector"], familia=fila["familia"], nivel=fila["nivel"],
                              stack=fila["stack"] or [])
    return Perfil.model_validate({
        **fila["datos"], "version": fila["version"], "taxonomia": taxonomia,
        "preguntas_pendientes": fila["preguntas_pendientes"],
        "instrucciones_embebidas": fila["instrucciones_embebidas"]})


def vigente(s: Session) -> dict | None:
    """La versión vigente: la de mayor número ya construida (estado 'hecha')."""
    fila = s.execute(text("select * from perfiles where estado = 'hecha' "
                          "order by version desc limit 1")).mappings().first()
    return dict(fila) if fila else None


def vigente_de(s: Session, usuaria_id: int) -> dict | None:
    """Como `vigente`, para una usuaria concreta (el worker en modo sistema no tiene sesión de usuaria)."""
    fila = s.execute(text("select * from perfiles where usuaria_id = :u and estado = 'hecha' "
                          "order by version desc limit 1"), {"u": usuaria_id}).mappings().first()
    return dict(fila) if fila else None


def lo_de_la_usuaria(s: Session, usuaria_id: int) -> dict | None:
    """Lo que ella escribió o corrigió en el perfil vigente (origen «usuaria»), más su nombre y el género de
    sus puestos. Se lleva a la versión nueva cuando se rehace el perfil (RF-10.14)."""
    fila = vigente_de(s, usuaria_id)
    if fila is None:
        return None
    datos = perfil_modelo(fila).model_dump(mode="json")
    suyo: dict = {c: [x for x in datos[c] if x["origen"]["fuente"] == "usuaria"]
                  for c in ("experiencias", "formacion", "idiomas", "habilidades", "proyectos",
                            "certificaciones", "actividades", "otros")}
    for c in ("titular", "resumen"):
        if datos[c] and datos[c]["origen"]["fuente"] == "usuaria":
            suyo[c] = datos[c]
    suyo["nombre"], suyo["genero_puestos"] = datos.get("nombre"), datos.get("genero_puestos")
    # Lo que propuso guardar y aún no ha confirmado sigue en «Por resolver» (RF-10.15d).
    suyo["propuestas"] = [p for p in datos["preguntas_pendientes"] if p["campo"] == CAMPO_PROPUESTA]
    return suyo


def por_version(s: Session, version: int) -> dict | None:
    fila = s.execute(text("select * from perfiles where version = :v"), {"v": version}).mappings().first()
    return dict(fila) if fila else None


def ultima(s: Session) -> dict | None:
    """La última versión reservada, esté como esté (para decir si se está construyendo o falló)."""
    fila = s.execute(text("select id, version, estado, motivo_error from perfiles "
                          "order by version desc limit 1")).mappings().first()
    return dict(fila) if fila else None


def origenes(s: Session, perfil_id: int) -> list[dict]:
    return [dict(f) for f in s.execute(text(
        "select campo, fragmento from origen where entidad = 'perfil' and entidad_id = :i "
        "order by id"), {"i": perfil_id}).mappings().all()]


def _origenes(perfil: Perfil) -> list[tuple[str, str]]:
    salida = []
    for campo in ("titular", "resumen"):
        dato = getattr(perfil, campo)
        if dato:
            salida.append((campo, dato.origen.fragmento))
    for campo in ("resumenes", "titulares", "experiencias", "formacion", "idiomas", "habilidades", "proyectos",
                  "certificaciones", "actividades", "otros"):
        for i, x in enumerate(getattr(perfil, campo)):
            salida.append((f"{campo}.{i}", x.origen.fragmento))
    return salida


def guardar_perfil(s: Session, usuaria_id: int, perfil_id: int, perfil: Perfil,
                   cv_maestro: str | None = None) -> None:
    """Rellena la fila de la versión y sus orígenes (RT-08). `cv_maestro=None` conserva el anterior."""
    tax = perfil.taxonomia
    datos = perfil.model_dump(mode="json", exclude={"version", "taxonomia", "preguntas_pendientes",
                                                    "instrucciones_embebidas"})
    s.execute(text(
        "update perfiles set datos = cast(:d as jsonb), cv_maestro = coalesce(:m, cv_maestro), "
        "preguntas_pendientes = cast(:p as jsonb), instrucciones_embebidas = cast(:i as jsonb), "
        "sector = :sector, familia = :familia, nivel = :nivel, stack = cast(:stack as jsonb), "
        "estado = 'hecha', motivo_error = null where id = :id and estado <> 'retirado'"),
        {"id": perfil_id, "d": _j(datos), "m": cv_maestro,
         "p": _j([p.model_dump(mode="json") for p in perfil.preguntas_pendientes]),
         "i": _j(perfil.instrucciones_embebidas), "sector": tax.sector if tax else None,
         "familia": tax.familia if tax else None, "nivel": tax.nivel if tax else None,
         "stack": _j(tax.stack if tax else [])})
    s.execute(text("delete from origen where entidad = 'perfil' and entidad_id = :i "
                   "and usuaria_id = :u"), {"i": perfil_id, "u": usuaria_id})
    for campo, fragmento in _origenes(perfil):
        s.execute(text("insert into origen (usuaria_id, entidad, entidad_id, campo, fragmento) "
                       "values (:u, 'perfil', :i, :c, :f)"),
                  {"u": usuaria_id, "i": perfil_id, "c": campo, "f": fragmento})


def guardar_pendientes(s: Session, perfil_id: int, pendientes: list[dict]) -> None:
    """Cambia solo «Por resolver» de una versión, sin crear otra: añadir o descartar una propuesta de la
    usuaria no toca ningún dato del perfil (RF-10.15d)."""
    s.execute(text("update perfiles set preguntas_pendientes = cast(:p as jsonb) where id = :i"),
              {"i": perfil_id, "p": _j(pendientes)})


def marcar_error_perfil(s: Session, perfil_id: int, motivo: str) -> None:
    s.execute(text("update perfiles set estado = 'error', motivo_error = :m where id = :i "
                   "and estado <> 'retirado'"),
              {"i": perfil_id, "m": motivo[:500]})


def retirar_todos(s: Session) -> None:
    """Sin ningún CV, la usuaria se queda sin perfil vigente. Las versiones se conservan: las candidaturas y
    las compatibilidades ya hechas apuntan a ellas (RF-10.14)."""
    s.execute(text("update perfiles set estado = 'retirado' where estado in ('hecha', 'pendiente')"))


def aplazados(s: Session) -> list[tuple[int, int]]:
    """(usuaria, versión) de las versiones reservadas que esperan su `perfilar` porque no había presupuesto
    (RF-10.14). Solo en modo sistema."""
    return [(f[0], f[1]) for f in s.execute(text("select usuaria_id, perfil_id from perfiles_aplazados()")).all()]


def nueva_version(s: Session, usuaria_id: int) -> tuple[int, int]:
    """Reserva la siguiente versión (pendiente). Devuelve (id, versión)."""
    version = s.execute(text("select coalesce(max(version), 0) + 1 from perfiles "
                             "where usuaria_id = :u"), {"u": usuaria_id}).scalar_one()
    pid = s.execute(text("insert into perfiles (usuaria_id, version) values (:u, :v) returning id"),
                    {"u": usuaria_id, "v": version}).scalar_one()
    return pid, version


# --- preferencias ------------------------------------------------------------------------------
def preferencias(s: Session) -> Preferencias:
    """Las de la usuaria de la sesión, o las de por defecto si aún no hay."""
    fila = s.execute(text(f"select {', '.join(_COLUMNAS_PREFS)} from preferencias")).mappings().first()
    if not fila:
        return Preferencias()
    datos = dict(fila)
    if datos["sueldo_minimo"] is not None:
        datos["sueldo_minimo"] = float(datos["sueldo_minimo"])
    return Preferencias.model_validate(datos)


def guardar_preferencias(s: Session, usuaria_id: int, p: Preferencias) -> None:
    valores = p.model_dump(mode="json")
    valores["origen"] = _j(valores["origen"])
    valores["puestos_sugeridos"] = _j(valores["puestos_sugeridos"])
    columnas = ", ".join(_COLUMNAS_PREFS)
    marcas = ", ".join(f"cast(:{c} as jsonb)" if c == "origen" or c == "puestos_sugeridos" else
                       f"cast(:{c} as text[])" if isinstance(valores[c], list) else f":{c}"
                       for c in _COLUMNAS_PREFS)
    cambios = ", ".join(f"{c} = excluded.{c}" for c in _COLUMNAS_PREFS)
    s.execute(text(
        f"insert into preferencias (usuaria_id, {columnas}) values (:u, {marcas}) "
        f"on conflict (usuaria_id) do update set {cambios}, actualizada_en = now()"),
        {"u": usuaria_id, **valores})


def aplicar_preferencias_del_cv(s: Session, usuaria_id: int, desde_cv: Preferencias) -> None:
    """Rellena puestos, sectores e idiomas con lo que sale del CV (RF-2.8b) sin pisar los grupos que
    la usuaria ya escribió ella."""
    actual = preferencias(s)
    actual.puestos_sugeridos = desde_cv.puestos_sugeridos  # siempre se renuevan (RF-9.3b)
    for grupo in GRUPOS_DEL_CV:
        if actual.origen.get(grupo) == "usuaria":
            continue
        valor = getattr(desde_cv, grupo)
        setattr(actual, grupo, valor)
        if valor:
            actual.origen[grupo] = "cv"
        else:
            actual.origen.pop(grupo, None)
    guardar_preferencias(s, usuaria_id, actual)


def aplicar_puestos_del_cv(s: Session, usuaria_id: int, sugeridos: list[dict]) -> None:
    """Tras reclasificar: los sugeridos se renuevan; los puestos marcados, solo si no los tocó ella."""
    desde_cv = Preferencias(puestos=[p["titulo"] for p in sugeridos], puestos_sugeridos=sugeridos)
    actual = preferencias(s)
    actual.puestos_sugeridos = desde_cv.puestos_sugeridos
    if actual.origen.get("puestos") != "usuaria":
        actual.puestos = desde_cv.puestos
        if actual.puestos:
            actual.origen["puestos"] = "cv"
        else:
            actual.origen.pop("puestos", None)
    guardar_preferencias(s, usuaria_id, actual)


def anadir_puesto_de_oferta(s: Session, usuaria_id: int, titulo: str | None) -> bool:
    """RF-10.6h: el título de una oferta que ella añade entra en sus puestos marcados si ninguno lo cubre.
    Con la lista vacía no se añade: un puesto empezaría a filtrar lo que hoy se ve todo."""
    titulo = " ".join((titulo or "").split())[:MAX_LARGO_TERMINO]
    actual = preferencias(s)
    if (not titulo or not actual.puestos or len(actual.puestos) >= MAX_TERMINOS
            or casa_con_puestos(titulo, actual.puestos)):
        return False
    actual.puestos = [*actual.puestos, titulo]
    actual.origen["puestos"] = "usuaria"   # lo ha traído ella: el CV ya no lo pisa
    guardar_preferencias(s, usuaria_id, actual)
    return True


# --- avisos vistos y longitud del CV (RF-9.2c, RF-9.2d) -----------------------------------------
def avisos_vistos(s: Session) -> dict[str, str]:
    """clave -> huella de lo que la usuaria dio por visto."""
    return {f["clave"]: f["huella"] for f in s.execute(text(
        "select clave, huella from avisos_vistos")).mappings()}


def marcar_visto(s: Session, usuaria_id: int, clave: str, huella: str) -> None:
    s.execute(text(
        "insert into avisos_vistos (usuaria_id, clave, huella) values (:u, :c, :h) "
        "on conflict (usuaria_id, clave) do update set huella = excluded.huella, creado_en = now()"),
        {"u": usuaria_id, "c": clave, "h": huella})


def longitud_cv(s: Session) -> str | None:
    return s.execute(text("select longitud_cv from ajustes_perfil")).scalar()


def fijar_longitud(s: Session, usuaria_id: int, longitud: str) -> None:
    s.execute(text(
        "insert into ajustes_perfil (usuaria_id, longitud_cv) values (:u, :l) "
        "on conflict (usuaria_id) do update set longitud_cv = excluded.longitud_cv"),
        {"u": usuaria_id, "l": longitud})


# --- CV base -----------------------------------------------------------------------------------
def _nombre_cv_base(destino: dict, version: int) -> str:
    return f"CV base · {destino['familia']} · {destino['sector']} · v{version}"


def listar_cv_base(s: Session) -> list[dict]:
    """Todos los CV base de la usuaria. `desfasado` (RF-5.1e): el perfil ha avanzado Y algún dato de la
    traza del CV ya no está en el maestro vigente; `cambios` = esas líneas, tal como estaban."""
    filas = [dict(f) for f in s.execute(text(
        "select c.id, c.nombre, c.sector, c.familia, c.contenido, c.estado, c.motivo_error, "
        "c.perfil_version, c.creado_en, c.traza, c.visibilidad "
        "from cv_base c order by c.id")).mappings().all()]
    actual = vigente(s)
    for f in filas:
        traza = f.pop("traza") or []
        cambios = (lineas_cambiadas(traza, actual["cv_maestro"])
                   if actual and f["perfil_version"] < actual["version"] else [])
        f["cambios"], f["desfasado"] = cambios, bool(cambios)
    return filas


def hay_cv_base_hecho(s: Session, perfil_version: int) -> bool:
    return s.execute(text("select 1 from cv_base where perfil_version = :v and estado = 'hecho'"),
                     {"v": perfil_version}).first() is not None


def renombrar_cv_base(s: Session, cv_id: int, nombre: str) -> bool:
    return s.execute(text("update cv_base set nombre = :n where id = :i and estado = 'hecho'"),
                     {"i": cv_id, "n": nombre}).rowcount == 1


def editar_cv_base(s: Session, cv_id: int, nombre: str | None, contenido: str | None, *,
                   origen: str = "edicion") -> bool:
    """Cambia el nombre y/o el texto de un CV base ya hecho. El texto editado es de ella, no del modelo.

    Antes de sobrescribir guarda la versión que se va a sustituir en `cv_base_versiones` (RF-3.8d), en
    la misma transacción. `origen` dice qué la sustituye: `edicion` manual o `restauracion`.
    Si no cambia nada, no se guarda versión."""
    actual = s.execute(text("select usuaria_id, nombre, contenido from cv_base "
                            "where id = :i and estado = 'hecho' for update"), {"i": cv_id}).mappings().first()
    if actual is None:
        return False
    nuevo_nombre = actual["nombre"] if nombre is None else nombre
    nuevo_contenido = actual["contenido"] if contenido is None else contenido
    if (nuevo_nombre, nuevo_contenido) == (actual["nombre"], actual["contenido"]):
        return True
    s.execute(text(
        "insert into cv_base_versiones (usuaria_id, cv_base_id, nombre, contenido, origen) "
        "values (:u, :i, :n, :c, :o)"),
        {"u": actual["usuaria_id"], "i": cv_id, "n": actual["nombre"], "c": actual["contenido"],
         "o": origen})
    s.execute(text("update cv_base set nombre = :n, contenido = :c where id = :i"),
              {"i": cv_id, "n": nuevo_nombre, "c": nuevo_contenido})
    return True


def datos_para_regenerar(s: Session, cv_id: int) -> dict | None:
    """Destino del CV base que se va a regenerar; `None` si no existe o no está hecho."""
    fila = s.execute(text("select sector, familia, visibilidad from cv_base "
                          "where id = :i and estado = 'hecho'"), {"i": cv_id}).mappings().first()
    return dict(fila) if fila else None


def experiencias_marcables(s: Session) -> list[dict]:
    """Las experiencias del perfil vigente con su clave estable, para marcar su visibilidad (RF-5.1g)."""
    fila = vigente(s)
    if fila is None:
        return []
    return [{"clave": clave_experiencia(x), "nombre": nombre_experiencia(x),
             "periodo": " - ".join(p for p in (x.inicio, x.fin) if p)}
            for x in perfil_modelo(fila).experiencias]


def guardar_visibilidad(s: Session, cv_id: int, visibilidad: dict[str, str]) -> bool:
    return s.execute(text("update cv_base set visibilidad = cast(:v as jsonb) "
                          "where id = :i and estado = 'hecho'"),
                     {"i": cv_id, "v": _j(visibilidad)}).rowcount == 1


def regenerar_cv_base(s: Session, cv_id: int, perfil_version: int, guardado: dict) -> bool:
    """Sustituye el contenido, la traza y la versión del perfil del CV base. La versión anterior va al
    historial con origen `regeneracion` (misma transacción). Mantiene el nombre que le puso la usuaria."""
    if not editar_cv_base(s, cv_id, None, guardado["contenido"], origen="regeneracion"):
        return False
    s.execute(text("update cv_base set traza = cast(:t as jsonb), perfil_version = :v, "
                   "motivo_error = null where id = :i"),
              {"i": cv_id, "t": _j(guardado["traza"]), "v": perfil_version})
    return True


def marcar_error_regeneracion(s: Session, cv_id: int, motivo: str) -> None:
    """El CV se queda como estaba; el motivo se ve en su tarjeta."""
    s.execute(text("update cv_base set motivo_error = :m where id = :i and estado = 'hecho'"),
              {"i": cv_id, "m": motivo[:500]})


def limpiar_error_regeneracion(s: Session, cv_id: int) -> None:
    """Al pedir otra regeneración, el aviso del intento anterior desaparece para no confundir."""
    s.execute(text("update cv_base set motivo_error = null where id = :i"), {"i": cv_id})


def versiones_cv_base(s: Session, cv_id: int) -> list[dict] | None:
    """El historial del CV base, de la más reciente a la más antigua; `None` si el CV base no existe.
    Cada versión se compara con la siguiente (la que la sustituyó; la última, con el texto actual)."""
    actual = s.execute(text("select contenido from cv_base where id = :i and estado = 'hecho'"),
                       {"i": cv_id}).scalar()
    if actual is None:
        return None
    filas = [dict(f) for f in s.execute(text(
        "select id, nombre, contenido, origen, creado_en from cv_base_versiones "
        "where cv_base_id = :i order by id"), {"i": cv_id}).mappings()]
    siguientes = [f["contenido"] for f in filas[1:]] + ([actual] if filas else [])
    for f, siguiente in zip(filas, siguientes, strict=True):
        f["lineas"] = comparar_versiones(f["contenido"], siguiente)
        del f["contenido"]
    return filas[::-1]


def restaurar_cv_base(s: Session, cv_id: int, version_id: int) -> bool | None:
    """Vuelve a una versión: guarda antes la actual en el historial. Si el nombre de esa versión lo usa
    ahora otro CV, conserva el actual. `None` si no existe el CV base o la versión."""
    v = s.execute(text("select nombre, contenido from cv_base_versiones "
                       "where id = :v and cv_base_id = :i"), {"v": version_id, "i": cv_id}).mappings().first()
    if v is None:
        return None
    libre = s.execute(text(
        "select not exists (select 1 from cv_base where lower(nombre) = lower(:n) and estado = 'hecho' "
        "and id <> :i) and not exists (select 1 from cv_archivos where lower(nombre) = lower(:n))"),
        {"n": v["nombre"], "i": cv_id}).scalar_one()
    nombre = v["nombre"] if libre else None
    return editar_cv_base(s, cv_id, nombre, v["contenido"], origen="restauracion") or None


def eliminar_cv_base(s: Session, cv_id: int) -> bool:
    return s.execute(text("delete from cv_base where id = :i"), {"i": cv_id}).rowcount == 1


def guardar_cv_base(s: Session, usuaria_id: int, perfil_version: int, resultado: dict) -> None:
    """Un CV por destino: los verificados quedan 'hecho' y los rechazados dejan su motivo."""
    for g in resultado["guardados"]:
        d = g["destino"]
        s.execute(text(
            "insert into cv_base (usuaria_id, perfil_version, nombre, sector, familia, contenido, "
            "traza) values (:u, :v, :n, :s, :f, :c, cast(:t as jsonb))"),
            {"u": usuaria_id, "v": perfil_version, "n": _nombre_cv_base(d, perfil_version),
             "s": d["sector"], "f": d["familia"], "c": g["contenido"], "t": _j(g["traza"])})
    for r in resultado["rechazados"]:
        d = r["destino"]
        s.execute(text(
            "insert into cv_base (usuaria_id, perfil_version, nombre, sector, familia, estado, "
            "motivo_error) values (:u, :v, :n, :s, :f, 'rechazado', :m)"),
            {"u": usuaria_id, "v": perfil_version, "n": _nombre_cv_base(d, perfil_version),
             "s": d["sector"], "f": d["familia"], "m": r["motivo"][:500]})


def marcar_error_cv_base(s: Session, usuaria_id: int, perfil_version: int, motivo: str) -> None:
    s.execute(text(
        "insert into cv_base (usuaria_id, perfil_version, nombre, estado, motivo_error) "
        "values (:u, :v, 'CV base · error', 'error', :m)"),
        {"u": usuaria_id, "v": perfil_version, "m": motivo[:500]})
