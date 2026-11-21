"""Recomendaciones: puntuar lo que falta, listar, descartar y corregir (RF-2.11 a 2.13, RF-8.4 a 8.6)."""
import json

from sqlalchemy import Engine

from horma.config import ajustes
from horma.tools.buscar_ofertas import buscar_ofertas
from horma.tools.huella_perfil import huella_compatibilidad
from horma.web.db import sesion_de, sesion_sistema
from horma.web.repositories import candidaturas as repo_candidaturas
from horma.web.repositories import descartes, perfiles, tareas
from horma.web.repositories import matches as repo
from horma.web.repositories import ofertas as repo_ofertas
from horma.web.services import presupuesto

CATALOGO_MAX = 150


class SinPerfil(Exception):
    """Aún no hay perfil."""


class OfertaNoExiste(Exception):
    """La oferta no existe o no es suya (RLS)."""


class YaPuntuada(Exception):
    """Esa oferta ya tiene nota o se está puntuando."""


class CandidaturaAbierta(Exception):
    """No se puede descartar una oferta con candidatura abierta (RF-8.6)."""


class SinNota(Exception):
    """La oferta aún no tiene match, o no tiene corrección."""


def recomendar(engine: Engine, usuaria_id: int, motivo_pedido: str) -> dict:
    """Puntúa lo que falta sin botón (RF-8.5). Devuelve `{tarea_id}` o `{tarea_id: None, motivo}`."""
    a = ajustes()
    with sesion_de(engine, usuaria_id) as s:
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


def puntuar_ahora(engine: Engine, usuaria_id: int, oferta_id: int) -> int:
    """«Puntuar ahora» (RF-8.5e): solo esa oferta. Sin presupuesto, `SinPresupuesto`."""
    a = ajustes()
    with sesion_de(engine, usuaria_id) as s:
        fila = perfiles.vigente(s)
        if fila is None:
            raise SinPerfil
        if not repo_ofertas.visible(s, oferta_id):
            raise OfertaNoExiste
        if oferta_id in repo.puntuadas_de(s, huella_compatibilidad(perfiles.perfil_modelo(fila)),
                                          oferta_id) or tareas.sin_terminar(s, "puntuar_una", oferta_id):
            raise YaPuntuada
        return presupuesto.encolar(s, usuaria_id, "puntuar_una", oferta_id, a.tope_coste_puntuar_una,
                                   a.tope_reintentos_tarea)


def listar(engine: Engine, usuaria_id: int) -> list[dict]:
    """Todo lo que pasa «Qué buscas», con su nota (o «sin puntuar»), su candidatura y si está descartada."""
    with sesion_de(engine, usuaria_id) as s:
        prefs = perfiles.preferencias(s)
        vigente = perfiles.vigente(s)
        taxonomia = perfiles.perfil_modelo(vigente).taxonomia if vigente else None
        ids = repo.ids_candidatas(s, buscar_ofertas(prefs, taxonomia))
        huella = huella_compatibilidad(perfiles.perfil_modelo(vigente)) if vigente else None
        filas = repo.listado(s, ids, huella)
    with sesion_sistema(engine) as s:
        repo_ofertas.marcar_fuente_desconocida(filas, s)
    return filas


def descartar(engine: Engine, usuaria_id: int, oferta_id: int) -> None:
    with sesion_de(engine, usuaria_id) as s:
        if not repo_ofertas.visible(s, oferta_id):
            raise OfertaNoExiste
        if repo_candidaturas.hay_viva(s, oferta_id):
            raise CandidaturaAbierta
        descartes.descartar(s, usuaria_id, oferta_id)


def recuperar(engine: Engine, usuaria_id: int, oferta_id: int) -> None:
    with sesion_de(engine, usuaria_id) as s:
        descartes.recuperar(s, oferta_id)


def corregir(engine: Engine, usuaria_id: int, oferta_id: int, correccion: dict) -> None:
    """Se guarda junto al match; no entra en `evals/` hasta que Mar lo revise (P4)."""
    with sesion_de(engine, usuaria_id) as s:
        m = repo.uno(s, oferta_id)
        if m is None:
            raise SinNota
        repo.guardar_correccion(s, oferta_id, m["perfil_version"],
                                json.dumps(correccion, ensure_ascii=False))


def exportar(engine: Engine, usuaria_id: int, oferta_id: int) -> dict:
    """El caso corregido, con el formato de `evals/recomendacion/casos/` (entrada y esperado)."""
    with sesion_de(engine, usuaria_id) as s:
        m = repo.uno(s, oferta_id)
        if m is None or m["correccion"] is None:
            raise SinNota
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


def catalogo_comun(engine: Engine) -> list[dict]:
    """Las ofertas recomendables y procesadas del catálogo común, sin ningún dato personal."""
    with sesion_sistema(engine) as s:
        ids = repo_ofertas.ids_recomendables_comunes(s, CATALOGO_MAX)
        completas = repo_ofertas.completas(s, ids)
    return [{"oferta_id": i, "oferta": completas[i].model_dump(mode="json")} for i in ids if i in completas]
