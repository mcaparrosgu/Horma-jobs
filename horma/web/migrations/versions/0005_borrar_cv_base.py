"""Fase 2: la usuaria puede borrar un CV base (DELETE en `cv_base`, solo sus filas por RLS).

Revision ID: 0005
Revises: 0004
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("GRANT DELETE ON cv_base TO horma_app;")


def downgrade() -> None:
    op.execute("REVOKE DELETE ON cv_base FROM horma_app;")
