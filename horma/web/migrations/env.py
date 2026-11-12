import os

from alembic import context
from sqlalchemy import create_engine

config = context.config


def _url() -> str:
    url = config.get_main_option("sqlalchemy.url") or os.environ.get("DATABASE_URL_MIGRACIONES", "")
    if not url:
        from dotenv import dotenv_values

        url = dotenv_values(".env").get("DATABASE_URL_MIGRACIONES", "")
    if not url:
        raise RuntimeError("Falta DATABASE_URL_MIGRACIONES (rol horma_migrador).")
    return url


engine = create_engine(_url())
with engine.connect() as conexion:
    context.configure(connection=conexion, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
