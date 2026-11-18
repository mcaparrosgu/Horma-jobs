"""Fase 5, bloque F: cartas de presentación y marca «Lo escribí yo» (RF-5.6); tabla `estilo` (RF-5.6d).

`cv_archivos.clase` admite `carta` (solo muestra de estilo: no alimenta el perfil) y gana
`escrito_por_ella`. La guía de estilo vive en `estilo`: una por usuaria, solo la ve ella (RLS «propia»).

Revision ID: 0015
Revises: 0014
"""
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
ALTER TABLE cv_archivos DROP CONSTRAINT cv_archivos_clase_check;
ALTER TABLE cv_archivos ADD CONSTRAINT cv_archivos_clase_check
    CHECK (clase IN ('fuente', 'estetico', 'carta'));
ALTER TABLE cv_archivos ADD COLUMN escrito_por_ella boolean NOT NULL DEFAULT false;

CREATE TABLE estilo (
    usuaria_id integer PRIMARY KEY REFERENCES usuarias(id) ON DELETE CASCADE,
    guia jsonb NOT NULL,
    origen text NOT NULL CHECK (origen IN ('modelo', 'usuaria')),
    analizada_en timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE estilo ENABLE ROW LEVEL SECURITY;
CREATE POLICY propia ON estilo FOR ALL
    USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
GRANT SELECT, INSERT, UPDATE, DELETE ON estilo TO horma_app;
""")


def downgrade() -> None:
    op.execute("""
DROP TABLE estilo;
DELETE FROM cv_archivos WHERE clase = 'carta';
ALTER TABLE cv_archivos DROP COLUMN escrito_por_ella;
ALTER TABLE cv_archivos DROP CONSTRAINT cv_archivos_clase_check;
ALTER TABLE cv_archivos ADD CONSTRAINT cv_archivos_clase_check CHECK (clase IN ('fuente', 'estetico'));
""")
