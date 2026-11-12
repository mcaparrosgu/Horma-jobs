"""Fase 1: catálogo común de ofertas (auditoría y taxonomía), fuentes, calificaciones, ejecuciones de
ingesta y claves de API. Modo sistema para lo que no pertenece a una usuaria.

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

FUNCIONES = """
CREATE FUNCTION app_sistema() RETURNS boolean LANGUAGE sql STABLE AS
$$ SELECT coalesce(current_setting('app.sistema', true), '') = 'on' $$;
GRANT EXECUTE ON FUNCTION app_sistema() TO horma_app;
"""

TABLAS = """
CREATE TABLE fuentes (
    id serial PRIMARY KEY,
    nombre text NOT NULL UNIQUE,
    web text NOT NULL CHECK (web LIKE 'https://%'),
    url text NOT NULL CHECK (url LIKE 'https://%'),
    metodo text NOT NULL DEFAULT 'GET' CHECK (metodo IN ('GET', 'POST')),
    parametros jsonb NOT NULL DEFAULT '{}',
    cabeceras jsonb NOT NULL DEFAULT '{}',
    variable_clave text,
    mapeo jsonb NOT NULL,
    activa boolean NOT NULL DEFAULT false,
    creada_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE claves_api (
    id serial PRIMARY KEY,
    nombre text NOT NULL,
    prefijo text NOT NULL,
    hash text NOT NULL UNIQUE,
    alcance text NOT NULL CHECK (alcance IN ('ofertas', 'ingesta')),
    creada_en timestamptz NOT NULL DEFAULT now(),
    revocada_en timestamptz
);

CREATE TABLE calificaciones_fuente (
    id serial PRIMARY KEY,
    url text NOT NULL,
    dominio text NOT NULL,
    estado text NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'hecha', 'error')),
    apta boolean,
    excluida_por_regla boolean,
    permite_uso_automatizado boolean,
    robots_permite boolean,
    requiere_clave boolean,
    motivos jsonb NOT NULL DEFAULT '[]',
    citas jsonb NOT NULL DEFAULT '[]',
    instrucciones_embebidas jsonb NOT NULL DEFAULT '[]',
    motivo_error text,
    creada_en timestamptz NOT NULL DEFAULT now(),
    calificada_en timestamptz
);
CREATE INDEX calificaciones_dominio_idx ON calificaciones_fuente (dominio, id DESC);

CREATE TABLE ejecuciones_ingesta (
    id serial PRIMARY KEY,
    fuente_id integer NOT NULL REFERENCES fuentes(id),
    limite integer NOT NULL DEFAULT 20 CHECK (limite BETWEEN 1 AND 500),
    estado text NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'en_curso', 'hecha', 'error')),
    recibidas integer NOT NULL DEFAULT 0,
    nuevas integer NOT NULL DEFAULT 0,
    repetidas integer NOT NULL DEFAULT 0,
    errores integer NOT NULL DEFAULT 0,
    motivo_error text,
    creada_en timestamptz NOT NULL DEFAULT now(),
    iniciada_en timestamptz,
    terminada_en timestamptz
);
CREATE INDEX ejecuciones_fuente_idx ON ejecuciones_ingesta (fuente_id, id DESC);
"""

OFERTAS = """
DROP POLICY propia ON ofertas;
ALTER TABLE ofertas DROP COLUMN usuaria_id;
ALTER TABLE ofertas
    ADD COLUMN fuente_id integer REFERENCES fuentes(id),
    ADD COLUMN clave_id integer REFERENCES claves_api(id),
    ADD COLUMN id_externo text,
    ADD COLUMN huella text,
    ADD COLUMN fantasma boolean,
    ADD COLUMN motivos_fantasma jsonb NOT NULL DEFAULT '[]',
    ADD COLUMN fraude boolean,
    ADD COLUMN senales_fraude jsonb NOT NULL DEFAULT '[]',
    ADD COLUMN dominio_empresa text,
    ADD COLUMN empresa_validada boolean,
    ADD COLUMN salario_publicado boolean,
    ADD COLUMN salario_rango text,
    ADD COLUMN frase_pedir_salario text,
    ADD COLUMN sector text,
    ADD COLUMN familia text,
    ADD COLUMN nivel text,
    ADD COLUMN stack jsonb NOT NULL DEFAULT '[]',
    ADD COLUMN procesada_en timestamptz;
-- RF-1.9: fuera de la recomendación si es fantasma o fraude (y mientras no esté procesada).
ALTER TABLE ofertas ADD COLUMN recomendable boolean
    GENERATED ALWAYS AS (coalesce(NOT (fantasma OR fraude), false)) STORED;
CREATE INDEX ofertas_id_idx ON ofertas (id DESC);
CREATE INDEX ofertas_huella_idx ON ofertas (huella);
-- RF-1.11: una fuente (o una empresa con su clave) no entrega dos veces la misma oferta.
CREATE UNIQUE INDEX ofertas_fuente_externo_uq ON ofertas (fuente_id, id_externo)
    WHERE fuente_id IS NOT NULL AND id_externo IS NOT NULL;
