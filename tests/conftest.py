"""Fixtures de base de datos: Postgres de Compose, base `<POSTGRES_DB>_test`."""
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from horma.config import ajustes

RAIZ = Path(__file__).resolve().parent.parent


def _url_test(url: str) -> str:
    u = make_url(url)
    return u.set(database=f"{u.database}_test").render_as_string(hide_password=False)


def _urls() -> tuple[str, str]:
    a = ajustes()
    migracion = os.environ.get("DATABASE_URL_MIGRACIONES")
    if not (a.database_url and migracion):
        from dotenv import dotenv_values

        migracion = dotenv_values(RAIZ / ".env").get("DATABASE_URL_MIGRACIONES", "")
    return _url_test(a.database_url), _url_test(migracion)


@pytest.fixture(scope="session")
def urls_bd():
    app, mig = _urls()
    try:
        e = create_engine(mig)
        with e.connect() as c:
            c.execute(text("select 1"))
        e.dispose()
    except Exception as exc:  # sin Postgres: se salta en local, falla en CI
        if os.environ.get("CI"):
            raise
        pytest.skip(f"Postgres no disponible (docker compose up -d postgres): {exc}")
    return app, mig


@pytest.fixture(scope="session")
def bd_migrada(urls_bd):
    """Esquema limpio y migrado con el rol propietario."""
    from alembic import command
    from alembic.config import Config

    app, mig = urls_bd
    e = create_engine(mig, isolation_level="AUTOCOMMIT")
    with e.connect() as c:
        c.execute(text("DROP SCHEMA public CASCADE"))
        c.execute(text("CREATE SCHEMA public AUTHORIZATION horma_migrador"))
        c.execute(text("GRANT USAGE ON SCHEMA public TO horma_app"))
    e.dispose()
    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", mig)
    command.upgrade(cfg, "head")
    return urls_bd


@pytest.fixture
def motor_app(bd_migrada):
    e = create_engine(bd_migrada[0])
    yield e
    e.dispose()


@pytest.fixture
def motor_migrador(bd_migrada):
    e = create_engine(bd_migrada[1])
    yield e
    e.dispose()


@pytest.fixture(autouse=False)
def bd_limpia(motor_migrador):
    """Tablas vacías y la semilla de fuentes recién sembrada."""
    from horma.web.semilla import sembrar_fuentes

    with motor_migrador.begin() as c:
        c.execute(text("TRUNCATE origen, ofertas, tareas, llm_llamadas, usuarias, fuentes, "
                       "calificaciones_fuente, ejecuciones_ingesta, claves_api, cv_archivos, perfiles, "
                       "preferencias, cv_base, matches RESTART IDENTITY CASCADE"))
        sembrar_fuentes(c)
