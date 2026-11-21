"""CV subidos (RF-2.1). Todo con sesión; escribir pide CSRF. Los endpoints del CV base se quitaron en la
simplificación (RF-10.3e): las tablas se conservan."""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from horma.config import ajustes
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.db import sesion_de
from horma.web.limites import limite_subida_cv
from horma.web.repositories import cv as repo
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
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        return repo.listar(s)


@router.patch("/api/cv/{cv_id}", dependencies=[Depends(exigir_csrf)])
def renombrar(cv_id: int, datos: Nombre, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    nombre = _nombre(datos.nombre)
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        if repo.uno(s, cv_id) is None:
            raise HTTPException(status_code=404, detail="No existe ese CV")
        if repo.nombre_en_uso(s, nombre, excepto_cv=cv_id):
            raise HTTPException(status_code=409, detail="Ya tienes un CV con ese nombre.")
        repo.renombrar(s, cv_id, nombre)
    return {"id": cv_id, "nombre": nombre}


@router.put("/api/cv/{cv_id}/escrito-por-ella", dependencies=[Depends(exigir_csrf)])
def marcar_escrito_por_ella(cv_id: int, datos: EscritoPorElla, request: Request,
                            usuaria_id: int = Depends(usuaria_actual)):
    """«Lo escribí yo»: los documentos así marcados pesan más en la guía de estilo (RF-5.6b)."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        if not repo.marcar_escrito_por_ella(s, cv_id, datos.escrito_por_ella):
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
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        cv = repo.uno(s, cv_id)
    ruta = servicio.carpeta() / cv["ruta"] if cv else None
    if not cv or not ruta.is_file():
        raise HTTPException(status_code=404, detail="No existe ese CV")
    return FileResponse(ruta, media_type=servicio.MEDIA[cv["tipo"]], filename=cv["nombre_original"])


@router.get("/api/cv/{cv_id}/ver")
def ver(cv_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """El CV en línea, para el visor de la página (RF-2.1c). Solo la dueña (RLS)."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        cv = repo.uno(s, cv_id)
    ruta = servicio.carpeta() / cv["ruta"] if cv else None
    if not cv or not ruta.is_file():
        raise HTTPException(status_code=404, detail="No existe ese CV")
    if cv["tipo"] == "docx":
        raise HTTPException(status_code=415, detail="Los DOCX no se pueden ver en el navegador: descárgalo.")
    medio = "application/pdf" if cv["tipo"] == "pdf" else "text/plain; charset=utf-8"
    return FileResponse(ruta, media_type=medio, content_disposition_type="inline")
