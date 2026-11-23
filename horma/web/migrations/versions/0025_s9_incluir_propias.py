"""S9: «Incluir las ofertas que añado» (RF-10.6g).

Con la casilla marcada (por defecto), las ofertas que añade la usuaria se ven siempre, aunque no pasen
«Qué buscas» ni el rango de compatibilidad. Desmarcada, no se ven.

Revision ID: 0025
Revises: 0024
"""
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE preferencias ADD COLUMN incluir_propias boolean NOT NULL DEFAULT true")


def downgrade() -> None:
    op.execute("ALTER TABLE preferencias DROP COLUMN incluir_propias")
