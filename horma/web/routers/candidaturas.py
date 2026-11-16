"""Candidaturas (RF-3.1 a RF-3.10): API con sesión; escribir pide CSRF. La lógica vive en el servicio."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from horma.schemas.candidatura import MAX_CANAL_OTRO, Canal, MotivoCierre
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.limites import limite_candidaturas
from horma.web.services import candidaturas as servicio

router = APIRouter()


class Nueva(BaseModel):
    oferta_id: int
    repetir: bool = False  # confirma preparar otra aunque ya haya una cerrada para la oferta


class Edicion(BaseModel):
    cv_contenido: str | None = Field(default=None, min_length=1, max_length=20000)
    carta_contenido: str | None = Field(default=None, min_length=1, max_length=20000)


class Envio(BaseModel):
    fecha: date | None = None  # sin fecha, la de hoy
    canal: Canal | None = None
    canal_otro: str | None = Field(default=None, max_length=MAX_CANAL_OTRO)


class Cierre(BaseModel):
    motivo: MotivoCierre


def _llamar(funcion, request: Request, usuaria_id: int, *args):
    try:
        return funcion(request.app.state.engine, usuaria_id, *args)
    except servicio.ErrorCandidatura as e:
        raise HTTPException(status_code=e.estado, detail=e.motivo) from e


@router.post("/api/candidaturas", status_code=202,
             dependencies=[Depends(exigir_csrf), Depends(limite_candidaturas)])
def crear(datos: Nueva, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Crea la candidatura en borrador y encola su preparación; el CV base lo elige Horma (RF-3.1b)."""
    return _llamar(servicio.crear, request, usuaria_id, datos.oferta_id, datos.repetir)


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


@router.post("/api/candidaturas/{candidatura_id}/aprobar", dependencies=[Depends(exigir_csrf)])
def aprobar(candidatura_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _llamar(servicio.aprobar, request, usuaria_id, candidatura_id)


@router.post("/api/candidaturas/{candidatura_id}/reintentar", status_code=202,
             dependencies=[Depends(exigir_csrf), Depends(limite_candidaturas)])
def reintentar(candidatura_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _llamar(servicio.reintentar, request, usuaria_id, candidatura_id)


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
    pdf = _llamar(servicio.documento_pdf, request, usuaria_id, candidatura_id, cual)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{cual}.pdf"'})


@router.get("/api/candidaturas/{candidatura_id}/cv.pdf")
def cv_pdf(candidatura_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _descarga("cv", candidatura_id, request, usuaria_id)


@router.get("/api/candidaturas/{candidatura_id}/carta.pdf")
def carta_pdf(candidatura_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _descarga("carta", candidatura_id, request, usuaria_id)
