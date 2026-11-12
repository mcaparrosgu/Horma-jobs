"""Esquema inicial de la fase 0: tablas, seguridad por filas (RLS) y funciones de acceso.

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TABLAS = """
CREATE TABLE usuarias (
    id serial PRIMARY KEY,
    google_sub text NOT NULL UNIQUE,
    creada_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ofertas (
    id serial PRIMARY KEY,
    usuaria_id integer NOT NULL REFERENCES usuarias(id),
    texto_crudo text NOT NULL,
    estado text NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'procesada', 'error')),
    motivo_error text,
    titulo text,
    empresa text,
    ubicacion text,
    remoto boolean,
    contrato text,
    salario_minimo numeric,
    salario_maximo numeric,
    salario_moneda text,
    idiomas jsonb NOT NULL DEFAULT '[]',
    requisitos jsonb NOT NULL DEFAULT '[]',
    fecha_publicacion text,
    url text,
    instrucciones_embebidas jsonb NOT NULL DEFAULT '[]',
    creada_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ofertas_usuaria_idx ON ofertas (usuaria_id, id DESC);

CREATE TABLE origen (
    id serial PRIMARY KEY,
    usuaria_id integer NOT NULL REFERENCES usuarias(id),
    entidad text NOT NULL,
    entidad_id integer NOT NULL,
    campo text NOT NULL,
    fragmento text NOT NULL CHECK (length(fragmento) > 0)
);
CREATE INDEX origen_entidad_idx ON origen (entidad, entidad_id);

CREATE TABLE tareas (
    id serial PRIMARY KEY,
    usuaria_id integer NOT NULL REFERENCES usuarias(id),
    tipo text NOT NULL,
    entidad_id integer NOT NULL,
    estado text NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'en_curso', 'hecha', 'error')),
    intentos integer NOT NULL DEFAULT 0,
    coste_acumulado numeric NOT NULL DEFAULT 0,
    tope_coste numeric NOT NULL,
    tope_reintentos integer NOT NULL DEFAULT 3,
    motivo_error text,
    creada_en timestamptz NOT NULL DEFAULT now()
);

-- RT-06: solo métricas, nunca texto
CREATE TABLE llm_llamadas (
    id serial PRIMARY KEY,
    tarea_id integer,
    agente text NOT NULL,
    modelo text NOT NULL,
    tokens_entrada integer NOT NULL,
    tokens_salida integer NOT NULL,
    coste numeric NOT NULL,
    latencia_ms integer NOT NULL,
    resultado text NOT NULL,
    creada_en timestamptz NOT NULL DEFAULT now()
);
"""

RLS = """
CREATE FUNCTION app_usuaria() RETURNS integer LANGUAGE sql STABLE AS
$$ SELECT NULLIF(current_setting('app.usuaria_id', true), '')::integer $$;

ALTER TABLE usuarias ENABLE ROW LEVEL SECURITY;
ALTER TABLE ofertas ENABLE ROW LEVEL SECURITY;
ALTER TABLE origen ENABLE ROW LEVEL SECURITY;
ALTER TABLE tareas ENABLE ROW LEVEL SECURITY;

CREATE POLICY propia ON usuarias FOR SELECT USING (id = app_usuaria());
CREATE POLICY propia ON ofertas FOR ALL
    USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
CREATE POLICY propia ON origen FOR ALL
    USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
CREATE POLICY propia ON tareas FOR ALL
    USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());

-- Funciones que necesitan ver más allá de una usuaria (login y cola). Se ejecutan con los
-- privilegios del propietario; hacen una sola cosa y no devuelven datos de otras usuarias.
CREATE FUNCTION obtener_o_crear_usuaria(p_sub text) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_id integer;
BEGIN
    INSERT INTO usuarias (google_sub) VALUES (p_sub) ON CONFLICT (google_sub) DO NOTHING;
    SELECT id INTO v_id FROM usuarias WHERE google_sub = p_sub;
    RETURN v_id;
END $$;

CREATE FUNCTION reclamar_tarea() RETURNS SETOF tareas
LANGUAGE sql SECURITY DEFINER SET search_path = public AS $$
    UPDATE tareas SET estado = 'en_curso', intentos = intentos + 1
    WHERE id = (SELECT id FROM tareas WHERE estado = 'pendiente'
                ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1)
    RETURNING *
$$;

REVOKE ALL ON FUNCTION obtener_o_crear_usuaria(text), reclamar_tarea() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION obtener_o_crear_usuaria(text), reclamar_tarea(), app_usuaria()
    TO horma_app;
"""

PERMISOS = """
GRANT SELECT ON usuarias TO horma_app;
GRANT SELECT, INSERT, UPDATE ON ofertas, tareas TO horma_app;
GRANT SELECT, INSERT, DELETE ON origen TO horma_app;
GRANT SELECT, INSERT ON llm_llamadas TO horma_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO horma_app;
"""


def upgrade() -> None:
    for bloque in (TABLAS, RLS, PERMISOS):
        op.execute(bloque)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS llm_llamadas, tareas, origen, ofertas, usuarias CASCADE")
    op.execute("DROP FUNCTION IF EXISTS reclamar_tarea(), obtener_o_crear_usuaria(text), "
               "app_usuaria()")
