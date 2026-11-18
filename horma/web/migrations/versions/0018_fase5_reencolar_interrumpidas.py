"""Fase 5: recuperar las tareas que quedaron «en_curso» cuando el worker se paró (reinicio, caída).

Sin esto, una tarea interrumpida se quedaba en curso para siempre: la pantalla mostraba «Regenerando…» sin
fin y la API respondía «Ya se está regenerando». El worker llama a la función al arrancar y las devuelve a
«pendiente» (hay un solo worker, así que ninguna en curso es de otro proceso vivo).

Revision ID: 0018
Revises: 0017
"""
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE FUNCTION reencolar_interrumpidas() RETURNS integer
LANGUAGE sql SECURITY DEFINER SET search_path = public AS $$
    WITH r AS (UPDATE tareas SET estado = 'pendiente' WHERE estado = 'en_curso' RETURNING 1)
    SELECT count(*)::integer FROM r
$$;
REVOKE ALL ON FUNCTION reencolar_interrumpidas() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION reencolar_interrumpidas() TO horma_app;
""")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS reencolar_interrumpidas()")
