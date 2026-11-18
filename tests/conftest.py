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
                       "preferencias, cv_base, matches, candidaturas, candidatura_eventos, "
                       "cv_base_versiones, alertas, checkpoints, checkpoint_blobs, checkpoint_writes "
                       "RESTART IDENTITY CASCADE"))
        sembrar_fuentes(c)


@pytest.fixture
def limites_reales():
    """Marca de los tests de la fase 5 (T20-T23) que comprueban de verdad el mínimo y el máximo."""


@pytest.fixture(autouse=True)
def _sin_limite_de_palabras_salvo_que_se_pida(request, monkeypatch):
    """Los CV de los tests antiguos son de una o dos líneas: `validar_cv` (fase 5, RF-5.4) no les cuenta las
    palabras. Los tests que sí las cuentan piden `limites_reales`."""
    if "limites_reales" in request.fixturenames:
        return
    from horma.tools import validar_cv as modulo

    monkeypatch.setattr(modulo, "CV_PALABRAS_MIN", 0)
    monkeypatch.setattr(modulo, "CV_PALABRAS_MAX", 10**9)


@pytest.fixture
def juez_automatico(monkeypatch):
    """Los tests de la fase 2 y 5 del CV base no cuentan con la llamada al juez que suma RF-5.4d: la
    aprueba sola cuando la cola de respuestas simuladas está vacía o la siguiente es del generador, y no
    la apunta en `llamadas`. Si la cola trae una respuesta del juez, se usa esa."""
    from horma.llm.simulado import ProveedorSimulado

    original = ProveedorSimulado.generar
    aprobado = {"veredicto_cv": "aprobado", "veredicto_carta": "aprobado", "problemas": []}

    def generar(self, *, modelo, sistema, usuario, esquema, timeout):
        siguiente = self._respuestas[0] if self._respuestas else None
        auto = "revisor de candidaturas" in sistema and (
            siguiente is None or (isinstance(siguiente, dict) and "contenido" in siguiente))
        if auto:
            self._respuestas.insert(0, aprobado)
        r = original(self, modelo=modelo, sistema=sistema, usuario=usuario, esquema=esquema, timeout=timeout)
        if auto:
            self.llamadas.pop()
        return r

    monkeypatch.setattr(ProveedorSimulado, "generar", generar)
