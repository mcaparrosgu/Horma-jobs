"""Spec 012 · T28: la migración 0032 pasa las huellas guardadas a la copia ciega sin volver a puntuar."""
import hashlib
import importlib
import json

import pytest
from sqlalchemy import text

from horma.schemas.perfil import Perfil
from horma.tools.huella_perfil import huella_compatibilidad

pytestmark = pytest.mark.bd

PERFIL = {"nombre": "Lucía Ferrer",
          "experiencias": [{"puesto": "Camarera", "empresa": "Bar Sol",
                            "origen": {"fuente": "cv", "cv_id": 1, "fragmento": "Camarera"}}]}


def _migracion():
    return importlib.import_module("horma.web.migrations.versions.0032_s12_huella_copia")


def test_la_migracion_0032_encadena_con_la_0031():
    m = _migracion()
    assert (m.revision, m.down_revision) == ("0032", "0031")


def test_la_migracion_reescribe_la_huella_y_conserva_la_nota(bd_migrada, motor_migrador, bd_limpia):
    from alembic import command
    from alembic.config import Config

    from tests.conftest import RAIZ

    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", bd_migrada[1])
    perfil = Perfil.model_validate(PERFIL)
    vieja = _migracion().huella_anterior(perfil.model_dump(mode="json"))
    nueva = huella_compatibilidad(perfil)
    assert vieja != nueva and len(vieja) == len(hashlib.sha256(b"").hexdigest()[:32])
    command.downgrade(cfg, "0031")
    with motor_migrador.begin() as c:
        u = c.execute(text("insert into usuarias (google_sub) values ('h') returning id")).scalar_one()
        o = c.execute(text("insert into ofertas (texto_crudo, huella, estado) "
                           "values ('t', 'h32', 'procesada') returning id")).scalar_one()
        c.execute(text("insert into perfiles (usuaria_id, version, estado, datos) "
                       "values (:u, 1, 'hecha', cast(:d as jsonb))"),
                  {"u": u, "d": json.dumps(perfil.model_dump(mode="json"))})
        c.execute(text("insert into matches (usuaria_id, oferta_id, perfil_version, nota, condiciones, "
                       "huella_perfil) values (:u, :o, 1, 77, 'alto', :h)"), {"u": u, "o": o, "h": vieja})
    command.upgrade(cfg, "head")
    with motor_migrador.connect() as c:
        assert c.execute(text("select nota, huella_perfil from matches")).one() == (77, nueva)
