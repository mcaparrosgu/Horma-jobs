"""Fase 5, bloque C: ofertas privadas de una usuaria (RF-5.3c).

`ofertas.usuaria_id` nulo = catálogo común (lo ven todas); con valor = oferta añadida por esa usuaria,
que solo ve su dueña. Lo garantiza la política de lectura (RLS), no solo la consulta.

Revision ID: 0013
Revises: 0012
"""
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE ofertas ADD COLUMN usuaria_id integer REFERENCES usuarias(id) ON DELETE CASCADE;
    CREATE INDEX ofertas_usuaria_idx ON ofertas (usuaria_id) WHERE usuaria_id IS NOT NULL;
    DROP POLICY lectura ON ofertas;
    CREATE POLICY lectura ON ofertas FOR SELECT USING (
        app_sistema()
        OR (app_usuaria() IS NOT NULL AND (usuaria_id IS NULL OR usuaria_id = app_usuaria())));
    -- Al procesar una oferta propia, el worker (modo sistema) encola la tarea de puntuarla a su dueña.
    CREATE POLICY alta_sistema ON tareas FOR INSERT WITH CHECK (app_sistema());
    CREATE POLICY lectura_sistema ON tareas FOR SELECT USING (app_sistema());
    """)


def downgrade() -> None:
    op.execute("""
    DROP POLICY alta_sistema ON tareas;
    DROP POLICY lectura_sistema ON tareas;
    DROP POLICY lectura ON ofertas;
    DELETE FROM ofertas WHERE usuaria_id IS NOT NULL;
    DROP INDEX ofertas_usuaria_idx;
    ALTER TABLE ofertas DROP COLUMN usuaria_id;
    CREATE POLICY lectura ON ofertas FOR SELECT USING (app_usuaria() IS NOT NULL OR app_sistema());
    """)
