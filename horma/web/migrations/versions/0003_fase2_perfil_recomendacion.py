"""Fase 2: CV, perfiles con versiones, preferencias, CV base y matches (todo por usuaria, RLS
«propia») y columnas normalizadas en `ofertas` para filtrar (país, contrato, idiomas, sueldo anual).

Revision ID: 0003
Revises: 0002
"""
from alembic import op
from sqlalchemy import text

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TABLAS = """
CREATE TABLE cv_archivos (
    id serial PRIMARY KEY,
    usuaria_id integer NOT NULL REFERENCES usuarias(id),
    nombre text NOT NULL CHECK (length(nombre) > 0),
    nombre_original text NOT NULL,
    ruta text NOT NULL UNIQUE,
    tipo text NOT NULL CHECK (tipo IN ('pdf', 'docx', 'md')),
    clase text NOT NULL CHECK (clase IN ('fuente', 'estetico')),
    tamano integer NOT NULL CHECK (tamano > 0),
    texto text,
    creado_en timestamptz NOT NULL DEFAULT now(),
    UNIQUE (usuaria_id, nombre)
);

-- Una fila por versión del perfil. La vigente es la de mayor versión con estado 'hecha'.
CREATE TABLE perfiles (
    id serial PRIMARY KEY,
    usuaria_id integer NOT NULL REFERENCES usuarias(id),
    version integer NOT NULL CHECK (version >= 1),
    datos jsonb NOT NULL DEFAULT '{}',
    cv_maestro text NOT NULL DEFAULT '',
    preguntas_pendientes jsonb NOT NULL DEFAULT '[]',
    instrucciones_embebidas jsonb NOT NULL DEFAULT '[]',
    sector text,
    familia text,
    nivel text,
    stack jsonb NOT NULL DEFAULT '[]',
    estado text NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'hecha', 'error')),
    motivo_error text,
    creado_en timestamptz NOT NULL DEFAULT now(),
    UNIQUE (usuaria_id, version)
);

CREATE TABLE preferencias (
    usuaria_id integer PRIMARY KEY REFERENCES usuarias(id),
    familias text[] NOT NULL DEFAULT '{}',
    sectores text[] NOT NULL DEFAULT '{}',
    contratos text[] NOT NULL DEFAULT '{}',
    niveles text[] NOT NULL DEFAULT '{}',
    paises text[] NOT NULL DEFAULT '{}',
    idiomas text[] NOT NULL DEFAULT '{}',
    solo_remoto boolean NOT NULL DEFAULT false,
    solo_salario boolean NOT NULL DEFAULT false,
    sueldo_minimo numeric CHECK (sueldo_minimo >= 0),
    orden text NOT NULL DEFAULT 'compatibles' CHECK (orden IN ('recientes', 'compatibles')),
    rango_min integer NOT NULL DEFAULT 40 CHECK (rango_min BETWEEN 0 AND 100),
    rango_max integer NOT NULL DEFAULT 100 CHECK (rango_max BETWEEN 0 AND 100),
    origen jsonb NOT NULL DEFAULT '{}',
    actualizada_en timestamptz NOT NULL DEFAULT now(),
    CHECK (rango_min <= rango_max)
);

-- Un CV base por destino; el rechazado por la verificación (o la tarea fallida) deja su motivo
-- y la API no lo enseña.
CREATE TABLE cv_base (
    id serial PRIMARY KEY,
    usuaria_id integer NOT NULL REFERENCES usuarias(id),
    perfil_version integer NOT NULL,
    nombre text NOT NULL,
    sector text,
    familia text,
    contenido text NOT NULL DEFAULT '',
    traza jsonb NOT NULL DEFAULT '[]',
    estado text NOT NULL DEFAULT 'hecho' CHECK (estado IN ('hecho', 'rechazado', 'error')),
    motivo_error text,
    creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX cv_base_usuaria_idx ON cv_base (usuaria_id, id DESC);

-- La tabla es la caché del matcher: cambiar un filtro nunca llama al modelo.
CREATE TABLE matches (
    usuaria_id integer NOT NULL REFERENCES usuarias(id),
    oferta_id integer NOT NULL REFERENCES ofertas(id),
    perfil_version integer NOT NULL,
    nota integer NOT NULL CHECK (nota BETWEEN 0 AND 100),
    condiciones text NOT NULL CHECK (condiciones IN ('bajo', 'medio', 'alto')),
    explicacion text NOT NULL DEFAULT '',
    cita_perfil text NOT NULL DEFAULT '',
    cita_oferta text NOT NULL DEFAULT '',
    retirada boolean NOT NULL DEFAULT false,
    correccion jsonb,
    corregido_en timestamptz,
    creada_en timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (usuaria_id, oferta_id, perfil_version)
);

ALTER TABLE ofertas
    ADD COLUMN pais text,
    ADD COLUMN tipo_contrato text,
    ADD COLUMN idiomas_norm text[] NOT NULL DEFAULT '{}',
    ADD COLUMN salario_anual_eur_min numeric,
    ADD COLUMN salario_anual_eur_max numeric;
CREATE INDEX ofertas_pais_idx ON ofertas (pais);
"""

