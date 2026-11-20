"""Avance de las tareas (RF-8.7). La pantalla pregunta cada pocos segundos; el motivo sale ya saneado."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from horma.web.auth.sesion import usuaria_actual
from horma.web.db import sesion_de
from horma.web.repositories import tareas

router = APIRouter()


@router.get("/api/tareas/activas")
def activas(request: Request, usuaria_id: int = Depends(usuaria_actual),
            tipo: Annotated[list[str] | None, Query()] = None):
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        return {"tareas": tareas.activas(s, usuaria_id, tipo)}


@router.get("/api/tareas/{tarea_id}")
def una(tarea_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        fila = tareas.una(s, tarea_id)
    if fila is None:
        raise HTTPException(status_code=404, detail="No existe esa tarea")
    return fila
