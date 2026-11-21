"""Ofertas recomendadas (RF-2.11 a 2.13, RF-8.4 a 8.6).

`GET /api/recomendaciones` solo lee lo ya puntuado: no llama al modelo ni encola nada.
Puntuar lo que falta es `POST /api/recomendar`."""
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text

from horma.config import ajustes
from horma.tools.buscar_ofertas import buscar_ofertas
from horma.tools.huella_perfil import huella_compatibilidad
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.db import sesion_de, sesion_sistema
from horma.web.repositories import candidaturas as repo_candidaturas
from horma.web.repositories import descartes, perfiles, tareas
from horma.web.repositories import matches as repo
from horma.web.repositories import ofertas as repo_ofertas
from horma.web.routers.ingesta import solo_ingesta
from horma.web.services import presupuesto

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



def _aviso_auditor(f: dict) -> str | None:
    """Señales de fraude que el auditor vio en una oferta propia (RF-5.3e). Solo avisa; no oculta."""
    avisos = []
    if f["fraude"]:
        senales = "; ".join(f["senales_fraude"] or [])
        avisos.append("Posibles señales de fraude" + (f": {senales}" if senales else ""))
    # «Fantasma» no se avisa: la oferta la ha pegado ella misma (RF-5.3e, enmienda P19, 20-nov).
    return ". ".join(avisos) or None


class Recomendar(BaseModel):
    motivo: Literal["abrir", "buscar"] = "abrir"


@router.post("/api/recomendar", dependencies=[Depends(exigir_csrf)])
def recomendar(request: Request, datos: Recomendar | None = None, usuaria_id: int = Depends(usuaria_actual)):
    """Puntúa lo que falta sin botón (RF-8.5). Siempre responde 200 con `{tarea_id}` o, si no lanza nada,
    `{tarea_id: null, motivo}`: `sin_perfil`, `en_marcha` (con la tarea en curso),
    `sin_pendientes`, `reciente`
    (solo al abrir: la última empezó hace menos de una hora) o `presupuesto` (RF-10.9c: hoy ya no queda)."""
    motivo_pedido = (datos or Recomendar()).motivo
    a = ajustes()
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        fila = perfiles.vigente(s)
        if fila is None:
            return {"tarea_id": None, "motivo": "sin_perfil"}
        if en_curso := tareas.activas(s, usuaria_id, ["recomendar"]):
            return {"tarea_id": en_curso[0]["id"], "motivo": "en_marcha"}
        if motivo_pedido == "abrir":
            ultima = tareas.ultima(s, usuaria_id, "recomendar")
            if ultima and ultima["hace_s"] < a.intervalo_recomendar_min * 60:
                return {"tarea_id": None, "motivo": "reciente"}
        prefs = perfiles.preferencias(s).model_copy(
            update={"rango_min": 40, "rango_max": 100, "orden": "compatibles"})
        taxonomia = perfiles.perfil_modelo(fila).taxonomia
        huella = huella_compatibilidad(perfiles.perfil_modelo(fila))
        excluir = repo.puntuadas(s, huella) + descartes.ids(s)
        if not repo.ids_candidatas(s, buscar_ofertas(prefs, taxonomia, excluir_ids=excluir, limite=1)):
            return {"tarea_id": None, "motivo": "sin_pendientes"}
        try:
            tarea = presupuesto.encolar(s, usuaria_id, "recomendar", fila["id"],
                                        a.tope_coste_recomendar, a.tope_reintentos_tarea)
        except presupuesto.SinPresupuesto:
            return {"tarea_id": None, "motivo": "presupuesto"}
    return {"tarea_id": tarea, "perfil_version": fila["version"]}


