"""Preferencias de búsqueda y las opciones de las casillas con su contador (RF-2.8, RF-2.8b)."""
from fastapi import APIRouter, Depends, Request

from horma.schemas.filtros import CONTRATOS, IDIOMAS, PAISES
from horma.schemas.preferencias import GRUPOS_CON_ORIGEN, Preferencias
from horma.schemas.taxonomia import FAMILIAS, NIVELES, SECTORES
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.db import sesion_de
from horma.web.repositories import ofertas as repo_ofertas
from horma.web.repositories import perfiles

router = APIRouter()

_CATALOGO = {"familias": FAMILIAS, "sectores": SECTORES, "niveles": NIVELES, "contratos": CONTRATOS,
             "paises": PAISES, "idiomas": IDIOMAS}


@router.get("/api/preferencias")
def ver(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        return perfiles.preferencias(s).model_dump(mode="json")


@router.put("/api/preferencias", dependencies=[Depends(exigir_csrf)])
def guardar(nuevas: Preferencias, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Lo que ella cambia pasa a ser suyo: el origen de ese grupo es «usuaria» y el CV ya no lo pisa."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        actual = perfiles.preferencias(s)
        origen = dict(actual.origen)
        for grupo in GRUPOS_CON_ORIGEN:
            if getattr(nuevas, grupo) != getattr(actual, grupo):
                origen[grupo] = "usuaria"
        nuevas = nuevas.model_copy(update={"origen": origen})
        perfiles.guardar_preferencias(s, usuaria_id, nuevas)
    return nuevas.model_dump(mode="json")


@router.get("/api/preferencias/opciones")
def opciones(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Cada casilla con cuántas ofertas recomendables tiene el catálogo; las vacías, con 0."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        total, cuentas = repo_ofertas.contadores(s)
    return {"total": total,
            "grupos": {g: [{"valor": v, "n": cuentas.get(g, {}).get(v, 0)} for v in valores]
                       for g, valores in _CATALOGO.items()}}
