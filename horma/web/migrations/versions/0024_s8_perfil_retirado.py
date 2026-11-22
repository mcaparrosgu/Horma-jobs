"""S8: un perfil puede quedar «retirado» (RF-10.14).

Al borrar el último CV, el perfil deja de estar vigente pero sus versiones se conservan: las candidaturas y
las compatibilidades ya hechas apuntan a ellas.

`perfiles_aplazados()` da (usuaria, perfil) de las versiones reservadas que esperan su `perfilar` porque no había
presupuesto al borrar un CV. Solo en modo sistema: el worker no ve las filas de las usuarias por la RLS.

Revision ID: 0024
Revises: 0023
"""
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE perfiles DROP CONSTRAINT perfiles_estado_check;
    ALTER TABLE perfiles ADD CONSTRAINT perfiles_estado_check
        CHECK (estado IN ('pendiente', 'hecha', 'error', 'retirado'));
    CREATE FUNCTION perfiles_aplazados() RETURNS TABLE (usuaria_id integer, perfil_id integer)
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
        SELECT p.usuaria_id, p.id FROM perfiles p
        WHERE current_setting('app.sistema', true) = 'on' AND p.estado = 'pendiente'
          AND NOT EXISTS (SELECT 1 FROM tareas t WHERE t.tipo = 'perfilar' AND t.entidad_id = p.id)
        ORDER BY p.id
    $$;
    REVOKE ALL ON FUNCTION perfiles_aplazados() FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION perfiles_aplazados() TO horma_app;
    """)


def downgrade() -> None:
    op.execute("""
    DROP FUNCTION perfiles_aplazados();
    UPDATE perfiles SET estado = 'hecha' WHERE estado = 'retirado';
    ALTER TABLE perfiles DROP CONSTRAINT perfiles_estado_check;
    ALTER TABLE perfiles ADD CONSTRAINT perfiles_estado_check
        CHECK (estado IN ('pendiente', 'hecha', 'error'));
    """)