@router.post("/api/matches/{oferta_id}/puntuar", status_code=202, dependencies=[Depends(exigir_csrf)])
def puntuar_ahora(oferta_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """«Puntuar ahora» (RF-8.5e): puntúa solo esa oferta. Funciona con una tanda en marcha; gasta del
    presupuesto del día (RF-10.9): sin presupuesto, 429 `presupuesto`."""
    a = ajustes()
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        fila = perfiles.vigente(s)
        if fila is None:
            raise HTTPException(status_code=409, detail="Aún no tienes un perfil: sube un CV primero.")
        if not repo_ofertas.visible(s, oferta_id):
            raise HTTPException(status_code=404, detail="No existe esa oferta")
        if oferta_id in repo.puntuadas_de(s, huella_compatibilidad(perfiles.perfil_modelo(fila)),
                                          oferta_id) or tareas.sin_terminar(
                s, "puntuar_una", oferta_id):
            raise HTTPException(status_code=409, detail="Esa oferta ya tiene nota o se está puntuando.")
        tarea = presupuesto.encolar(s, usuaria_id, "puntuar_una", oferta_id, a.tope_coste_puntuar_una,
                                    a.tope_reintentos_tarea)
    return {"tarea_id": tarea}


@router.get("/api/recomendaciones")
def listar(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Todo lo que pasa «Qué buscas», con su nota (o «sin puntuar»), su candidatura y si está descartada.
    Rango, orden y estado los aplica el navegador (RF-8.4c): aquí no hay parámetros de vista."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        prefs = perfiles.preferencias(s)
        vigente = perfiles.vigente(s)
        taxonomia = perfiles.perfil_modelo(vigente).taxonomia if vigente else None
        ids = repo.ids_candidatas(s, buscar_ofertas(prefs, taxonomia))
        huella = huella_compatibilidad(perfiles.perfil_modelo(vigente)) if vigente else None
        filas = repo.listado(s, ids, huella)
    with sesion_sistema(request.app.state.engine) as s:
        repo_ofertas.marcar_fuente_desconocida(filas, s)
    salida = [{**f, "salario": _salario(f), "sin_puntuar": f["nota"] is None,
               "aviso_auditor": _aviso_auditor(f) if f["propia"] else None} for f in filas]
    return {"total": len(salida), "sin_puntuar": sum(1 for f in salida if f["sin_puntuar"]),
            "recomendaciones": salida}


@router.put("/api/descartes/{oferta_id}", dependencies=[Depends(exigir_csrf)])
def descartar(oferta_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Descarta una oferta: deja de puntuarse y sale de «Nuevas». No cabe con candidatura abierta (RF-8.6)."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        if not repo_ofertas.visible(s, oferta_id):
            raise HTTPException(status_code=404, detail="No existe esa oferta")
        if repo_candidaturas.hay_viva(s, oferta_id):
            raise HTTPException(status_code=409,
                                detail="Esa oferta tiene una candidatura abierta: ciérrala antes de descartarla.")  # noqa: E501
        descartes.descartar(s, usuaria_id, oferta_id)
    return {"oferta_id": oferta_id, "descartada": True}


@router.delete("/api/descartes/{oferta_id}", dependencies=[Depends(exigir_csrf)])
def recuperar(oferta_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        descartes.recuperar(s, oferta_id)
    return {"oferta_id": oferta_id, "descartada": False}


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


CATALOGO_MAX = 150


@router.get("/api/catalogo", dependencies=[Depends(solo_ingesta)])
def catalogo(request: Request):
    """Las ofertas recomendables y ya procesadas, comunes a todas las usuarias y sin ningún dato
    personal. Lo usa `horma recomendar` (clave de ingesta) para probar el matcher desde la consola."""
    with sesion_sistema(request.app.state.engine) as s:
        ids = [f[0] for f in s.execute(text(
            "select id from ofertas where estado = 'procesada' and recomendable "
            "and usuaria_id is null order by fecha_publicacion desc nulls last, id desc limit :n"),
            {"n": CATALOGO_MAX})]
        completas = repo_ofertas.completas(s, ids)
    return {"ofertas": [{"oferta_id": i, "oferta": completas[i].model_dump(mode="json")}
                        for i in ids if i in completas]}
