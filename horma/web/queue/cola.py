"""Cola de tareas en Postgres. La carga son ids; `reclamar_tarea()` usa SKIP LOCKED."""
from sqlalchemy import Engine, text

from horma.web.db import sesion_sin_usuaria


def reclamar(engine: Engine) -> dict | None:
    """Toma la siguiente tarea pendiente (y la marca en curso) o devuelve None."""
    with sesion_sin_usuaria(engine) as s:
        fila = s.execute(text("select * from reclamar_tarea()")).mappings().first()
    return dict(fila) if fila else None


def reencolar_interrumpidas(engine: Engine) -> int:
    """Al arrancar el worker: las tareas que quedaron «en_curso» vuelven a «pendiente». Devuelve cuántas."""
    with sesion_sin_usuaria(engine) as s:
        return s.execute(text("select reencolar_interrumpidas()")).scalar_one()
