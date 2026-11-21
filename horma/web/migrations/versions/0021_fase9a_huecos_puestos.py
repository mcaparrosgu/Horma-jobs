"""Fase 9a: puestos y términos excluidos en las preferencias, título normalizado de la oferta, avisos
vistos y longitud del CV por usuaria (RF-9.2c, RF-9.2d, RF-9.3b, RF-9.3c).

`ofertas.titulo_norm` se rellena aquí (por lotes, en Python) con `normalizar_titulo`; las ofertas nuevas
lo llevan desde que se procesan.

Revision ID: 0021
Revises: 0020
"""
from alembic import op
from sqlalchemy import text

from horma.tools.normalizar_titulo import normalizar_titulo

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

_LOTE = 500


def upgrade() -> None:
    op.execute("""
    ALTER TABLE preferencias ADD COLUMN puestos text[] NOT NULL DEFAULT '{}';
    ALTER TABLE preferencias ADD COLUMN puestos_sugeridos jsonb NOT NULL DEFAULT '[]';
    ALTER TABLE preferencias ADD COLUMN excluidos text[] NOT NULL DEFAULT '{}';
    ALTER TABLE ofertas ADD COLUMN titulo_norm text;

    CREATE TABLE avisos_vistos (
        usuaria_id integer NOT NULL REFERENCES usuarias(id) ON DELETE CASCADE,
        clave text NOT NULL,
        huella text NOT NULL,
        creado_en timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (usuaria_id, clave)
    );
    CREATE TABLE ajustes_perfil (
        usuaria_id integer PRIMARY KEY REFERENCES usuarias(id) ON DELETE CASCADE,
        longitud_cv text CHECK (longitud_cv IN ('mantener', 'sintetizar'))
    );
    ALTER TABLE avisos_vistos ENABLE ROW LEVEL SECURITY;
    ALTER TABLE ajustes_perfil ENABLE ROW LEVEL SECURITY;
    CREATE POLICY propia ON avisos_vistos FOR ALL
        USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
    CREATE POLICY propia ON ajustes_perfil FOR ALL
        USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
    GRANT SELECT, INSERT, UPDATE, DELETE ON avisos_vistos, ajustes_perfil TO horma_app;
    """)
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
    op.execute("""
    DROP TABLE ajustes_perfil;
    DROP TABLE avisos_vistos;
    ALTER TABLE ofertas DROP COLUMN titulo_norm;
    ALTER TABLE preferencias DROP COLUMN excluidos;
    ALTER TABLE preferencias DROP COLUMN puestos_sugeridos;
    ALTER TABLE preferencias DROP COLUMN puestos;
    """)
