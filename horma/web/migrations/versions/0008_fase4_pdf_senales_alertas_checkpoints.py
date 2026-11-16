"""Fase 4, bloque B: PDF guardados al aprobar, señales de entrada en las llamadas, alertas de coste y las
tablas del checkpointer de LangGraph (`PostgresSaver.setup()` con el rol migrador). Reversible: `downgrade`
quita todo, incluidas las tablas del checkpointer.

Las tablas del checkpointer no llevan RLS: no tienen columna de usuaria y solo las tocan el worker y la API.
Si una versión nueva de `langgraph-checkpoint-postgres` cambia su esquema, hará falta otra migración nuestra.

Revision ID: 0008
Revises: 0007
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

TABLAS_CHECKPOINT = "checkpoints, checkpoint_blobs, checkpoint_writes, checkpoint_migrations"

UPGRADE = """
ALTER TABLE candidaturas
    ADD COLUMN cv_pdf bytea,
    ADD COLUMN carta_pdf bytea,
    ADD COLUMN entregada_en timestamptz;

ALTER TABLE llm_llamadas ADD COLUMN senales_entrada text[] NOT NULL DEFAULT '{}';

CREATE TABLE alertas (
    id serial PRIMARY KEY,
    tipo text NOT NULL CHECK (tipo IN ('gasto_dia', 'tasa_errores')),
    valor numeric NOT NULL,
    umbral numeric NOT NULL,
    creada_en timestamptz NOT NULL DEFAULT now(),
    correo_enviado boolean NOT NULL DEFAULT false
);
CREATE INDEX alertas_tipo_dia_idx ON alertas (tipo, creada_en DESC);
ALTER TABLE alertas ENABLE ROW LEVEL SECURITY;
CREATE POLICY sistema ON alertas FOR ALL USING (app_sistema()) WITH CHECK (app_sistema());
GRANT SELECT, INSERT, UPDATE ON alertas TO horma_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO horma_app;
"""

PERMISOS_CHECKPOINT = f"GRANT SELECT, INSERT, UPDATE, DELETE ON {TABLAS_CHECKPOINT} TO horma_app;"

DOWNGRADE = f"""
DROP TABLE IF EXISTS {TABLAS_CHECKPOINT};
DROP TABLE IF EXISTS alertas;
ALTER TABLE llm_llamadas DROP COLUMN senales_entrada;
ALTER TABLE candidaturas DROP COLUMN cv_pdf, DROP COLUMN carta_pdf, DROP COLUMN entregada_en;
"""


def _crear_tablas_del_checkpointer() -> None:
    """`PostgresSaver.setup()` en su propia conexión autocommit y con el mismo rol que migra."""
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg import Connection
    from psycopg.rows import dict_row

    url = op.get_bind().engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    with Connection.connect(url, autocommit=True, prepare_threshold=0, row_factory=dict_row) as conexion:
        PostgresSaver(conexion).setup()


def upgrade() -> None:
    op.execute(UPGRADE)
    _crear_tablas_del_checkpointer()
    op.execute(PERMISOS_CHECKPOINT)


def downgrade() -> None:
    op.execute(DOWNGRADE)
