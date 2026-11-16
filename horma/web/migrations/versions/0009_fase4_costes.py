"""Fase 4, bloque F: función para contar las tareas en error por tipo sin ver filas de otras usuarias.

`tareas` tiene RLS por usuaria; la pantalla `/costes` (solo admins) necesita solo el recuento por tipo.
La función devuelve únicamente (tipo, n): sin ids de usuaria, de tarea ni motivos.

Revision ID: 0009
Revises: 0008
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

UPGRADE = """
CREATE FUNCTION tareas_en_error_por_tipo() RETURNS TABLE (tipo text, n bigint)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
    SELECT tipo, count(*) FROM tareas WHERE estado = 'error' GROUP BY tipo ORDER BY tipo
$$;
REVOKE ALL ON FUNCTION tareas_en_error_por_tipo() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION tareas_en_error_por_tipo() TO horma_app;
"""

DOWNGRADE = "DROP FUNCTION IF EXISTS tareas_en_error_por_tipo();"


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
