"""CV subidos y CV base (RF-2.1, RF-2.1b, RF-2.9, RF-2.10). Todo con sesión; escribir pide CSRF."""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from horma.config import ajustes
from horma.tools.visibilidad_cv import VALORES
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.db import sesion_de
from horma.web.limites import limite_subida_cv
from horma.web.repositories import cv as repo
from horma.web.repositories import perfiles, tareas
from horma.web.services import cv as servicio

router = APIRouter()


class Nombre(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)


class EscritoPorElla(BaseModel):
    escrito_por_ella: bool


class EdicionCvBase(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    contenido: str | None = Field(default=None, min_length=1, max_length=20000)


class VisibilidadCvBase(BaseModel):
    visibilidad: dict[str, str] = Field(default_factory=dict, max_length=60)


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


# --- CV base -----------------------------------------------------------------------------------
@router.post("/api/cv-base", status_code=202, dependencies=[Depends(exigir_csrf)])
def generar_cv_base(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Se genera a petición, una sola vez por versión del perfil (RF-2.9); nunca por sí solo."""
    a = ajustes()
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        fila = perfiles.vigente(s)
        if fila is None:
            raise HTTPException(status_code=409, detail="Aún no tienes un perfil: sube un CV primero.")
        if perfiles.hay_cv_base_hecho(s, fila["version"]):
            raise HTTPException(status_code=409, detail="Ya has generado los CV base de esta versión "
                                                        "del perfil.")
        if tareas.sin_terminar(s, "generar_cv_base", fila["id"]):
            raise HTTPException(status_code=409, detail="Ya se están generando.")
        tarea = tareas.encolar(s, usuaria_id, "generar_cv_base", fila["id"], a.tope_coste_cv_base,
                               a.tope_reintentos_tarea)
    return {"tarea_id": tarea, "perfil_version": fila["version"]}


@router.post("/api/cv-base/{cv_id}/regenerar", status_code=202, dependencies=[Depends(exigir_csrf)])
def regenerar_cv_base(cv_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Vuelve a generar ese CV base con el perfil vigente. Solo al pulsar el botón (RF-5.1e)."""
    a = ajustes()
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        if perfiles.datos_para_regenerar(s, cv_id) is None:
            raise HTTPException(status_code=404, detail="No existe ese CV base.")
        if tareas.sin_terminar(s, "regenerar_cv_base", cv_id):
            raise HTTPException(status_code=409, detail="Ya se está regenerando.")
        tarea = tareas.encolar(s, usuaria_id, "regenerar_cv_base", cv_id, a.tope_coste_cv_base,
                               a.tope_reintentos_tarea)
    return {"tarea_id": tarea}


@router.put("/api/cv-base/{cv_id}/visibilidad", dependencies=[Depends(exigir_csrf)])
def visibilidad_cv_base(cv_id: int, datos: VisibilidadCvBase, request: Request,
                        usuaria_id: int = Depends(usuaria_actual)):
    """Marca cada experiencia del CV base como completa, condensada u oculta (RF-5.1g). Lo que se
    envíe sustituye lo marcado antes; vacío = todo automático. Se aplica al regenerar."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        if perfiles.datos_para_regenerar(s, cv_id) is None:
            raise HTTPException(status_code=404, detail="No existe ese CV base.")
        claves = {e["clave"] for e in perfiles.experiencias_marcables(s)}
        for clave, valor in datos.visibilidad.items():
            if valor not in VALORES or clave not in claves:
                raise HTTPException(status_code=422, detail="Esa marca no es válida: elige completa, "
                                    "condensada u oculta para una experiencia de tu perfil.")
        perfiles.guardar_visibilidad(s, cv_id, datos.visibilidad)
    return {"visibilidad": datos.visibilidad}


@router.get("/api/cv-base")
def listar_cv_base(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Los CV base verificados. Los rechazados no salen como CV: solo su motivo, en `avisos`."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        filas = perfiles.listar_cv_base(s)
        vigente = perfiles.vigente(s)
        en_curso = bool(vigente) and tareas.sin_terminar(s, "generar_cv_base", vigente["id"])
        experiencias = perfiles.experiencias_marcables(s)
        regenerando = [f["id"] for f in filas
                       if f["estado"] == "hecho" and tareas.sin_terminar(s, "regenerar_cv_base", f["id"])]
    return {"cv_base": [f for f in filas if f["estado"] == "hecho"],
            "avisos": [{"nombre": f["nombre"], "estado": f["estado"], "motivo": f["motivo_error"],
                        "perfil_version": f["perfil_version"]}
                       for f in filas if f["estado"] != "hecho" and not f["desfasado"]],
            "generando": en_curso, "regenerando": regenerando, "experiencias": experiencias}


@router.patch("/api/cv-base/{cv_id}", dependencies=[Depends(exigir_csrf)])
def editar_cv_base(cv_id: int, datos: EdicionCvBase, request: Request,
                   usuaria_id: int = Depends(usuaria_actual)):
    """Cambia el nombre y/o el texto del CV base: es de ella y lo puede retocar."""
    if datos.nombre is None and datos.contenido is None:
        raise HTTPException(status_code=422, detail="Indica el nombre o el texto nuevo.")
    nombre = _nombre(datos.nombre) if datos.nombre is not None else None
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        if nombre and repo.nombre_en_uso(s, nombre, excepto_base=cv_id):
            raise HTTPException(status_code=409, detail="Ya tienes un CV con ese nombre.")
        if not perfiles.editar_cv_base(s, cv_id, nombre, datos.contenido):
            raise HTTPException(status_code=404, detail="No existe ese CV base")
    return {"id": cv_id, "nombre": nombre}


@router.get("/api/cv-base/{cv_id}/versiones")
def versiones_cv_base(cv_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """El historial (RF-3.8d): de la más reciente a la más antigua, con las líneas marcadas."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        versiones = perfiles.versiones_cv_base(s, cv_id)
    if versiones is None:
        raise HTTPException(status_code=404, detail="No existe ese CV base")
    return {"versiones": versiones}


@router.post("/api/cv-base/{cv_id}/versiones/{version_id}/restaurar", dependencies=[Depends(exigir_csrf)])
def restaurar_cv_base(cv_id: int, version_id: int, request: Request,
                      usuaria_id: int = Depends(usuaria_actual)):
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        if not perfiles.restaurar_cv_base(s, cv_id, version_id):
            raise HTTPException(status_code=404, detail="No existe esa versión del CV base")
    return {"id": cv_id, "version_id": version_id}


@router.delete("/api/cv-base/{cv_id}", dependencies=[Depends(exigir_csrf)])
def eliminar_cv_base(cv_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        if not perfiles.eliminar_cv_base(s, cv_id):
            raise HTTPException(status_code=404, detail="No existe ese CV base")
    return {"id": cv_id}
