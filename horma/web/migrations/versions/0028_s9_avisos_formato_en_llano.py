"""S9: los avisos de formato ya guardados pasan al texto en llano (RF-10.16b).

Los avisos se guardan al preparar la candidatura; esta migración reescribe los que tienen el texto viejo
(«Para que los filtros de selección lean bien tu CV, revisa esto: …») con `texto_de_formato`. No cambia
el esquema.

Revision ID: 0028
Revises: 0027
"""
import json

import sqlalchemy as sa
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None

_VIEJO = "Para que los filtros de selección lean bien tu CV, revisa esto: "


def upgrade() -> None:
    from horma.schemas.candidatura import texto_de_formato

    bind = op.get_bind()
    filas = bind.execute(sa.text(
        "select id, avisos from candidaturas where avisos::text like :p"), {"p": f"%{_VIEJO}%"}).mappings().all()
    for f in filas:
        avisos = f["avisos"] if isinstance(f["avisos"], list) else json.loads(f["avisos"])
        for a in avisos:
            m = a.get("mensaje") or ""
            if m.startswith(_VIEJO):
                a["mensaje"] = texto_de_formato(m[len(_VIEJO):].rstrip("."))
        bind.execute(sa.text("update candidaturas set avisos = cast(:a as jsonb) where id = :i"),
                     {"a": json.dumps(avisos, ensure_ascii=False), "i": f["id"]})


def downgrade() -> None:
    """El texto viejo no se recupera."""
