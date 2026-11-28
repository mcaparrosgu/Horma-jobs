"""S12 (RF-12.30h, T28): la huella de compatibilidad pasa a calcularse sobre la copia ciega.

Cada nota guardada con la huella anterior de su versión del perfil recibe la nueva. Sin esto, al desplegar
se volvería a puntuar todo.

Revision ID: 0032
Revises: 0031
"""
import hashlib
import json

from alembic import op
from sqlalchemy import text

from horma.schemas.perfil import Perfil
from horma.tools.huella_perfil import huella_compatibilidad

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None

_CAMPOS = ("titular", "experiencias", "formacion", "habilidades", "idiomas")


def _sin_origen(valor):
    if isinstance(valor, dict):
        return {k: _sin_origen(v) for k, v in valor.items() if k != "origen"}
    if isinstance(valor, list):
        return [_sin_origen(v) for v in valor]
    return valor


def huella_anterior(perfil: dict) -> str:
    """La huella tal como se calculaba hasta la 0031, sobre el perfil original (con el titular)."""
    datos = {c: _sin_origen(perfil.get(c)) for c in _CAMPOS}
    canon = json.dumps(datos, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:32]


def _reescribir(de, a) -> None:
    conexion = op.get_bind()
    filas = conexion.execute(text(
        "select p.usuaria_id, p.version, p.datos from perfiles p where p.estado <> 'pendiente' and exists "
        "(select 1 from matches m where m.usuaria_id = p.usuaria_id)")).mappings().all()
    for f in filas:
        datos = f["datos"] if isinstance(f["datos"], dict) else json.loads(f["datos"])
        if not datos:
            continue
        perfil = Perfil.model_validate({**datos, "version": f["version"]})
        conexion.execute(text("update matches set huella_perfil = :n where usuaria_id = :u "
                              "and huella_perfil = :v"),
                         {"n": a(perfil), "v": de(perfil), "u": f["usuaria_id"]})


def _vieja(perfil: Perfil) -> str:
    return huella_anterior(perfil.model_dump(mode="json"))


def upgrade() -> None:
    _reescribir(_vieja, huella_compatibilidad)


def downgrade() -> None:
    _reescribir(huella_compatibilidad, _vieja)
