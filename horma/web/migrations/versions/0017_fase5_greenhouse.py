"""Fase 5, bloque G (T32): siembra las empresas de Greenhouse de `config/greenhouse.json`.

Una fuente por empresa, siempre inactiva hasta una calificación apta (RF-5.5c). No pisa las existentes.

Revision ID: 0017
Revises: 0016
"""
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from horma.web.semilla import sembrar_fuentes

    sembrar_fuentes(op.get_bind())


def downgrade() -> None:
    op.execute("DELETE FROM fuentes WHERE nombre LIKE 'gh-%'")
