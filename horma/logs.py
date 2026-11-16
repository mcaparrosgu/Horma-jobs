"""Registros (log): nivel por `LOG_LEVEL` y motivos de error sin texto de la usuaria (RF-4.7c)."""
import logging

from horma.config import ajustes
from horma.flows.base import ErrorDePaso
from horma.llm.gateway import SalidaInvalida
from horma.llm.metricas import TopeSuperado

_NIVELES = {"debug", "info", "warning", "error", "critical"}


def configurar_logs() -> int:
    """Aplica `LOG_LEVEL` (un nombre inválido cae a INFO). Devuelve el nivel aplicado."""
    nombre = ajustes().log_level.strip().lower()
    nivel = getattr(logging, nombre.upper()) if nombre in _NIVELES else logging.INFO
    logging.basicConfig(level=nivel, force=True)
    logging.getLogger().setLevel(nivel)
    return nivel


def _causa_segura(causa: BaseException | str) -> str:
    """Texto fijo escrito por el código (str o ValueError exacto); de cualquier otra excepción, solo
    su clase, porque su mensaje puede llevar datos de la usuaria (p. ej. un ValidationError)."""
    if isinstance(causa, str):
        return causa
    if type(causa) is ValueError:
        return str(causa)
    return type(causa).__name__


def motivo_seguro(e: BaseException) -> str:
    """Motivo apto para `tareas.motivo_error` y el log: paso, tipo de error y mensaje fijo."""
    if isinstance(e, TopeSuperado):
        return "tope de coste superado"
    if isinstance(e, SalidaInvalida):
        return "la salida del modelo no cumple el formato esperado"
    if isinstance(e, ErrorDePaso):
        causa = motivo_seguro(e.causa) if isinstance(e.causa, BaseException) else e.causa
        return f"paso {e.paso}: {causa}"
    return _causa_segura(e)
