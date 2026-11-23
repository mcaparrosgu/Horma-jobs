"""S9: «Otros» pasa a «Información adicional» en el CV maestro (RF-10.16a).

Recompone el `cv_maestro` de cada versión de perfil con `componer_cv_maestro`, como la 0010: así los
perfiles ya guardados tienen el título nuevo (y las fechas MM-AAAA de RF-10.14h) sin esperar a que la
usuaria cambie su perfil. No cambia el esquema.

Revision ID: 0026
Revises: 0025
"""
import json

import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from horma.schemas.perfil import Perfil
    from horma.tools.componer_cv_maestro import componer_cv_maestro

    bind = op.get_bind()
    filas = bind.execute(sa.text(
        "select id, datos, version from perfiles where estado = 'hecha'")).mappings().all()
    for f in filas:
        datos = f["datos"] if isinstance(f["datos"], dict) else json.loads(f["datos"])
        perfil = Perfil.model_validate({**datos, "version": f["version"]})
        bind.execute(sa.text("update perfiles set cv_maestro = :m where id = :i"),
                     {"m": componer_cv_maestro(perfil), "i": f["id"]})


def downgrade() -> None:
    """No se puede recuperar el maestro anterior: queda el recompuesto."""