CREATE UNIQUE INDEX ofertas_clave_externo_uq ON ofertas (clave_id, id_externo)
    WHERE fuente_id IS NULL AND clave_id IS NOT NULL AND id_externo IS NOT NULL;

ALTER TABLE origen ALTER COLUMN usuaria_id DROP NOT NULL;
ALTER TABLE tareas ALTER COLUMN usuaria_id DROP NOT NULL;
DROP POLICY propia ON origen;
DROP POLICY propia ON tareas;
"""

RLS = """
-- Catálogo común: lo lee cualquier sesión con usuaria; solo lo escribe el sistema.
CREATE POLICY lectura ON ofertas FOR SELECT USING (app_usuaria() IS NOT NULL OR app_sistema());
CREATE POLICY alta ON ofertas FOR INSERT WITH CHECK (app_sistema());
CREATE POLICY cambio ON ofertas FOR UPDATE USING (app_sistema()) WITH CHECK (app_sistema());

-- Origen: sin usuaria = dato del catálogo; con usuaria = como en la fase 0.
CREATE POLICY lectura ON origen FOR SELECT USING (
    (usuaria_id IS NULL AND (app_usuaria() IS NOT NULL OR app_sistema()))
    OR usuaria_id = app_usuaria());
CREATE POLICY alta ON origen FOR INSERT WITH CHECK (
    (usuaria_id IS NULL AND app_sistema()) OR usuaria_id = app_usuaria());
CREATE POLICY baja ON origen FOR DELETE USING (
    (usuaria_id IS NULL AND app_sistema()) OR usuaria_id = app_usuaria());

-- Tareas: las de una usuaria, suyas; las del sistema (sin usuaria), solo del sistema.
CREATE POLICY propia_o_sistema ON tareas FOR ALL
    USING (usuaria_id = app_usuaria() OR (usuaria_id IS NULL AND app_sistema()))
    WITH CHECK (usuaria_id = app_usuaria() OR (usuaria_id IS NULL AND app_sistema()));

ALTER TABLE fuentes ENABLE ROW LEVEL SECURITY;
ALTER TABLE claves_api ENABLE ROW LEVEL SECURITY;
ALTER TABLE calificaciones_fuente ENABLE ROW LEVEL SECURITY;
ALTER TABLE ejecuciones_ingesta ENABLE ROW LEVEL SECURITY;
CREATE POLICY sistema ON fuentes FOR ALL USING (app_sistema()) WITH CHECK (app_sistema());
CREATE POLICY sistema ON claves_api FOR ALL USING (app_sistema()) WITH CHECK (app_sistema());
CREATE POLICY sistema ON calificaciones_fuente FOR ALL USING (app_sistema())
    WITH CHECK (app_sistema());
CREATE POLICY sistema ON ejecuciones_ingesta FOR ALL USING (app_sistema())
    WITH CHECK (app_sistema());
"""

PERMISOS = """
GRANT SELECT, INSERT, UPDATE ON fuentes, claves_api, calificaciones_fuente, ejecuciones_ingesta
    TO horma_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO horma_app;
"""


def upgrade() -> None:
    for bloque in (FUNCIONES, TABLAS, OFERTAS, RLS, PERMISOS):
        op.execute(bloque)
    from horma.web.semilla import sembrar_fuentes

    sembrar_fuentes(op.get_bind())


def downgrade() -> None:
    op.execute("""
    DROP POLICY lectura ON ofertas; DROP POLICY alta ON ofertas; DROP POLICY cambio ON ofertas;
    DROP POLICY lectura ON origen; DROP POLICY alta ON origen; DROP POLICY baja ON origen;
    DROP POLICY propia_o_sistema ON tareas;
    DELETE FROM origen WHERE usuaria_id IS NULL;
    DELETE FROM tareas WHERE usuaria_id IS NULL;
    DELETE FROM ofertas;
    ALTER TABLE ofertas DROP COLUMN recomendable;
    ALTER TABLE ofertas DROP COLUMN fuente_id, DROP COLUMN clave_id, DROP COLUMN id_externo,
        DROP COLUMN huella, DROP COLUMN fantasma, DROP COLUMN motivos_fantasma,
        DROP COLUMN fraude, DROP COLUMN senales_fraude, DROP COLUMN dominio_empresa,
        DROP COLUMN empresa_validada, DROP COLUMN salario_publicado, DROP COLUMN salario_rango,
        DROP COLUMN frase_pedir_salario, DROP COLUMN sector, DROP COLUMN familia,
        DROP COLUMN nivel, DROP COLUMN stack, DROP COLUMN procesada_en;
    ALTER TABLE ofertas ADD COLUMN usuaria_id integer NOT NULL REFERENCES usuarias(id);
    ALTER TABLE origen ALTER COLUMN usuaria_id SET NOT NULL;
    ALTER TABLE tareas ALTER COLUMN usuaria_id SET NOT NULL;
    CREATE POLICY propia ON ofertas FOR ALL
        USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
    CREATE POLICY propia ON origen FOR ALL
        USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
    CREATE POLICY propia ON tareas FOR ALL
        USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
    DROP TABLE ejecuciones_ingesta, calificaciones_fuente, claves_api, fuentes;
    DROP FUNCTION app_sistema();
    """)
