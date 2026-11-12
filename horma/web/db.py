"""Acceso a Postgres: una transacción por operación, con la usuaria fijada para RLS."""
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from horma.config import ajustes


@lru_cache
def motor() -> Engine:
    url = ajustes().database_url
    if not url:
        raise RuntimeError("Falta DATABASE_URL (rol horma_app).")
    return create_engine(url, pool_pre_ping=True)


@contextmanager
def sesion_de(engine: Engine, usuaria_id: int) -> Iterator[Session]:
    """Sesión cuya transacción solo ve los datos de `usuaria_id` (RLS)."""
    with Session(engine) as s, s.begin():
        s.execute(text("select set_config('app.usuaria_id', :u, true)"), {"u": str(usuaria_id)})
        yield s


@contextmanager
def sesion_sin_usuaria(engine: Engine) -> Iterator[Session]:
    """Sesión sin usuaria: con RLS no ve filas; solo sirve para las funciones de acceso."""
    with Session(engine) as s, s.begin():
        yield s
