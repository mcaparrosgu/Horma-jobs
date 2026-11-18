"""Fase 5, bloque D: lecturas de URL de ofertas (RF-5.3f, RF-5.3j).

Una fila por URL que la usuaria da: `pendiente` → `leida` (con la oferta creada) o `error` (con un motivo
fijo, sin detalles del proveedor). Solo la ve su dueña (RLS «propia»). También cuenta las lecturas del mes.

Revision ID: 0014
Revises: 0013
"""
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE importaciones (
    id serial PRIMARY KEY,
    usuaria_id integer NOT NULL REFERENCES usuarias(id) ON DELETE CASCADE,
    url text NOT NULL,
    estado text NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'leida', 'error')),
    motivo text,
    oferta_id integer REFERENCES ofertas(id) ON DELETE SET NULL,
    creada_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX importaciones_usuaria_idx ON importaciones (usuaria_id, id DESC);
ALTER TABLE importaciones ENABLE ROW LEVEL SECURITY;
CREATE POLICY propia ON importaciones FOR ALL
    USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
GRANT SELECT, INSERT, UPDATE ON importaciones TO horma_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO horma_app;
""")


def downgrade() -> None:
    op.execute("DROP TABLE importaciones;")
