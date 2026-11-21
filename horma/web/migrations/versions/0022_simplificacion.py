"""Simplificación S5: gasto del día por usuaria contando el análisis de sus ofertas propias (RF-10.9) y
caché de la compatibilidad por huella del perfil (RF-10.10c).

`procesar_oferta` es una tarea del sistema (sin usuaria): la RLS la esconde de la sesión de la usuaria.
`gasto_hoy_usuaria(u)` suma las tareas de `u` y el análisis de las ofertas que `u` añadió; solo da la cifra
de la propia sesión (o la del sistema), nunca de otra usuaria.

Revision ID: 0022
Revises: 0021
"""
import json

from alembic import op
from sqlalchemy import text

from horma.schemas.perfil import Perfil
from horma.tools.huella_perfil import huella_compatibilidad

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE matches ADD COLUMN huella_perfil text;
    CREATE INDEX matches_huella_idx ON matches (usuaria_id, oferta_id, huella_perfil);
    CREATE FUNCTION gasto_hoy_usuaria(p_usuaria integer) RETURNS numeric
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
        SELECT CASE
            WHEN current_setting('app.sistema', true) = 'on' OR app_usuaria() = p_usuaria THEN (
                SELECT coalesce(sum(t.coste_acumulado), 0) FROM tareas t
                WHERE (t.creada_en AT TIME ZONE 'Europe/Madrid')::date
                      = (now() AT TIME ZONE 'Europe/Madrid')::date
                  AND (t.usuaria_id = p_usuaria OR (t.tipo = 'procesar_oferta' AND t.entidad_id IN (
                        SELECT o.id FROM ofertas o WHERE o.usuaria_id = p_usuaria))))
            ELSE 0 END
    $$;
    REVOKE ALL ON FUNCTION gasto_hoy_usuaria(integer) FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION gasto_hoy_usuaria(integer) TO horma_app;
    """)
    _rellenar_huellas()


def _rellenar_huellas() -> None:
    """Cada nota de hoy toma la huella de la versión del perfil con la que se calculó."""
    conexion = op.get_bind()
    filas = conexion.execute(text(
        "select p.usuaria_id, p.version, p.datos from perfiles p where exists "
        "(select 1 from matches m where m.usuaria_id = p.usuaria_id and m.perfil_version = p.version)"
    )).mappings().all()
    for f in filas:
        datos = f["datos"] if isinstance(f["datos"], dict) else json.loads(f["datos"])
        huella = huella_compatibilidad(Perfil.model_validate({**datos, "version": f["version"]}))
        conexion.execute(text("update matches set huella_perfil = :h where usuaria_id = :u "
                              "and perfil_version = :v"),
                         {"h": huella, "u": f["usuaria_id"], "v": f["version"]})


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS gasto_hoy_usuaria(integer)")
    op.execute("DROP INDEX IF EXISTS matches_huella_idx")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS huella_perfil")
