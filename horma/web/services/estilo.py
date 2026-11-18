"""Guía de estilo: se calcula una sola vez y solo se vuelve a calcular si ella lo pide (RF-5.6d)."""
from sqlalchemy.orm import Session

from horma.config import ajustes
from horma.web.repositories import estilo as repo
from horma.web.repositories import tareas

TAREA = "analizar_estilo"


def encolar(s: Session, usuaria_id: int) -> int | None:
    """Encola el análisis salvo que ya haya uno por terminar. La carga es el id de la usuaria."""
    if tareas.sin_terminar(s, TAREA, usuaria_id):
        return None
    a = ajustes()
    return tareas.encolar(s, usuaria_id, TAREA, usuaria_id, a.tope_coste_estilo, a.tope_reintentos_tarea)


def encolar_si_no_hay_guia(s: Session, usuaria_id: int) -> int | None:
    """La primera vez que hay documentos suyos. Si ya hay guía (del modelo o editada por ella), no."""
    if repo.guia(s) is not None or not repo.documentos(s):
        return None
    return encolar(s, usuaria_id)
