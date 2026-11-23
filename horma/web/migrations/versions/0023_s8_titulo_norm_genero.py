"""S8: `ofertas.titulo_norm` sin marcas de género («Jefe/a de sala» → «jefe de sala», RF-10.14p).

Recalcula el título normalizado de todas las ofertas, por lotes y en Python, con `normalizar_titulo`.

Revision ID: 0023
Revises: 0022
"""
from alembic import op
from sqlalchemy import text

from horma.tools.normalizar_titulo import normalizar_titulo

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

_LOTE = 500


def upgrade() -> None:
    conn = op.get_bind()
    ultimo = 0
    while True:
        filas = conn.execute(text(
            "SELECT id, titulo FROM ofertas WHERE id > :u ORDER BY id LIMIT :n"),
            {"u": ultimo, "n": _LOTE}).fetchall()
        if not filas:
            break
        conn.execute(text("UPDATE ofertas SET titulo_norm = :t WHERE id = :i"),
                     [{"i": i, "t": normalizar_titulo(t)} for i, t in filas])
        ultimo = filas[-1][0]


def downgrade() -> None:
    pass  # solo recalcula un dato derivado; no hay nada que deshacer
