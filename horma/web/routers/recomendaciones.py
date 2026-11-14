"""Ofertas recomendadas (RF-2.11 a 2.13, RF-2.15c).

`GET /api/recomendaciones` solo filtra y ordena lo ya puntuado: no llama al modelo ni encola nada.
Puntuar lo que falta es `POST /api/recomendar`."""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, ValidationError

from horma.config import ajustes
from horma.schemas.preferencias import Preferencias
from horma.tools.buscar_ofertas import buscar_ofertas
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.db import sesion_de
from horma.web.repositories import matches as repo
from horma.web.repositories import ofertas as repo_ofertas
from horma.web.repositories import perfiles, tareas

router = APIRouter()


class Correccion(BaseModel):
    nota: int | None = Field(default=None, ge=0, le=100)
    comentario: str = Field(min_length=1, max_length=1000)


def _salario(f: dict) -> str | None:
    """El texto tal como lo dice la oferta (P17): nunca el valor convertido."""
    if f["salario_rango"]:
        return f["salario_rango"]
    if f["salario_minimo"] is None and f["salario_maximo"] is None:
        return None
    partes = [f"{float(v):g}" for v in (f["salario_minimo"], f["salario_maximo"]) if v is not None]
    return " - ".join(dict.fromkeys(partes)) + (f" {f['salario_moneda']}" if f["salario_moneda"] else "")


def _rango(valor: str | None, base: Preferencias) -> tuple[int, int]:
    if not valor:
        return base.rango_min, base.rango_max
    try:
        a, b = (int(x) for x in valor.split("-"))
        Preferencias(rango_min=a, rango_max=b)
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=422, detail="El rango debe ser «mínimo-máximo», de 0 a 100.") from e
    return a, b


@router.post("/api/recomendar", status_code=202, dependencies=[Depends(exigir_csrf)])
def recomendar(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Puntúa solo lo que falta para la versión vigente del perfil (RF-2.12)."""
    a = ajustes()
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        fila = perfiles.vigente(s)
        if fila is None:
            raise HTTPException(status_code=409, detail="Aún no tienes un perfil: sube un CV primero.")
        if tareas.sin_terminar(s, "recomendar", fila["id"]):
            raise HTTPException(status_code=409, detail="Ya se está puntuando.")
        tarea = tareas.encolar(s, usuaria_id, "recomendar", fila["id"], a.tope_coste_recomendar,
                               a.tope_reintentos_tarea)
    return {"tarea_id": tarea, "perfil_version": fila["version"]}


@router.get("/api/recomendaciones")
def listar(request: Request, usuaria_id: int = Depends(usuaria_actual),
           rango: str | None = None, orden: str | None = None,
           familias: Annotated[list[str] | None, Query()] = None,
           sectores: Annotated[list[str] | None, Query()] = None,
           contratos: Annotated[list[str] | None, Query()] = None,
           niveles: Annotated[list[str] | None, Query()] = None,
           paises: Annotated[list[str] | None, Query()] = None,
           idiomas: Annotated[list[str] | None, Query()] = None,
           solo_remoto: bool | None = None, solo_salario: bool | None = None,
           sueldo_minimo: float | None = None):
    """Filtra y ordena lo ya puntuado; lo que aún no tiene nota sale «sin puntuar». Lo que no se pasa
    en la URL sale de las preferencias guardadas."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        guardadas = perfiles.preferencias(s)
        cambios = {k: v for k, v in {
            "familias": familias, "sectores": sectores, "contratos": contratos, "niveles": niveles,
            "paises": paises, "idiomas": idiomas, "solo_remoto": solo_remoto,
            "solo_salario": solo_salario, "sueldo_minimo": sueldo_minimo, "orden": orden}.items()
            if v is not None}
        try:
            prefs = Preferencias.model_validate({**guardadas.model_dump(), **cambios})
        except ValidationError as e:
            raise HTTPException(status_code=422, detail="Algún filtro no es válido.") from e
        minimo, maximo = _rango(rango, guardadas)
        vigente = perfiles.vigente(s)
        taxonomia = perfiles.perfil_modelo(vigente).taxonomia if vigente else None
        ids = repo.ids_candidatas(s, buscar_ofertas(prefs, taxonomia))
        filas = repo.listado(s, ids)
    salida = []
    for f in filas:
        if f["nota"] is not None and not minimo <= f["nota"] <= maximo:
            continue
        salida.append({**f, "salario": _salario(f), "sin_puntuar": f["nota"] is None})
    if prefs.orden == "compatibles":  # lo puntuado primero, de más a menos nota; el resto, al final
        salida.sort(key=lambda f: -1 if f["nota"] is None else f["nota"], reverse=True)
    return {"total": len(salida), "rango": [minimo, maximo],
            "sin_puntuar": sum(1 for f in salida if f["sin_puntuar"]), "recomendaciones": salida}


@router.post("/api/matches/{oferta_id}/correccion", dependencies=[Depends(exigir_csrf)])
def corregir(oferta_id: int, datos: Correccion, request: Request,
             usuaria_id: int = Depends(usuaria_actual)):
    """Se guarda junto al match. No entra en `evals/` hasta que Mar lo revise con un comando (P4)."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        m = repo.uno(s, oferta_id)
        if m is None:
            raise HTTPException(status_code=404, detail="Esa oferta aún no tiene nota.")
        repo.guardar_correccion(s, oferta_id, m["perfil_version"],
                                json.dumps(datos.model_dump(), ensure_ascii=False))
    return {"oferta_id": oferta_id, **datos.model_dump()}


@router.get("/api/matches/{oferta_id}/exportar")
def exportar(oferta_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """El caso corregido, con el formato de `evals/recomendacion/casos/` (entrada y esperado)."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        m = repo.uno(s, oferta_id)
        if m is None or m["correccion"] is None:
            raise HTTPException(status_code=404, detail="Esa oferta no tiene ninguna corrección.")
        fila = perfiles.por_version(s, m["perfil_version"])
        oferta = repo_ofertas.completas(s, [oferta_id]).get(oferta_id)
        prefs = perfiles.preferencias(s)
    perfil = perfiles.perfil_modelo(fila).model_copy(update={"instrucciones_embebidas": []})
    c = m["correccion"]
    return {"entrada": {"perfil": perfil.model_dump(mode="json"),
                        "preferencias": prefs.model_dump(mode="json"),
                        "oferta": oferta.model_dump(mode="json") if oferta else None},
            "esperado": {"nota": c["nota"] if c.get("nota") is not None else m["nota"],
                         "condiciones": m["condiciones"], "motivo": c["comentario"]},
            "modelo": {"nota": m["nota"], "condiciones": m["condiciones"],
                       "explicacion": m["explicacion"]}}
