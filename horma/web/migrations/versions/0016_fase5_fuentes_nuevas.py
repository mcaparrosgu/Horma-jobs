"""Fase 5, bloque G: campos para fuentes nuevas (RF-5.5, RF-5.5b, RF-5.5d).

`auth_basica` (Basic auth desde variables), `detalle` (segunda llamada por oferta), `cada_horas`
(intervalo mínimo entre ejecuciones) y `atribucion` (cita que se muestra con la oferta). Siembra las
fuentes nuevas de `config/endpoints.json` (siempre inactivas) y rellena los campos de las ya sembradas.

Revision ID: 0016
Revises: 0015
"""
import json

from alembic import op
from sqlalchemy import text

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
ALTER TABLE fuentes
    ADD COLUMN auth_basica jsonb,
    ADD COLUMN detalle jsonb,
    ADD COLUMN cada_horas integer CHECK (cada_horas IS NULL OR cada_horas >= 1),
    ADD COLUMN atribucion text;
-- La oferta lleva copia de la cita de su fuente (la usuaria no lee `fuentes`) y, si la fuente lo da,
-- su fecha de caducidad (Himalayas exige retirar las caducadas).
ALTER TABLE ofertas ADD COLUMN atribucion text, ADD COLUMN caduca_en timestamptz;
GRANT DELETE ON ofertas, matches TO horma_app;
CREATE POLICY caducada ON ofertas FOR DELETE
    USING (app_sistema() AND usuaria_id IS NULL AND caduca_en < now());
CREATE POLICY caducada_sistema ON matches FOR DELETE USING (app_sistema());
""")
    from horma.tools.semilla import fuentes_semilla
    from horma.web.semilla import sembrar_fuentes

    conexion = op.get_bind()
    sembrar_fuentes(conexion)
    for f in fuentes_semilla():  # las ya sembradas por 0002 reciben los campos nuevos (no la activación)
        conexion.execute(text(
            "update fuentes set auth_basica=cast(:a as jsonb), detalle=cast(:d as jsonb), "
            "cada_horas=:c, atribucion=:t where nombre=:n and auth_basica is null and detalle is null "
            "and cada_horas is null and atribucion is null"),
            {"a": json.dumps(f.auth_basica) if f.auth_basica else None,
             "d": json.dumps(f.detalle.model_dump()) if f.detalle else None,
             "c": f.cada_horas, "t": f.atribucion, "n": f.nombre})


def downgrade() -> None:
    op.execute("""
DROP POLICY caducada_sistema ON matches;
DROP POLICY caducada ON ofertas;
REVOKE DELETE ON ofertas, matches FROM horma_app;
ALTER TABLE ofertas DROP COLUMN atribucion, DROP COLUMN caduca_en;
ALTER TABLE fuentes DROP COLUMN auth_basica, DROP COLUMN detalle, DROP COLUMN cada_horas,
    DROP COLUMN atribucion;
""")
