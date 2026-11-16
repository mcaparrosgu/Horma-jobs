"""Servicio de `/costes`: coste y errores por día, agente y modelo, tareas en error y alertas (RF-4.7)."""
from sqlalchemy import Engine

from horma.web.db import sesion_sistema
from horma.web.repositories import costes as repo

DIAS = 30


def resumen(engine: Engine) -> dict:
    with sesion_sistema(engine) as s:
        return {"dias": repo.por_dia(s, DIAS), "agentes": repo.por_agente(s, DIAS),
                "modelos": repo.por_modelo(s, DIAS), "tareas_en_error": repo.tareas_en_error(s),
                "alertas": repo.alertas_recientes(s)}
