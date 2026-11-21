"""Avance de las tareas de la usuaria (RF-8.7)."""
from sqlalchemy import Engine

from horma.web.db import sesion_de
from horma.web.repositories import tareas


def activas(engine: Engine, usuaria_id: int, tipo: list[str] | None) -> list[dict]:
    with sesion_de(engine, usuaria_id) as s:
        return tareas.activas(s, usuaria_id, tipo)


def una(engine: Engine, usuaria_id: int, tarea_id: int) -> dict | None:
    with sesion_de(engine, usuaria_id) as s:
        return tareas.una(s, tarea_id)
