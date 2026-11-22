"""CV subidos (RF-2.1). Todo con sesión; escribir pide CSRF. Los endpoints del CV base se quitaron en la
simplificación (RF-10.3e): las tablas se conservan."""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from horma.config import ajustes
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.limites import limite_subida_cv
from horma.web.services import cv as servicio

router = APIRouter()


class Nombre(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)


class EscritoPorElla(BaseModel):
    escrito_por_ella: bool


def _nombre(valor: str) -> str:
    return valor.strip()


@router.post("/api/cv", status_code=201, dependencies=[Depends(exigir_csrf), Depends(limite_subida_cv)])
def subir(request: Request, archivo: Annotated[UploadFile, File()], nombre: str | None = Form(default=None),
          clase: str = Form(default="fuente"), escrito_por_ella: bool = Form(default=False),
          usuaria_id: int = Depends(usuaria_actual)):
    contenido = archivo.file.read(ajustes().max_cv_bytes + 1)
    try:
        return servicio.subir(request.app.state.engine, usuaria_id, contenido=contenido,
                              nombre_original=archivo.filename or "cv", nombre=nombre, clase=clase,
                              escrito_por_ella=escrito_por_ella)
    except servicio.ArchivoRechazado as e:
        raise HTTPException(status_code=e.estado, detail=e.motivo) from e
    except servicio.NombreRepetido as e:
        raise HTTPException(status_code=409, detail="Ya tienes un CV con ese nombre.") from e


@router.get("/api/cv")
def listar(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return servicio.listar(request.app.state.engine, usuaria_id)


@router.patch("/api/cv/{cv_id}", dependencies=[Depends(exigir_csrf)])
def renombrar(cv_id: int, datos: Nombre, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    nombre = _nombre(datos.nombre)
    try:
        if not servicio.renombrar(request.app.state.engine, usuaria_id, cv_id, nombre):
            raise HTTPException(status_code=404, detail="No existe ese CV")
    except servicio.NombreRepetido as e:
        raise HTTPException(status_code=409, detail="Ya tienes un CV con ese nombre.") from e
    return {"id": cv_id, "nombre": nombre}


@router.put("/api/cv/{cv_id}/escrito-por-ella", dependencies=[Depends(exigir_csrf)])
def marcar_escrito_por_ella(cv_id: int, datos: EscritoPorElla, request: Request,
                            usuaria_id: int = Depends(usuaria_actual)):
    """«Lo escribí yo»: los documentos así marcados pesan más en la guía de estilo (RF-5.6b)."""
    motor = request.app.state.engine
    if not servicio.marcar_escrito_por_ella(motor, usuaria_id, cv_id, datos.escrito_por_ella):
        raise HTTPException(status_code=404, detail="No existe ese CV")
    return {"id": cv_id, "escrito_por_ella": datos.escrito_por_ella}


@router.delete("/api/cv/{cv_id}", dependencies=[Depends(exigir_csrf)])
def eliminar(cv_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    if not servicio.eliminar(request.app.state.engine, usuaria_id, cv_id):
        raise HTTPException(status_code=404, detail="No existe ese CV")
    return {"id": cv_id}


@router.get("/api/cv/{cv_id}/archivo")
def descargar(cv_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Solo la dueña (RLS): para las demás, el CV no existe."""
    hallado = servicio.archivo(request.app.state.engine, usuaria_id, cv_id)
    if hallado is None:
        raise HTTPException(status_code=404, detail="No existe ese CV")
    cv, ruta = hallado
    return FileResponse(ruta, media_type=servicio.MEDIA[cv["tipo"]], filename=cv["nombre_original"])


@router.get("/api/cv/{cv_id}/ver")
def ver(cv_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """El CV en línea, para el visor de la página (RF-2.1c). Solo la dueña (RLS)."""
    hallado = servicio.archivo(request.app.state.engine, usuaria_id, cv_id)
    if hallado is None:
        raise HTTPException(status_code=404, detail="No existe ese CV")
    cv, ruta = hallado
    if cv["tipo"] == "docx":
        raise HTTPException(status_code=415, detail="Los DOCX no se pueden ver en el navegador: descárgalo.")
    medio = "application/pdf" if cv["tipo"] == "pdf" else "text/plain; charset=utf-8"
    return FileResponse(ruta, media_type=medio, content_disposition_type="inline")
