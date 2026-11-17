"""Fase 5, bloque B: un CV base se puede regenerar y su versión anterior queda en el historial.

`cv_base_versiones.origen` admite el valor nuevo `regeneracion` (RF-5.1e).

Revision ID: 0011
Revises: 0010
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
ALTER TABLE cv_base_versiones
    DROP CONSTRAINT cv_base_versiones_origen_check,
    ADD CONSTRAINT cv_base_versiones_origen_check
        CHECK (origen IN ('edicion', 'restauracion', 'regeneracion'));
""")


def downgrade() -> None:
    op.execute("UPDATE cv_base_versiones SET origen = 'edicion' WHERE origen = 'regeneracion';")
    op.execute("""
ALTER TABLE cv_base_versiones
    DROP CONSTRAINT cv_base_versiones_origen_check,
    ADD CONSTRAINT cv_base_versiones_origen_check CHECK (origen IN ('edicion', 'restauracion'));
""")
