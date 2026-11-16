"""Pantalla de costes y errores, solo para administradoras (RF-4.7)."""
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from horma.web.auth.sesion import exigir_admin
from horma.web.services import costes as servicio

router = APIRouter()
ESTATICOS = Path(__file__).resolve().parent.parent / "static"


@router.get("/costes", include_in_schema=False, dependencies=[Depends(exigir_admin)])
def pagina():
    return FileResponse(ESTATICOS / "costes.html")


@router.get("/api/costes", dependencies=[Depends(exigir_admin)])
def resumen(request: Request):
    return servicio.resumen(request.app.state.engine)
