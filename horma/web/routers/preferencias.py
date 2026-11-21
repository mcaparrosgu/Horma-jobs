"""Preferencias de búsqueda y las opciones de las casillas con su contador (RF-2.8, RF-2.8b)."""
from fastapi import APIRouter, Depends, Request

from horma.schemas.filtros import CONTRATOS, IDIOMAS, PAISES
from horma.schemas.preferencias import Preferencias
from horma.schemas.taxonomia import FAMILIAS, NIVELES, SECTORES
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.services import preferencias as servicio

router = APIRouter()

_CATALOGO = {"familias": FAMILIAS, "sectores": SECTORES, "niveles": NIVELES, "contratos": CONTRATOS,
             "paises": PAISES, "idiomas": IDIOMAS}


@router.get("/api/preferencias")
def ver(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return servicio.ver(request.app.state.engine, usuaria_id).model_dump(mode="json")


@router.put("/api/preferencias", dependencies=[Depends(exigir_csrf)])
def guardar(nuevas: Preferencias, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Lo que ella cambia pasa a ser suyo: el origen de ese grupo es «usuaria» y el CV ya no lo pisa."""
    return servicio.guardar(request.app.state.engine, usuaria_id, nuevas).model_dump(mode="json")


@router.get("/api/preferencias/titulos")
def titulos(request: Request, q: str = "", usuaria_id: int = Depends(usuaria_actual)):
    """Autocompletar «Añadir un puesto»: títulos reales de las ofertas que contienen lo escrito."""
    return {"titulos": servicio.titulos(request.app.state.engine, usuaria_id, q)}


@router.get("/api/preferencias/opciones")
def opciones(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Cada casilla con cuántas ofertas recomendables tiene el catálogo; las vacías, con 0."""
    total, cuentas, puestos = servicio.contadores(request.app.state.engine, usuaria_id)
    return {"total": total, "puestos": puestos,
            "grupos": {g: [{"valor": v, "n": cuentas.get(g, {}).get(v, 0)} for v in valores]
                       for g, valores in _CATALOGO.items()}}
