"""Guía de estilo de la usuaria (RF-5.6d). Con sesión; escribir pide CSRF."""
from fastapi import APIRouter, Depends, HTTPException, Request

from horma.schemas.estilo import GuiaEstilo
from horma.tools.depurar_guia import motivos_de_rechazo
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.services import estilo as servicio

router = APIRouter()


@router.get("/api/estilo")
def ver(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return servicio.ver(request.app.state.engine, usuaria_id)


@router.post("/api/estilo/analizar", status_code=202, dependencies=[Depends(exigir_csrf)])
def analizar(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """«Volver a analizar mi estilo»: solo al pulsar el botón; sustituye a la guía actual."""
    try:
        tarea = servicio.analizar(request.app.state.engine, usuaria_id)
    except servicio.SinDocumentos as e:
        raise HTTPException(status_code=409,
                            detail="Sube un CV o una carta tuya para analizar tu estilo.") from e
    except servicio.YaAnalizando as e:
        raise HTTPException(status_code=409, detail="Ya se está analizando tu estilo.") from e
    return {"tarea_id": tarea}


@router.put("/api/estilo", dependencies=[Depends(exigir_csrf)])
def editar(guia: GuiaEstilo, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Lo que ella edita manda: se guarda con origen «usuaria» y no se recalcula solo."""
    if motivos := motivos_de_rechazo(guia):
        raise HTTPException(status_code=422, detail=f"Esa guía no se puede guardar: {'; '.join(motivos)}.")
    try:
        servicio.guardar(request.app.state.engine, usuaria_id, guia)
    except servicio.YaAnalizando as e:
        raise HTTPException(status_code=409,
                            detail="Se está analizando tu estilo. "
                                   "Cuando termine, podrás editar la guía.") from e
    return {"guia": guia.model_dump(mode="json"), "origen": "usuaria"}
