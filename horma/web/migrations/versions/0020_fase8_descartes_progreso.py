"""Fase 8: avance de las tareas (RF-8.7), índice para los topes del día y descartes de ofertas (RF-8.6).

Revision ID: 0020
Revises: 0019
"""
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE tareas ADD COLUMN progreso smallint NOT NULL DEFAULT 0
        CHECK (progreso BETWEEN 0 AND 100);
    ALTER TABLE tareas ADD COLUMN actualizada_en timestamptz NOT NULL DEFAULT now();
    CREATE INDEX tareas_usuaria_tipo_idx ON tareas (usuaria_id, tipo, creada_en);

    CREATE TABLE descartes (
        usuaria_id integer NOT NULL REFERENCES usuarias(id) ON DELETE CASCADE,
        oferta_id integer NOT NULL REFERENCES ofertas(id) ON DELETE CASCADE,
        creada_en timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (usuaria_id, oferta_id)
    );
    ALTER TABLE descartes ENABLE ROW LEVEL SECURITY;
    CREATE POLICY propia ON descartes FOR ALL
        USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
    GRANT SELECT, INSERT, DELETE ON descartes TO horma_app;
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE descartes;
    DROP INDEX tareas_usuaria_tipo_idx;
    ALTER TABLE tareas DROP COLUMN actualizada_en;
    ALTER TABLE tareas DROP COLUMN progreso;
    """)
