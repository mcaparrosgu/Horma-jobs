"""Fase 3, bloque H: simplificar la candidatura (P16). Salen el documento elegido, el CV estético, la
respuesta pegada y las vueltas de revisión; entran las redacciones y los problemas del juez. Los avisos
pasan de texto a objetos `Aviso`. El historial deja de tener etiquetas de respuesta y las versiones de
CV base ya no dependen de una candidatura. Reversible: `downgrade` recrea lo quitado, vacío o por defecto.

Revision ID: 0007
Revises: 0006
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

UPGRADE = """
ALTER TABLE candidaturas
    ADD COLUMN redacciones_cv smallint NOT NULL DEFAULT 0 CHECK (redacciones_cv >= 0),
    ADD COLUMN redacciones_carta smallint NOT NULL DEFAULT 0 CHECK (redacciones_carta >= 0),
    ADD COLUMN problemas_juez jsonb NOT NULL DEFAULT '[]';
UPDATE candidaturas SET redacciones_cv = least(vueltas_cv, 32767),
                        redacciones_carta = least(vueltas_carta, 32767);
UPDATE candidaturas SET avisos = (
    SELECT coalesce(jsonb_agg(CASE WHEN jsonb_typeof(e) = 'string'
        THEN jsonb_build_object('documento', 'cv', 'frase', null, 'mensaje', e #>> '{}') ELSE e END),
        '[]'::jsonb)
    FROM jsonb_array_elements(avisos) AS e);
ALTER TABLE candidaturas
    DROP COLUMN documento, DROP COLUMN cv_estetico_id, DROP COLUMN respuesta_pendiente,
    DROP COLUMN respuesta_propuesta, DROP COLUMN vueltas_cv, DROP COLUMN vueltas_carta;

DELETE FROM candidatura_eventos WHERE tipo = 'cv_base_guardado';
UPDATE candidatura_eventos SET origen = 'usuaria' WHERE origen <> 'usuaria';
ALTER TABLE candidatura_eventos
    DROP CONSTRAINT candidatura_eventos_origen_check, DROP CONSTRAINT candidatura_eventos_tipo_check,
    DROP COLUMN etiqueta_respuesta,
    ADD CONSTRAINT candidatura_eventos_origen_check CHECK (origen = 'usuaria'),
    ADD CONSTRAINT candidatura_eventos_tipo_check CHECK (tipo IN ('transicion', 'nota'));

UPDATE cv_base_versiones SET origen = 'edicion' WHERE origen = 'candidatura';
ALTER TABLE cv_base_versiones
    DROP CONSTRAINT cv_base_versiones_origen_check, DROP COLUMN candidatura_id,
    ADD CONSTRAINT cv_base_versiones_origen_check CHECK (origen IN ('edicion', 'restauracion'));
"""

DOWNGRADE = """
ALTER TABLE cv_base_versiones
    DROP CONSTRAINT cv_base_versiones_origen_check,
    ADD COLUMN candidatura_id integer REFERENCES candidaturas(id) ON DELETE SET NULL,
    ADD CONSTRAINT cv_base_versiones_origen_check CHECK (origen IN ('candidatura', 'edicion', 'restauracion'));

ALTER TABLE candidatura_eventos
    DROP CONSTRAINT candidatura_eventos_origen_check, DROP CONSTRAINT candidatura_eventos_tipo_check,
    ADD COLUMN etiqueta_respuesta text CHECK (etiqueta_respuesta IN
        ('entrevista', 'rechazo', 'piden_informacion', 'otro')),
    ADD CONSTRAINT candidatura_eventos_origen_check CHECK (origen IN ('usuaria', 'respuesta')),
    ADD CONSTRAINT candidatura_eventos_tipo_check
        CHECK (tipo IN ('transicion', 'nota', 'cv_base_guardado'));

ALTER TABLE candidaturas
    ADD COLUMN vueltas_cv integer NOT NULL DEFAULT 0 CHECK (vueltas_cv >= 0),
    ADD COLUMN vueltas_carta integer NOT NULL DEFAULT 0 CHECK (vueltas_carta >= 0),
    ADD COLUMN documento text CHECK (documento IN ('adaptado', 'estetico')),
    ADD COLUMN cv_estetico_id integer REFERENCES cv_archivos(id) ON DELETE SET NULL,
    ADD COLUMN respuesta_pendiente text,
    ADD COLUMN respuesta_propuesta jsonb;
UPDATE candidaturas SET vueltas_cv = redacciones_cv, vueltas_carta = redacciones_carta;
UPDATE candidaturas SET avisos = (
    SELECT coalesce(jsonb_agg(CASE WHEN jsonb_typeof(e) = 'object' THEN to_jsonb(e ->> 'mensaje') ELSE e END),
        '[]'::jsonb)
    FROM jsonb_array_elements(avisos) AS e);
ALTER TABLE candidaturas
    DROP COLUMN redacciones_cv, DROP COLUMN redacciones_carta, DROP COLUMN problemas_juez;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
