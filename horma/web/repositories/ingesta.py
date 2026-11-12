"""SQL de fuentes, calificaciones, ejecuciones de ingesta y claves de API (todo en modo sistema)."""
import hashlib
import json
import secrets

from sqlalchemy import text
from sqlalchemy.orm import Session

from horma.schemas.fuente import CalificacionFuente, Fuente

CAMPOS_FUENTE = "id, nombre, web, url, metodo, parametros, cabeceras, variable_clave, mapeo, activa"


# --- fuentes -----------------------------------------------------------------------------------
def _parametros_fuente(f: Fuente) -> dict:
    return {**f.model_dump(), "parametros": json.dumps(f.parametros),
            "cabeceras": json.dumps(f.cabeceras), "mapeo": json.dumps(f.mapeo)}


def crear_fuente(s: Session, f: Fuente) -> int:
    return s.execute(text(
        "insert into fuentes (nombre, web, url, metodo, parametros, cabeceras, variable_clave, mapeo, "
        "activa) values (:nombre, :web, :url, :metodo, cast(:parametros as jsonb), "
        "cast(:cabeceras as jsonb), :variable_clave, cast(:mapeo as jsonb), :activa) returning id"),
        _parametros_fuente(f)).scalar_one()


def actualizar_fuente(s: Session, fuente_id: int, f: Fuente) -> bool:
    return s.execute(text(
        "update fuentes set nombre=:nombre, web=:web, url=:url, metodo=:metodo, "
        "parametros=cast(:parametros as jsonb), cabeceras=cast(:cabeceras as jsonb), "
        "variable_clave=:variable_clave, mapeo=cast(:mapeo as jsonb), activa=:activa where id=:id"),
        {**_parametros_fuente(f), "id": fuente_id}).rowcount == 1


def fuente(s: Session, *, fuente_id: int | None = None, nombre: str | None = None) -> dict | None:
    fila = s.execute(text(f"select {CAMPOS_FUENTE} from fuentes where id=:i or nombre=:n"),
                     {"i": fuente_id, "n": nombre}).mappings().first()
    return dict(fila) if fila else None


def fuentes(s: Session) -> list[dict]:
    """Cada fuente con su última ejecución y la última calificación de su dominio."""
    filas = s.execute(text(f"select {CAMPOS_FUENTE} from fuentes order by nombre")).mappings().all()
    resultado = []
    for f in filas:
        d = dict(f)
        d["ultima_ejecucion"] = ultima_ejecucion(s, f["id"])
        resultado.append(d)
    return resultado


# --- calificaciones ----------------------------------------------------------------------------
COLUMNAS_CALIFICACION = (
    "id, url, dominio, estado, apta, excluida_por_regla, permite_uso_automatizado, robots_permite, "
    "requiere_clave, motivos, citas, instrucciones_embebidas, motivo_error, creada_en, calificada_en")


def crear_calificacion(s: Session, url: str, dominio: str) -> int:
    return s.execute(text("insert into calificaciones_fuente (url, dominio) values (:u, :d) "
                          "returning id"), {"u": url, "d": dominio}).scalar_one()


def calificacion(s: Session, calificacion_id: int) -> dict | None:
    fila = s.execute(text(f"select {COLUMNAS_CALIFICACION} from calificaciones_fuente where id=:i"),
                     {"i": calificacion_id}).mappings().first()
    return dict(fila) if fila else None


def ultima_calificacion(s: Session, dominio: str) -> dict | None:
    fila = s.execute(text(f"select {COLUMNAS_CALIFICACION} from calificaciones_fuente "
                          "where dominio=:d and estado='hecha' order by id desc limit 1"),
                     {"d": dominio}).mappings().first()
    return dict(fila) if fila else None


def guardar_calificacion(s: Session, calificacion_id: int, c: CalificacionFuente) -> None:
    j = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731
    s.execute(text(
        "update calificaciones_fuente set estado='hecha', apta=:apta, "
        "excluida_por_regla=:excluida, permite_uso_automatizado=:permite, robots_permite=:robots, "
        "requiere_clave=:clave, motivos=cast(:motivos as jsonb), citas=cast(:citas as jsonb), "
        "instrucciones_embebidas=cast(:instr as jsonb), calificada_en=now() where id=:id"),
        {"id": calificacion_id, "apta": c.apta, "excluida": c.excluida_por_regla,
         "permite": c.permite_uso_automatizado, "robots": c.robots_permite,
         "clave": c.requiere_clave, "motivos": j(c.motivos), "citas": j(c.citas),
         "instr": j(c.instrucciones_embebidas)})


