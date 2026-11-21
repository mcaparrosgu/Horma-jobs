"""Presupuesto diario por usuaria (RF-10.9): se comprueba aquí, al encolar, y en ningún otro sitio."""
from sqlalchemy.orm import Session

from horma.config import ajustes
from horma.web.repositories import tareas

MIN_USD = 0.01  # por debajo de esto no merece la pena lanzar una tarea
TEXTO = "Hoy ya hemos trabajado todo lo posible para ti. Mañana seguimos."


class SinPresupuesto(Exception):
    """La usuaria ya ha gastado hoy su presupuesto: no se encola nada hasta mañana (RF-10.9c)."""


def restante_hoy(s: Session, usuaria_id: int) -> float:
    """Lo que queda hoy del presupuesto, en USD (nunca negativo)."""
    return max(0.0, round(ajustes().presupuesto_diario_usd - tareas.gasto_hoy(s, usuaria_id), 6))


def encolar(s: Session, usuaria_id: int, tipo: str, entidad_id: int, tope_tipo: float,
            tope_reintentos: int) -> int:
    """Único punto de encolado de las tareas de una usuaria. El tope de la tarea es lo que quede del día,
    sin pasar del tope de su tipo (la red de seguridad de RT-14)."""
    queda = restante_hoy(s, usuaria_id)
    if queda < MIN_USD:
        raise SinPresupuesto(TEXTO)
    return tareas.encolar(s, usuaria_id, tipo, entidad_id, min(tope_tipo, queda), tope_reintentos)


def encolar_oferta_propia(s: Session, usuaria_id: int, oferta_id: int, tope_tipo: float,
                          tope_reintentos: int) -> int:
    """El análisis de una oferta que ella añadió es una tarea del sistema (sin usuaria), pero gasta de su
    presupuesto: `tareas.gasto_hoy` lo cuenta por la dueña de la oferta."""
    queda = restante_hoy(s, usuaria_id)
    if queda < MIN_USD:
        raise SinPresupuesto(TEXTO)
    return tareas.encolar(s, None, "procesar_oferta", oferta_id, min(tope_tipo, queda), tope_reintentos)
