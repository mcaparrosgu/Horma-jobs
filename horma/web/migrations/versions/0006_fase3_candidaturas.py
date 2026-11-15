"""Fase 3: candidaturas, su historial y las versiones de cada CV base (todo por usuaria, RLS «propia»).
Un índice único parcial impide dos candidaturas no cerradas para la misma oferta (RF-3.7b); al
eliminar un CV base se borran sus versiones (RF-3.8d).

Revision ID: 0006
Revises: 0005
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

TABLAS = """
CREATE TABLE candidaturas (
    id serial PRIMARY KEY,
    usuaria_id integer NOT NULL REFERENCES usuarias(id),
    oferta_id integer NOT NULL REFERENCES ofertas(id),
    cv_base_id integer REFERENCES cv_base(id) ON DELETE SET NULL,
    cv_base_motivo text,
    perfil_version integer,
    estado text NOT NULL DEFAULT 'borrador'
        CHECK (estado IN ('borrador', 'aprobada', 'enviada', 'entrevista', 'cerrada')),
    motivo_cierre text CHECK (motivo_cierre IN ('rechazo', 'descartada', 'retirada')),
    preparacion text NOT NULL DEFAULT 'en_curso'
        CHECK (preparacion IN ('en_curso', 'lista', 'pendiente_de_ti', 'error')),
    motivo_error text,
    cv_contenido text NOT NULL DEFAULT '',
    cv_traza jsonb NOT NULL DEFAULT '[]',
    carta_contenido text NOT NULL DEFAULT '',
    carta_traza jsonb NOT NULL DEFAULT '[]',
    huecos jsonb NOT NULL DEFAULT '[]',
    avisos jsonb NOT NULL DEFAULT '[]',
    cobertura_ats numeric CHECK (cobertura_ats BETWEEN 0 AND 1),
    vueltas_cv integer NOT NULL DEFAULT 0 CHECK (vueltas_cv >= 0),
    vueltas_carta integer NOT NULL DEFAULT 0 CHECK (vueltas_carta >= 0),
    instrucciones_embebidas jsonb NOT NULL DEFAULT '[]',
    documento text CHECK (documento IN ('adaptado', 'estetico')),
    cv_estetico_id integer REFERENCES cv_archivos(id) ON DELETE SET NULL,
    canal text CHECK (canal IN ('correo', 'web', 'linkedin', 'otro')),
    canal_otro text CHECK (length(canal_otro) <= 60),
    enviada_en date,
    respuesta_pendiente text,
    respuesta_propuesta jsonb,
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX candidaturas_oferta_viva_idx ON candidaturas (usuaria_id, oferta_id)
    WHERE estado <> 'cerrada';
CREATE INDEX candidaturas_usuaria_idx ON candidaturas (usuaria_id, id DESC);

CREATE TABLE candidatura_eventos (
    id serial PRIMARY KEY,
    usuaria_id integer NOT NULL REFERENCES usuarias(id),
    candidatura_id integer NOT NULL REFERENCES candidaturas(id) ON DELETE CASCADE,
    de text,
    a text,
    motivo text,
    canal text,
    origen text NOT NULL DEFAULT 'usuaria' CHECK (origen IN ('usuaria', 'respuesta')),
    tipo text NOT NULL DEFAULT 'transicion' CHECK (tipo IN ('transicion', 'nota', 'cv_base_guardado')),
    etiqueta_respuesta text CHECK (etiqueta_respuesta IN
        ('entrevista', 'rechazo', 'piden_informacion', 'otro')),
    creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX candidatura_eventos_idx ON candidatura_eventos (candidatura_id, id);

CREATE TABLE cv_base_versiones (
    id serial PRIMARY KEY,
    usuaria_id integer NOT NULL REFERENCES usuarias(id),
    cv_base_id integer NOT NULL REFERENCES cv_base(id) ON DELETE CASCADE,
    nombre text NOT NULL,
    contenido text NOT NULL,
    origen text NOT NULL CHECK (origen IN ('candidatura', 'edicion', 'restauracion')),
    candidatura_id integer REFERENCES candidaturas(id) ON DELETE SET NULL,
    creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX cv_base_versiones_idx ON cv_base_versiones (cv_base_id, id DESC);
"""

RLS = """
ALTER TABLE candidaturas ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidatura_eventos ENABLE ROW LEVEL SECURITY;
ALTER TABLE cv_base_versiones ENABLE ROW LEVEL SECURITY;

CREATE POLICY propia ON candidaturas FOR ALL
    USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
CREATE POLICY propia ON candidatura_eventos FOR ALL
    USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
CREATE POLICY propia ON cv_base_versiones FOR ALL
    USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
"""

PERMISOS = """
GRANT SELECT, INSERT, UPDATE ON candidaturas TO horma_app;
GRANT SELECT, INSERT ON candidatura_eventos, cv_base_versiones TO horma_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO horma_app;
"""


def upgrade() -> None:
    for bloque in (TABLAS, RLS, PERMISOS):
        op.execute(bloque)


def downgrade() -> None:
    op.execute("DROP TABLE cv_base_versiones, candidatura_eventos, candidaturas;")
