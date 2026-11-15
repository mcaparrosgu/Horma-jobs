"""Fase 2: la usuaria puede quitar un CV subido (DELETE en `cv_archivos`, solo sus filas por RLS).

Revision ID: 0004
Revises: 0003
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("GRANT DELETE ON cv_archivos TO horma_app;")


def downgrade() -> None:
    op.execute("REVOKE DELETE ON cv_archivos FROM horma_app;")
