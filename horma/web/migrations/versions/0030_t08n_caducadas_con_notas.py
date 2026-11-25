"""Spec 011, T08n: borrar las ofertas caducadas del catálogo aunque tengan notas de compatibilidad.

Un DELETE con WHERE también exige poder ver las filas (política SELECT). La sesión de sistema no veía
ninguna fila de `matches`, así que `caducada_sistema` (0016) no borraba nada y el borrado de la oferta
fallaba por la clave ajena. Se añade una política de lectura solo para las notas de ofertas caducadas
del catálogo: el sistema sigue sin ver las demás.

Mismo fallo con las candidaturas: el sistema no las ve, así que «no borrar la que tiene candidatura» nunca
se cumplía y el borrado fallaba por la clave ajena. `oferta_con_candidatura` devuelve solo un booleano,
sin exponer filas (solo la ejecuta el sistema).

Revision ID: 0030
Revises: 0029
"""
from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE POLICY caducada_sistema_ver ON matches FOR SELECT USING (
    app_sistema() AND oferta_id IN (
        SELECT id FROM ofertas WHERE usuaria_id IS NULL AND caduca_en < now()));

CREATE FUNCTION oferta_con_candidatura(p_oferta integer) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
    SELECT app_sistema() AND EXISTS (SELECT 1 FROM candidaturas WHERE oferta_id = p_oferta)
$$;
REVOKE ALL ON FUNCTION oferta_con_candidatura(integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION oferta_con_candidatura(integer) TO horma_app;
""")


def downgrade() -> None:
    op.execute("""
DROP FUNCTION oferta_con_candidatura(integer);
DROP POLICY caducada_sistema_ver ON matches;
""")
