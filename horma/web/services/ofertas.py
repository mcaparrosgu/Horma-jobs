"""Servicio de ofertas: alta en el catálogo y encolado del flujo procesar_oferta (RF-1.3, RF-1.4)."""
from sqlalchemy import Engine

from horma.config import ajustes
from horma.web.db import sesion_sistema
from horma.web.repositories import ingesta as repo_ingesta
from horma.web.repositories import ofertas as repo
from horma.web.repositories import tareas

TIPO_TAREA = "procesar_oferta"


class FuenteNoValida(Exception):
    """La fuente indicada no existe o no está activa."""


def recibir(engine: Engine, texto: str, *, fuente: str | None = None, clave_id: int | None = None,
            id_externo: str | None = None, url: str | None = None,
            tope_coste: float | None = None, tope_reintentos: int | None = None) -> dict:
    """Guarda la oferta cruda y, si es nueva, encola su procesado. La carga de la cola es el id."""
    a = ajustes()
    with sesion_sistema(engine) as s:
        fuente_id = None
        if fuente:
            f = repo_ingesta.fuente(s, nombre=fuente)
            if not f or not f["activa"]:
                raise FuenteNoValida(fuente)
            fuente_id = f["id"]
        oferta_id, estado, nueva = repo.crear(s, texto, fuente_id=fuente_id, clave_id=clave_id,
                                              id_externo=id_externo, url=url)
        if nueva:
            tareas.encolar(s, None, TIPO_TAREA, oferta_id,
                           a.tope_coste_tarea if tope_coste is None else tope_coste,
                           a.tope_reintentos_tarea if tope_reintentos is None else tope_reintentos)
    return {"id": oferta_id, "estado": estado, "nueva": nueva}
