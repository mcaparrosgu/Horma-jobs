"""Fase 9a, T04: migración 0021 (puestos, titulo_norm, avisos_vistos, ajustes_perfil)."""
import importlib

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from horma.web.db import sesion_de

pytestmark = pytest.mark.bd


def test_la_migracion_0021_encadena_con_la_0020():
    m = importlib.import_module("horma.web.migrations.versions.0021_fase9a_huecos_puestos")
    assert (m.revision, m.down_revision) == ("0021", "0020")


def _usuaria(motor_migrador, sub):
    with motor_migrador.begin() as c:
        return c.execute(text("insert into usuarias (google_sub) values (:s) returning id"),
                         {"s": sub}).scalar_one()


def test_columnas_nuevas_de_preferencias_y_ofertas(motor_migrador, bd_limpia):
    u = _usuaria(motor_migrador, "a")
    with motor_migrador.begin() as c:
        c.execute(text("insert into preferencias (usuaria_id) values (:u)"), {"u": u})
        fila = c.execute(text("select puestos, puestos_sugeridos, excluidos from preferencias")).one()
        assert fila == ([], [], [])
        assert c.execute(text("select count(*) from information_schema.columns "
                              "where table_name='ofertas' and column_name='titulo_norm'")).scalar() == 1


def test_longitud_cv_tiene_su_check(motor_migrador, bd_limpia):
    u = _usuaria(motor_migrador, "a")
    with pytest.raises(DBAPIError):
        with motor_migrador.begin() as c:
            c.execute(text("insert into ajustes_perfil (usuaria_id, longitud_cv) values (:u, 'otra')"),
                      {"u": u})


def test_titulo_norm_se_rellena_en_las_ofertas_que_ya_habia(bd_migrada, motor_migrador, bd_limpia):
    from alembic import command
    from alembic.config import Config

    from tests.conftest import RAIZ

    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", bd_migrada[1])
    command.downgrade(cfg, "0020")
    with motor_migrador.begin() as c:
        c.execute(text("insert into ofertas (texto_crudo, huella, titulo, estado) "
                       "values ('t', 'h1', 'Senior Data Analyst (m/f)', 'procesada')"))
    command.upgrade(cfg, "head")
    with motor_migrador.connect() as c:
        assert c.execute(text("select titulo_norm from ofertas")).scalar_one() == "senior data analyst m f"


def test_rls_de_avisos_vistos_y_ajustes(motor_app, motor_migrador, bd_limpia):
    a, b = _usuaria(motor_migrador, "a"), _usuaria(motor_migrador, "b")
    with sesion_de(motor_app, a) as s:
        s.execute(text("insert into avisos_vistos (usuaria_id, clave, huella) values (:u, 'k', 'h')"),
                  {"u": a})
        s.execute(text("insert into ajustes_perfil (usuaria_id, longitud_cv) values (:u, 'mantener')"),
                  {"u": a})
    with sesion_de(motor_app, b) as s:
        assert s.execute(text("select count(*) from avisos_vistos")).scalar() == 0
        assert s.execute(text("select count(*) from ajustes_perfil")).scalar() == 0
        s.execute(text("delete from avisos_vistos"))
    with sesion_de(motor_app, a) as s:
        assert s.execute(text("select count(*) from avisos_vistos")).scalar() == 1
