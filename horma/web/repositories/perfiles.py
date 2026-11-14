"""SQL de los CV, los perfiles con versiones, las preferencias y los CV base. Todo es de una usuaria:
la sesión (RLS «propia») ya filtra, aquí no se repite el filtro por usuaria salvo al escribir."""
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias
from horma.schemas.taxonomia import Taxonomia

_j = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731
GRUPOS_DEL_CV = ("familias", "sectores", "idiomas")
_COLUMNAS_PREFS = ("familias", "sectores", "contratos", "niveles", "paises", "idiomas", "solo_remoto",
                   "solo_salario", "sueldo_minimo", "orden", "rango_min", "rango_max", "origen")


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


def _origenes(perfil: Perfil) -> list[tuple[str, str]]:
    salida = []
    for campo in ("titular", "resumen"):
        dato = getattr(perfil, campo)
        if dato:
            salida.append((campo, dato.origen.fragmento))
    for campo in ("experiencias", "formacion", "idiomas", "habilidades"):
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
        "estado = 'hecha', motivo_error = null where id = :id"),
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


def marcar_error_perfil(s: Session, perfil_id: int, motivo: str) -> None:
    s.execute(text("update perfiles set estado = 'error', motivo_error = :m where id = :i"),
              {"i": perfil_id, "m": motivo[:500]})


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
    columnas = ", ".join(_COLUMNAS_PREFS)
    marcas = ", ".join(f"cast(:{c} as jsonb)" if c == "origen" else
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


# --- CV base -----------------------------------------------------------------------------------
def guardar_cv_base(s: Session, usuaria_id: int, perfil_version: int, resultado: dict) -> None:
    """Un CV por destino: los verificados quedan 'hecho' y los rechazados dejan su motivo."""
    for g in resultado["guardados"]:
        d = g["destino"]
        s.execute(text(
            "insert into cv_base (usuaria_id, perfil_version, nombre, sector, familia, contenido, "
            "traza) values (:u, :v, :n, :s, :f, :c, cast(:t as jsonb))"),
            {"u": usuaria_id, "v": perfil_version, "n": f"CV base · {d['familia']} · {d['sector']}",
             "s": d["sector"], "f": d["familia"], "c": g["contenido"], "t": _j(g["traza"])})
    for r in resultado["rechazados"]:
        d = r["destino"]
        s.execute(text(
            "insert into cv_base (usuaria_id, perfil_version, nombre, sector, familia, estado, "
            "motivo_error) values (:u, :v, :n, :s, :f, 'rechazado', :m)"),
            {"u": usuaria_id, "v": perfil_version, "n": f"CV base · {d['familia']} · {d['sector']}",
             "s": d["sector"], "f": d["familia"], "m": r["motivo"][:500]})


def marcar_error_cv_base(s: Session, usuaria_id: int, perfil_version: int, motivo: str) -> None:
    s.execute(text(
        "insert into cv_base (usuaria_id, perfil_version, nombre, estado, motivo_error) "
        "values (:u, :v, 'CV base · error', 'error', :m)"),
        {"u": usuaria_id, "v": perfil_version, "m": motivo[:500]})
