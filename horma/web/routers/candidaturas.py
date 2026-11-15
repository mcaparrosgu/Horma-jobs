"""Candidaturas (RF-3.1 a RF-3.10): API con sesión; escribir pide CSRF. La lógica vive en el servicio."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, Field

from horma.schemas.candidatura import MAX_CANAL_OTRO, Canal, Documento, MotivoCierre
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.services import candidaturas as servicio

router = APIRouter()


class Nueva(BaseModel):
    oferta_id: int


class Edicion(BaseModel):
    cv_contenido: str | None = Field(default=None, min_length=1, max_length=20000)
    carta_contenido: str | None = Field(default=None, min_length=1, max_length=20000)


class GuardarCvBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)


class Aprobacion(BaseModel):
    documento: Documento
    cv_estetico_id: int | None = None
    avisos_revisados: bool = False


class Envio(BaseModel):
    fecha: date
    canal: Canal
    canal_otro: str | None = Field(default=None, max_length=MAX_CANAL_OTRO)


class Cierre(BaseModel):
    motivo: MotivoCierre


class Respuesta(BaseModel):
    texto: str = Field(min_length=1, max_length=20000)


def _llamar(funcion, request: Request, usuaria_id: int, *args):
    try:
        return funcion(request.app.state.engine, usuaria_id, *args)
    except servicio.ErrorCandidatura as e:
        raise HTTPException(status_code=e.estado, detail=e.motivo) from e


@router.post("/api/candidaturas", status_code=202, dependencies=[Depends(exigir_csrf)])
def crear(datos: Nueva, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Crea la candidatura en borrador y encola su preparación; el CV base lo elige Horma (RF-3.1b)."""
    return _llamar(servicio.crear, request, usuaria_id, datos.oferta_id)


@router.get("/api/candidaturas")
def tablero(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _llamar(servicio.tablero, request, usuaria_id)


@router.get("/api/candidaturas/{candidatura_id}")
def detalle(candidatura_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _llamar(servicio.detalle, request, usuaria_id, candidatura_id)


@router.patch("/api/candidaturas/{candidatura_id}", dependencies=[Depends(exigir_csrf)])
def editar(candidatura_id: int, datos: Edicion, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Solo en borrador y sin modelo: los avisos se recalculan con las herramientas de código."""
    if datos.cv_contenido is None and datos.carta_contenido is None:
        raise HTTPException(status_code=422, detail="Indica el CV o la carta nuevos.")
    return _llamar(servicio.editar, request, usuaria_id, candidatura_id, datos.cv_contenido,
                   datos.carta_contenido)


@router.post("/api/candidaturas/{candidatura_id}/guardar-cv-base", dependencies=[Depends(exigir_csrf)])
def guardar_cv_base(candidatura_id: int, datos: GuardarCvBase, request: Request,
                    usuaria_id: int = Depends(usuaria_actual)):
    return _llamar(servicio.guardar_cv_base, request, usuaria_id, candidatura_id, datos.nombre.strip())


@router.post("/api/candidaturas/{candidatura_id}/aprobar", dependencies=[Depends(exigir_csrf)])
def aprobar(candidatura_id: int, datos: Aprobacion, request: Request,
            usuaria_id: int = Depends(usuaria_actual)):
    return _llamar(servicio.aprobar, request, usuaria_id, candidatura_id, datos.documento,
                   datos.cv_estetico_id, datos.avisos_revisados)


@router.post("/api/candidaturas/{candidatura_id}/enviada", dependencies=[Depends(exigir_csrf)])
def enviada(candidatura_id: int, datos: Envio, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _llamar(servicio.marcar_enviada, request, usuaria_id, candidatura_id, datos.fecha, datos.canal,
                   datos.canal_otro)


@router.post("/api/candidaturas/{candidatura_id}/entrevista", dependencies=[Depends(exigir_csrf)])
def entrevista(candidatura_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _llamar(servicio.pasar_a_entrevista, request, usuaria_id, candidatura_id)


@router.post("/api/candidaturas/{candidatura_id}/cerrar", dependencies=[Depends(exigir_csrf)])
def cerrar(candidatura_id: int, datos: Cierre, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _llamar(servicio.cerrar, request, usuaria_id, candidatura_id, datos.motivo)


def _descarga(cual: Literal["cv", "carta"], candidatura_id: int, request: Request, usuaria_id: int):
    tipo, valor = _llamar(servicio.documento_pdf, request, usuaria_id, candidatura_id, cual)
    if tipo == "estetico":  # su archivo original, tal cual
        return RedirectResponse(f"/api/cv/{valor}/archivo", status_code=307)
    return Response(valor, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{cual}.pdf"'})


@router.get("/api/candidaturas/{candidatura_id}/cv.pdf")
def cv_pdf(candidatura_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _descarga("cv", candidatura_id, request, usuaria_id)


@router.get("/api/candidaturas/{candidatura_id}/carta.pdf")
def carta_pdf(candidatura_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _descarga("carta", candidatura_id, request, usuaria_id)


@router.post("/api/candidaturas/{candidatura_id}/respuesta", status_code=202,
             dependencies=[Depends(exigir_csrf)])
def pegar_respuesta(candidatura_id: int, datos: Respuesta, request: Request,
                    usuaria_id: int = Depends(usuaria_actual)):
    """El texto vive en la fila solo hasta que el worker lo clasifica; después no se conserva."""
    return _llamar(servicio.pegar_respuesta, request, usuaria_id, candidatura_id, datos.texto)


@router.post("/api/candidaturas/{candidatura_id}/respuesta/confirmar", dependencies=[Depends(exigir_csrf)])
def confirmar_respuesta(candidatura_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _llamar(servicio.confirmar_respuesta, request, usuaria_id, candidatura_id)


@router.post("/api/candidaturas/{candidatura_id}/respuesta/descartar", dependencies=[Depends(exigir_csrf)])
def descartar_respuesta(candidatura_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _llamar(servicio.descartar_respuesta, request, usuaria_id, candidatura_id)
