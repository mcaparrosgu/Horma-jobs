"""Guía de estilo de la usuaria (RF-5.6d). Con sesión; escribir pide CSRF."""
from fastapi import APIRouter, Depends, HTTPException, Request

from horma.schemas.estilo import GuiaEstilo
from horma.tools.depurar_guia import motivos_de_rechazo
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.db import sesion_de
from horma.web.repositories import estilo as repo
from horma.web.repositories import tareas
from horma.web.services import estilo as servicio

router = APIRouter()


@router.get("/api/estilo")
def ver(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        fila = repo.guia(s)
        return {"guia": fila["guia"] if fila else None, "origen": fila["origen"] if fila else None,
                "analizada_en": fila["analizada_en"] if fila else None,
                "analizando": tareas.sin_terminar(s, servicio.TAREA, usuaria_id),
                "hay_documentos": bool(repo.documentos(s))}


@router.post("/api/estilo/analizar", status_code=202, dependencies=[Depends(exigir_csrf)])
def analizar(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """«Volver a analizar mi estilo»: solo al pulsar el botón; sustituye a la guía actual."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        if not repo.documentos(s):
            raise HTTPException(status_code=409,
                                detail="Sube un CV o una carta tuya para analizar tu estilo.")
        tarea = servicio.encolar(s, usuaria_id)
        if tarea is None:
            raise HTTPException(status_code=409, detail="Ya se está analizando tu estilo.")
    return {"tarea_id": tarea}


@router.put("/api/estilo", dependencies=[Depends(exigir_csrf)])
def editar(guia: GuiaEstilo, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Lo que ella edita manda: se guarda con origen «usuaria» y no se recalcula solo."""
    if motivos := motivos_de_rechazo(guia):
        raise HTTPException(status_code=422, detail=f"Esa guía no se puede guardar: {'; '.join(motivos)}.")
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        repo.guardar(s, usuaria_id, guia, "usuaria")
    return {"guia": guia.model_dump(mode="json"), "origen": "usuaria"}
