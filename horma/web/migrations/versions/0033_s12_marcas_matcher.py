"""S12 (RF-12.35 a 12.37, T14e): `matches` guarda la nota del modelo, las marcas y la relación.

Con ellas se pone el aviso «Pide menos de lo que tienes» y la nota se puede recalcular en código sin volver a
llamar al modelo. Lo ya puntuado queda vacío.

Revision ID: 0033
Revises: 0032
"""
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table matches add column nota_modelo integer, add column marcas jsonb, "
               "add column relacion text")


def downgrade() -> None:
    op.execute("alter table matches drop column nota_modelo, drop column marcas, drop column relacion")
