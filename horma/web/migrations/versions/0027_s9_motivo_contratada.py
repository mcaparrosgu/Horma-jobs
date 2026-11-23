"""S9: «Me han contratado» cierra la candidatura con el motivo «contratada» (RF-10.17).

Revision ID: 0027
Revises: 0026
"""
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE candidaturas DROP CONSTRAINT candidaturas_motivo_cierre_check")
    op.execute("ALTER TABLE candidaturas ADD CONSTRAINT candidaturas_motivo_cierre_check "
               "CHECK (motivo_cierre IN ('rechazo', 'descartada', 'retirada', 'contratada'))")


def downgrade() -> None:
    op.execute("UPDATE candidaturas SET motivo_cierre = 'retirada' WHERE motivo_cierre = 'contratada'")
    op.execute("ALTER TABLE candidaturas DROP CONSTRAINT candidaturas_motivo_cierre_check")
    op.execute("ALTER TABLE candidaturas ADD CONSTRAINT candidaturas_motivo_cierre_check "
               "CHECK (motivo_cierre IN ('rechazo', 'descartada', 'retirada'))")
