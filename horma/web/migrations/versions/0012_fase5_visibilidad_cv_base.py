"""Fase 5, bloque B: visibilidad de cada experiencia en un CV base (RF-5.1g).

`cv_base.visibilidad` = {clave_experiencia: "completa" | "condensada" | "oculta"}; vacío = automático.

Revision ID: 0012
Revises: 0011
"""
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE cv_base ADD COLUMN visibilidad jsonb NOT NULL DEFAULT '{}'::jsonb;")


def downgrade() -> None:
    op.execute("ALTER TABLE cv_base DROP COLUMN visibilidad;")
