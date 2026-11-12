"""Servicio de ingesta: fuentes, calificaciones, ejecuciones y claves (RF-1.1, RF-1.7, RF-1.8)."""
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from horma.config import ajustes
from horma.schemas.fuente import Fuente
from horma.tools import dominio
from horma.web.db import sesion_sistema
from horma.web.repositories import ingesta as repo
from horma.web.repositories import ofertas as repo_ofertas
from horma.web.repositories import tareas

TIPO_CALIFICAR = "calificar_fuente"


class Conflicto(Exception):
    """La operación choca con el estado actual (409)."""


class NoValida(Exception):
    """Los datos no se aceptan por regla (422)."""


class NoEncontrada(Exception):
    """No existe (404)."""


def _comprobar_fuente(s, f: Fuente) -> None:
    for url in (f.web, f.url):
        if (portal := dominio.excluida_por_regla(url)):
            raise NoValida(f"Excluida por regla: {portal} nunca se usa como fuente.")
    if f.activa:
        c = repo.ultima_calificacion(s, dominio.registrable(f.web) or "")
        if not c or not c["apta"]:
            raise Conflicto("Solo se activa una fuente con una calificación apta de su dominio.")


def crear_fuente(engine: Engine, f: Fuente) -> int:
    try:
        with sesion_sistema(engine) as s:
            _comprobar_fuente(s, f)
            return repo.crear_fuente(s, f)
    except IntegrityError as e:
        raise Conflicto(f"Ya existe una fuente llamada {f.nombre}.") from e


def actualizar_fuente(engine: Engine, fuente_id: int, f: Fuente) -> None:
    try:
        with sesion_sistema(engine) as s:
            _comprobar_fuente(s, f)
            if not repo.actualizar_fuente(s, fuente_id, f):
                raise NoEncontrada(fuente_id)
    except IntegrityError as e:
        raise Conflicto(f"Ya existe una fuente llamada {f.nombre}.") from e


def resumen(engine: Engine) -> dict:
    with sesion_sistema(engine) as s:
        lista = repo.fuentes(s)
        for f in lista:
            f["calificacion"] = repo.ultima_calificacion(s, dominio.registrable(f["web"]) or "")
        return {"fuentes": lista, "ofertas_por_estado": repo_ofertas.por_estado(s),
                "errores": repo_ofertas.errores_recientes(s),
                "ejecuciones_con_error": repo.ejecuciones_con_error(s)}


def _fuente_activa(s, *, fuente_id=None, nombre=None) -> dict:
    f = repo.fuente(s, fuente_id=fuente_id, nombre=nombre)
    if not f:
        raise NoEncontrada(fuente_id or nombre)
    if not f["activa"]:
        raise Conflicto("La fuente no está activa.")
    return f


def pedir_ejecucion(engine: Engine, fuente_id: int, limite: int) -> dict:
    """El botón del dashboard: deja la ejecución pendiente; la ejecuta el ingestor (sin BD)."""
    with sesion_sistema(engine) as s:
        _fuente_activa(s, fuente_id=fuente_id)
        return repo.crear_ejecucion(s, fuente_id, limite)


def _con_fuente(s, ejecucion: dict) -> dict:
    f = repo.fuente(s, fuente_id=ejecucion["fuente_id"])
    return {"ejecucion": ejecucion, "fuente": Fuente.model_validate(f).model_dump()}


def empezar_ejecucion(engine: Engine, nombre: str, limite: int) -> dict:
    """La consola: crea la ejecución ya en curso y devuelve la configuración de la fuente."""
    with sesion_sistema(engine) as s:
        f = _fuente_activa(s, nombre=nombre)
        return _con_fuente(s, repo.crear_ejecucion(s, f["id"], limite, en_curso=True))


def reclamar_ejecucion(engine: Engine) -> dict | None:
    with sesion_sistema(engine) as s:
        c = repo.reclamar_ejecucion(s)
        return _con_fuente(s, c) if c else None


def cerrar_ejecucion(engine: Engine, ejecucion_id: int, **numeros) -> None:
    with sesion_sistema(engine) as s:
        if not repo.cerrar_ejecucion(s, ejecucion_id, **numeros):
            raise Conflicto("La ejecución no existe o no está en curso.")


def pedir_calificacion(engine: Engine, url: str) -> dict:
    with sesion_sistema(engine) as s:
        cid = repo.crear_calificacion(s, url, dominio.registrable(url) or url)
        a = ajustes()
        tareas.encolar(s, None, TIPO_CALIFICAR, cid, a.tope_coste_tarea, a.tope_reintentos_tarea)
        return {"id": cid, "estado": "pendiente"}


def ver_calificacion(engine: Engine, calificacion_id: int) -> dict:
    with sesion_sistema(engine) as s:
        c = repo.calificacion(s, calificacion_id)
    if not c:
        raise NoEncontrada(calificacion_id)
    return c


def crear_clave(engine: Engine, nombre: str, alcance: str) -> dict:
    with sesion_sistema(engine) as s:
        cid, clave, prefijo = repo.crear_clave(s, nombre, alcance)
    return {"id": cid, "clave": clave, "prefijo": prefijo, "alcance": alcance}


def claves(engine: Engine) -> list[dict]:
    with sesion_sistema(engine) as s:
        return repo.claves(s)


def revocar_clave(engine: Engine, clave_id: int) -> None:
    with sesion_sistema(engine) as s:
        if not repo.revocar_clave(s, clave_id):
            raise NoEncontrada(clave_id)


def validar_clave(engine: Engine, clave: str) -> dict | None:
    with sesion_sistema(engine) as s:
        return repo.buscar_clave(s, clave)
