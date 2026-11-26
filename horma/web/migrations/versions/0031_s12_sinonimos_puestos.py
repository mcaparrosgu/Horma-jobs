"""S12 (RF-12.4c): las otras formas de anunciar cada puesto marcado, pedidas al modelo una vez.

Revision ID: 0031
Revises: 0030
"""
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE preferencias ADD COLUMN sinonimos jsonb NOT NULL DEFAULT '{}'")


def downgrade() -> None:
    op.execute("ALTER TABLE preferencias DROP COLUMN sinonimos")
