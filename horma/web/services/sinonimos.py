"""Las otras formas de cada puesto marcado (RF-12.4c): se piden al modelo una vez, en el worker."""
from sqlalchemy.orm import Session

from horma.config import ajustes
from horma.schemas.preferencias import Preferencias
from horma.web.repositories import perfiles
from horma.web.repositories import tareas as repo_tareas
from horma.web.services import recalcular_notas

_MAX_FORMAS, _MAX_LARGO = 8, 80


def pendientes(prefs: Preferencias) -> list[str]:
    return [p for p in dict.fromkeys(prefs.puestos) if p not in prefs.sinonimos]


def encolar_si_faltan(s: Session, usuaria_id: int) -> None:
    if pendientes(perfiles.preferencias(s)) and not repo_tareas.sin_terminar(s, "sinonimos", usuaria_id):
        a = ajustes()
        repo_tareas.encolar(s, usuaria_id, "sinonimos", usuaria_id, a.tope_coste_tarea, a.llm_reintentos)


def guardar(s: Session, usuaria_id: int, pedidos: list[str], respuesta: dict[str, list[str]]) -> None:
    """Guarda solo las formas; un puesto sin respuesta queda vacío para no volver a pedirlo."""
    prefs = perfiles.preferencias(s)
    for puesto in pedidos:
        formas = [f.strip() for f in respuesta.get(puesto, []) if 0 < len(f.strip()) <= _MAX_LARGO]
        prefs.sinonimos[puesto] = formas[:_MAX_FORMAS]
    perfiles.guardar_preferencias(s, usuaria_id, prefs)
    recalcular_notas.recalcular(s)