def marcar_error_calificacion(s: Session, calificacion_id: int, motivo: str) -> None:
    s.execute(text("update calificaciones_fuente set estado='error', motivo_error=:m where id=:i"),
              {"i": calificacion_id, "m": motivo[:500]})


# --- ejecuciones de ingesta -----------------------------------------------------------------------
COLUMNAS_EJECUCION = ("id, fuente_id, limite, estado, recibidas, nuevas, repetidas, errores, "
                    "motivo_error, creada_en, iniciada_en, terminada_en")


def crear_ejecucion(s: Session, fuente_id: int, limite: int, en_curso: bool = False) -> dict:
    return dict(s.execute(text(
        f"insert into ejecuciones_ingesta (fuente_id, limite, estado, iniciada_en) values "
        f"(:f, :l, :e, case when :c then now() end) returning {COLUMNAS_EJECUCION}"),
        {"f": fuente_id, "l": limite, "e": "en_curso" if en_curso else "pendiente",
         "c": en_curso}).mappings().one())


def reclamar_ejecucion(s: Session) -> dict | None:
    fila = s.execute(text(
        f"update ejecuciones_ingesta set estado='en_curso', iniciada_en=now() where id = ("
        "select id from ejecuciones_ingesta where estado='pendiente' order by id "
        f"for update skip locked limit 1) returning {COLUMNAS_EJECUCION}")).mappings().first()
    return dict(fila) if fila else None


def cerrar_ejecucion(s: Session, ejecucion_id: int, *, recibidas: int, nuevas: int, repetidas: int,
                   errores: int, motivo: str | None) -> bool:
    return s.execute(text(
        "update ejecuciones_ingesta set estado=:e, recibidas=:r, nuevas=:n, repetidas=:p, "
        "errores=:x, motivo_error=:m, terminada_en=now() where id=:i and estado='en_curso'"),
        {"i": ejecucion_id, "e": "error" if motivo else "hecha", "r": recibidas, "n": nuevas,
         "p": repetidas, "x": errores, "m": motivo[:500] if motivo else None}).rowcount == 1


def ejecucion(s: Session, ejecucion_id: int) -> dict | None:
    fila = s.execute(text(f"select {COLUMNAS_EJECUCION} from ejecuciones_ingesta where id=:i"),
                     {"i": ejecucion_id}).mappings().first()
    return dict(fila) if fila else None


def ultima_ejecucion(s: Session, fuente_id: int) -> dict | None:
    fila = s.execute(text(f"select {COLUMNAS_EJECUCION} from ejecuciones_ingesta where fuente_id=:f "
                          "order by id desc limit 1"), {"f": fuente_id}).mappings().first()
    return dict(fila) if fila else None


def ejecuciones_con_error(s: Session, n: int = 10) -> list[dict]:
    filas = s.execute(text(
        "select c.id, f.nombre as fuente, c.motivo_error, c.terminada_en from ejecuciones_ingesta c "
        "join fuentes f on f.id = c.fuente_id where c.estado='error' order by c.id desc limit :n"),
        {"n": n}).mappings().all()
    return [dict(f) for f in filas]


# --- claves de API -----------------------------------------------------------------------------
def _hash(clave: str) -> str:
    return hashlib.sha256(clave.encode("utf-8")).hexdigest()


def crear_clave(s: Session, nombre: str, alcance: str) -> tuple[int, str, str]:
    """Devuelve (id, clave en claro, prefijo). La clave en claro no se guarda nunca."""
    clave = "hk_" + secrets.token_urlsafe(32)
    prefijo = clave[:10]
    cid = s.execute(text("insert into claves_api (nombre, prefijo, hash, alcance) "
                         "values (:n, :p, :h, :a) returning id"),
                    {"n": nombre, "p": prefijo, "h": _hash(clave), "a": alcance}).scalar_one()
    return cid, clave, prefijo


def buscar_clave(s: Session, clave: str) -> dict | None:
    fila = s.execute(text("select id, alcance from claves_api where hash=:h and revocada_en is null"),
                     {"h": _hash(clave)}).mappings().first()
    return dict(fila) if fila else None


def claves(s: Session) -> list[dict]:
    filas = s.execute(text("select id, nombre, prefijo, alcance, creada_en, revocada_en "
                           "from claves_api order by id desc")).mappings().all()
    return [dict(f) for f in filas]


def revocar_clave(s: Session, clave_id: int) -> bool:
    return s.execute(text("update claves_api set revocada_en=now() where id=:i "
                          "and revocada_en is null"), {"i": clave_id}).rowcount == 1
