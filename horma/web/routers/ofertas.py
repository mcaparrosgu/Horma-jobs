from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from horma.config import ajustes
from horma.web.auth import claves
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.db import sesion_de
from horma.web.queue import worker
from horma.web.repositories import ofertas as repo
from horma.web.services import ofertas as servicio

router = APIRouter()


class NuevaOferta(BaseModel):
    texto: str = Field(min_length=1, max_length=20000)
    fuente: str | None = Field(default=None, max_length=41)
    id_externo: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=2000)


@router.post("/ofertas", status_code=201)
def crear(datos: NuevaOferta, request: Request, response: Response):
    """Con sesión y CSRF (web) o con clave de API (ingesta o empresa). RF-1.3."""
    clave_id = None
    if claves.portador(request):
        clave = claves.clave_valida(request, {"ofertas", "ingesta"})
        if datos.fuente and clave.alcance != "ingesta":
            raise HTTPException(status_code=403, detail="Solo la ingesta entrega en nombre de una fuente")
        claves.contar_ritmo(request, clave)
        clave_id = clave.id
    else:
        exigir_csrf(request, usuaria_actual(request))
        if datos.fuente:
            raise HTTPException(status_code=403, detail="Solo la ingesta entrega en nombre de una fuente")
    engine = request.app.state.engine
    try:
        r = servicio.recibir(engine, datos.texto, fuente=datos.fuente, clave_id=clave_id,
                             id_externo=datos.id_externo, url=datos.url)
    except servicio.FuenteNoValida as e:
        raise HTTPException(status_code=409, detail=f"Fuente no válida o inactiva: {e}") from e
    if not r["nueva"]:
        response.status_code = 200
    elif ajustes().horma_flujo_en_linea:  # solo desarrollo: sin cola ni worker aparte
        r["estado"] = "procesada" if worker.procesar_una(engine) == "hecha" else "pendiente"
    return r


@router.get("/ofertas/total")
def total(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Cuántas ofertas hay en el catálogo (todas, no solo las listadas), por estado."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        por_estado = repo.por_estado(s)
    return {"total": sum(por_estado.values()), "por_estado": por_estado}


@router.get("/ofertas")
def listar(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """El catálogo común con su auditoría y su taxonomía."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        return repo.listar(s)
