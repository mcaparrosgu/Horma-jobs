"""Fase 7: modalidad de la oferta (remoto, híbrido o presencial) para que «Solo remoto» sea estricto.

Las ofertas ya guardadas quedan sin modalidad (no se reprocesan): con «Solo remoto» no salen.

Revision ID: 0019
Revises: 0018
"""
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE ofertas ADD COLUMN modalidad text "
               "CHECK (modalidad IN ('remoto', 'hibrido', 'presencial'))")


def downgrade() -> None:
    op.execute("ALTER TABLE ofertas DROP COLUMN modalidad")