RLS = """
ALTER TABLE cv_archivos ENABLE ROW LEVEL SECURITY;
ALTER TABLE perfiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE preferencias ENABLE ROW LEVEL SECURITY;
ALTER TABLE cv_base ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;

CREATE POLICY propia ON cv_archivos FOR ALL
    USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
CREATE POLICY propia ON perfiles FOR ALL
    USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
CREATE POLICY propia ON preferencias FOR ALL
    USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
CREATE POLICY propia ON cv_base FOR ALL
    USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
CREATE POLICY propia ON matches FOR ALL
    USING (usuaria_id = app_usuaria()) WITH CHECK (usuaria_id = app_usuaria());
"""

PERMISOS = """
GRANT SELECT, INSERT, UPDATE ON cv_archivos, perfiles, preferencias, cv_base, matches TO horma_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO horma_app;
"""


def _rellenar_ofertas(conexion) -> None:
    """Normaliza las ofertas ya procesadas (las nuevas lo hacen al guardarse)."""
    from horma.schemas.oferta import OfertaExtraida, Salario
    from horma.tools.normalizar_oferta import normalizar_oferta

    filas = conexion.execute(text(
        "SELECT id, titulo, ubicacion, remoto, contrato, salario_minimo, salario_maximo, "
        "salario_moneda, idiomas, texto_crudo FROM ofertas WHERE estado = 'procesada'")).mappings().all()
    for f in filas:
        salario = None
        if f["salario_minimo"] is not None or f["salario_maximo"] is not None:
            salario = Salario(minimo=None if f["salario_minimo"] is None else float(f["salario_minimo"]),
                              maximo=None if f["salario_maximo"] is None else float(f["salario_maximo"]),
                              moneda=f["salario_moneda"])
        oferta = OfertaExtraida(titulo=f["titulo"] or "sin título", ubicacion=f["ubicacion"],
                                remoto=f["remoto"], contrato=f["contrato"], salario=salario,
                                idiomas=f["idiomas"] or [])
        n = normalizar_oferta(oferta, f["texto_crudo"] or "")
        conexion.execute(text(
            "UPDATE ofertas SET pais=:p, tipo_contrato=:c, idiomas_norm=:i, "
            "salario_anual_eur_min=:smin, salario_anual_eur_max=:smax WHERE id=:id"),
            {"id": f["id"], "p": n.pais, "c": n.tipo_contrato, "i": n.idiomas,
             "smin": n.salario_anual_eur_min, "smax": n.salario_anual_eur_max})


def upgrade() -> None:
    for bloque in (TABLAS, RLS, PERMISOS):
        op.execute(bloque)
    _rellenar_ofertas(op.get_bind())


def downgrade() -> None:
    op.execute("""
    DROP TABLE matches, cv_base, preferencias, perfiles, cv_archivos;
    DELETE FROM origen WHERE entidad = 'perfil';
    DROP INDEX ofertas_pais_idx;
    ALTER TABLE ofertas DROP COLUMN pais, DROP COLUMN tipo_contrato, DROP COLUMN idiomas_norm,
        DROP COLUMN salario_anual_eur_min, DROP COLUMN salario_anual_eur_max;
    """)
