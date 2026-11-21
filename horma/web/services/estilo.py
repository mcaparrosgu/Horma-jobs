"""Guía de estilo: se calcula una sola vez y solo se vuelve a calcular si ella lo pide (RF-5.6d)."""
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from horma.config import ajustes
from horma.schemas.estilo import GuiaEstilo
from horma.web.db import sesion_de
from horma.web.repositories import estilo as repo
from horma.web.repositories import tareas
from horma.web.services import presupuesto

TAREA = "analizar_estilo"


def encolar(s: Session, usuaria_id: int) -> int | None:
    """Encola el análisis salvo que ya haya uno por terminar. La carga es el id de la usuaria."""
    if tareas.sin_terminar(s, TAREA, usuaria_id):
        return None
    a = ajustes()
    return presupuesto.encolar(s, usuaria_id, TAREA, usuaria_id, a.tope_coste_estilo, a.tope_reintentos_tarea)


def encolar_si_no_hay_guia(s: Session, usuaria_id: int) -> int | None:
    """La primera vez que hay documentos suyos. Si ya hay guía (del modelo o editada por ella), no."""
    if repo.guia(s) is not None or not repo.documentos(s):
        return None
    try:
        return encolar(s, usuaria_id)
    except presupuesto.SinPresupuesto:  # sin presupuesto, solo con el botón otro día
        return None


class SinDocumentos(Exception):
    """No hay ningún CV ni carta suyos que analizar."""


class YaAnalizando(Exception):
    """Ya hay un análisis de estilo en marcha."""


def ver(engine: Engine, usuaria_id: int) -> dict:
    with sesion_de(engine, usuaria_id) as s:
        fila = repo.guia(s)
        return {"guia": fila["guia"] if fila else None, "origen": fila["origen"] if fila else None,
                "analizada_en": fila["analizada_en"] if fila else None,
                "analizando": tareas.sin_terminar(s, TAREA, usuaria_id),
                "hay_documentos": bool(repo.documentos(s))}


def analizar(engine: Engine, usuaria_id: int) -> int:
    """«Volver a analizar mi estilo»: solo al pulsar el botón; sustituye a la guía actual."""
    with sesion_de(engine, usuaria_id) as s:
        if not repo.documentos(s):
            raise SinDocumentos
        tarea = encolar(s, usuaria_id)
    if tarea is None:
        raise YaAnalizando
    return tarea


def guardar(engine: Engine, usuaria_id: int, guia: GuiaEstilo) -> None:
    """Lo que ella edita manda: origen «usuaria», y no se recalcula solo."""
    with sesion_de(engine, usuaria_id) as s:
        if tareas.sin_terminar(s, TAREA, usuaria_id):   # el worker la pisaría al terminar
            raise YaAnalizando
        repo.guardar(s, usuaria_id, guia, "usuaria")
