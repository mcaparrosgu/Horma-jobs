"""Medición de destinos del envío (RF-11.1): solo administradoras o la clave de ingesta (consola)."""
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from horma.web.auth.sesion import exigir_admin
from horma.web.routers.ingesta import admin_o_ingesta
from horma.web.services import envios as servicio

router = APIRouter()
ESTATICOS = Path(__file__).resolve().parent.parent / "static"


@router.get("/envios", include_in_schema=False, dependencies=[Depends(exigir_admin)])
def pagina():
    return FileResponse(ESTATICOS / "envios.html")


@router.get("/api/admin/envios/medicion", dependencies=[Depends(admin_o_ingesta)])
def medicion(request: Request):
    """Tabla portal · ofertas · exige cuenta del catálogo real. Puede tardar: sigue redirecciones."""
    return servicio.medir_destinos(request.app.state.engine)
