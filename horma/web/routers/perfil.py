"""Perfil con versiones (RF-2.2 a 2.4): verlo con sus orígenes y pendientes, responder o corregir."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.services import perfil as servicio

router = APIRouter()


class Respuesta(BaseModel):
    indice: int
    dato: dict | None = None


class Correccion(BaseModel):
    campo: str
    indice: int | None = None
    dato: dict | None = None


@router.get("/api/perfil")
def ver(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return servicio.ver(request.app.state.engine, usuaria_id)


@router.get("/api/perfil/cv.pdf")
def cv_completo_pdf(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """PDF de «Tu CV completo» (RF-10.4): el CV maestro del perfil vigente, sin modelo. Solo su dueña."""
    try:
        pdf = servicio.cv_completo_pdf(request.app.state.engine, usuaria_id)
    except servicio.SinPerfil as e:
        raise HTTPException(status_code=404, detail="Aún no tienes un perfil: sube un CV primero.") from e
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="cv-completo.pdf"'})


def _cambiar(request: Request, usuaria_id: int, accion):
    try:
        return accion(request.app.state.engine, usuaria_id)
    except servicio.SinPerfil as e:
        raise HTTPException(status_code=409, detail="Aún no tienes un perfil: sube un CV primero.") from e
    except servicio.DatoNoValido as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/api/perfil/respuestas", status_code=201, dependencies=[Depends(exigir_csrf)])
def responder(datos: Respuesta, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _cambiar(request, usuaria_id, lambda e, u: servicio.responder(e, u, datos.indice, datos.dato))


@router.patch("/api/perfil/datos", status_code=201, dependencies=[Depends(exigir_csrf)])
def corregir(datos: Correccion, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _cambiar(request, usuaria_id,
                    lambda e, u: servicio.corregir(e, u, datos.campo, datos.indice, datos.dato))


class Visto(BaseModel):
    clave: str = Field(min_length=1, max_length=300)
    huella: str = Field(min_length=1, max_length=64)


class Longitud(BaseModel):
    longitud: Literal["mantener", "sintetizar"]


@router.get("/api/perfil/avisos")
def avisos(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Huecos y avisos por reglas del perfil vigente, sin los que ella dio por vistos (RF-9.1c, RF-9.2)."""
    return servicio.avisos(request.app.state.engine, usuaria_id)


@router.put("/api/perfil/avisos/visto", dependencies=[Depends(exigir_csrf)])
def dar_por_visto(datos: Visto, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    servicio.dar_por_visto(request.app.state.engine, usuaria_id, datos.clave, datos.huella)
    return {"ok": True}


@router.put("/api/perfil/longitud", dependencies=[Depends(exigir_csrf)])
def elegir_longitud(datos: Longitud, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    servicio.elegir_longitud(request.app.state.engine, usuaria_id, datos.longitud)
    return {"longitud": datos.longitud}
