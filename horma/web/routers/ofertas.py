from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from horma.config import ajustes
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.db import sesion_de
from horma.web.queue import worker
from horma.web.repositories import ofertas as repo
from horma.web.services import ofertas as servicio

router = APIRouter()


class NuevaOferta(BaseModel):
    texto: str = Field(min_length=1, max_length=20000)


@router.post("/ofertas", status_code=201, dependencies=[Depends(exigir_csrf)])
def crear(datos: NuevaOferta, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    engine = request.app.state.engine
    oferta_id = servicio.crear_y_encolar(engine, usuaria_id, datos.texto)
    estado = "pendiente"
    if ajustes().horma_flujo_en_linea:  # solo desarrollo: sin cola ni worker aparte
        worker.procesar_una(engine)
        estado = "procesada"
    return {"id": oferta_id, "estado": estado}


@router.get("/ofertas")
def listar(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        return repo.listar(s)
