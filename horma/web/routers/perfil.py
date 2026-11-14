"""Perfil con versiones (RF-2.2 a 2.4): verlo con sus orígenes y pendientes, responder o corregir."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.db import sesion_de
from horma.web.repositories import perfiles
from horma.web.services import perfil as servicio

router = APIRouter()


class Respuesta(BaseModel):
    indice: int
    dato: dict | None = None


class Correccion(BaseModel):
    campo: Literal["experiencias", "formacion", "idiomas", "habilidades", "titular", "resumen"]
    indice: int | None = None
    dato: dict | None = None


@router.get("/api/perfil")
def ver(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        fila, ultima = perfiles.vigente(s), perfiles.ultima(s)
        if fila is None:
            return {"perfil": None, "origenes": [],
                    "construyendo": bool(ultima) and ultima["estado"] == "pendiente",
                    "error": ultima["motivo_error"] if ultima and ultima["estado"] == "error" else None}
        return {"perfil": perfiles.perfil_modelo(fila).model_dump(mode="json"),
                "origenes": perfiles.origenes(s, fila["id"]),
                "construyendo": ultima["version"] > fila["version"] and ultima["estado"] == "pendiente",
                "error": ultima["motivo_error"] if ultima["version"] > fila["version"]
                and ultima["estado"] == "error" else None}


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
