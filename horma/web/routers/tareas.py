"""Avance de las tareas (RF-8.7). La pantalla pregunta cada pocos segundos; el motivo sale ya saneado."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from horma.web.auth.sesion import usuaria_actual
from horma.web.services import tareas

router = APIRouter()

# Tareas que la usuaria ve en la cabecera (RF-10.8) y la pantalla a la que lleva cada una.
PANTALLA_DE_TIPO = {
    "perfilar": "/perfil", "clasificar_perfil": "/perfil", "analizar_estilo": "/perfil",
    "recomendar": "/ofertas", "puntuar_propias": "/ofertas", "puntuar_una": "/ofertas",
    "leer_url": "/ofertas",
}


def _url(t: dict) -> str | None:
    if t["tipo"] == "candidatura":
        return f"/candidaturas/{t['entidad_id']}"
    return PANTALLA_DE_TIPO.get(t["tipo"])


@router.get("/api/tareas/activas")
def activas(request: Request, usuaria_id: int = Depends(usuaria_actual),
            tipo: Annotated[list[str] | None, Query()] = None):
    filas = tareas.activas(request.app.state.engine, usuaria_id, tipo)
    salida = []
    for t in filas:
        url = _url(t)
        if url is not None:   # lo que la usuaria no ve (p. ej. interno) no sale
            salida.append({**t, "url": url})
    return {"tareas": salida}


@router.get("/api/tareas/{tarea_id}")
def una(tarea_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    fila = tareas.una(request.app.state.engine, usuaria_id, tarea_id)
    if fila is None:
        raise HTTPException(status_code=404, detail="No existe esa tarea")
    return fila
