"""RLS. Fase 0: datos por usuaria (origen y tareas). Fase 1: las ofertas son un catálogo común que
lee cualquier sesión y solo escribe el sistema."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from horma.schemas.oferta import OfertaExtraida
from horma.web.db import sesion_de, sesion_sin_usuaria, sesion_sistema

pytestmark = pytest.mark.bd


def test_las_tablas_existen_y_el_esquema_tiene_su_columna(motor_migrador):
    with motor_migrador.connect() as c:
        tablas = {r[0] for r in c.execute(text(
            "select table_name from information_schema.tables where table_schema='public'"))}
        cols = {r[0] for r in c.execute(text(
            "select column_name from information_schema.columns where table_name='ofertas'"))}
    assert {"usuarias", "ofertas", "origen", "tareas", "llm_llamadas"} <= tablas
    esperadas = set(OfertaExtraida.model_fields) - {"salario"}
    esperadas |= {"salario_minimo", "salario_maximo", "salario_moneda"}
    assert esperadas <= cols


def test_el_rol_de_la_app_no_es_superusuario_ni_salta_rls(motor_migrador):
    with motor_migrador.connect() as c:
        fila = c.execute(text(
            "select rolsuper, rolbypassrls from pg_roles where rolname='horma_app'")).one()
    assert fila == (False, False)


def _crear_usuarias(motor):
    with sesion_sin_usuaria(motor) as s:
        a = s.execute(text("select obtener_o_crear_usuaria('google-A')")).scalar_one()
        b = s.execute(text("select obtener_o_crear_usuaria('google-B')")).scalar_one()
        return a, b


def test_obtener_o_crear_usuaria_es_idempotente(motor_app, bd_limpia):
    a, _ = _crear_usuarias(motor_app)
    with sesion_sin_usuaria(motor_app) as s:
        assert s.execute(text("select obtener_o_crear_usuaria('google-A')")).scalar_one() == a


def test_el_catalogo_lo_leen_todas_y_solo_lo_escribe_el_sistema(motor_app, bd_limpia):
    a, b = _crear_usuarias(motor_app)
    with sesion_sistema(motor_app) as s:
        s.execute(text("insert into ofertas (texto_crudo) values ('oferta del catálogo')"))
    for u in (a, b):
        with sesion_de(motor_app, u) as s:
            assert s.execute(text("select count(*) from ofertas")).scalar_one() == 1
    with pytest.raises(DBAPIError), sesion_de(motor_app, a) as s:
        s.execute(text("insert into ofertas (texto_crudo) values ('x')"))
    with sesion_de(motor_app, a) as s:  # actualizar sin modo sistema no toca ninguna fila
        assert s.execute(text("update ofertas set titulo='hackeada'")).rowcount == 0


def test_sin_usuaria_ni_sistema_no_se_ve_nada(motor_app, bd_limpia):
    with sesion_sistema(motor_app) as s:
        s.execute(text("insert into ofertas (texto_crudo) values ('x')"))
        s.execute(text("insert into fuentes (nombre, web, url, mapeo) "
                       "values ('f', 'https://f.test', 'https://f.test/api', '{}')"))
    with sesion_sin_usuaria(motor_app) as s:
        assert s.execute(text("select count(*) from ofertas")).scalar_one() == 0
        assert s.execute(text("select count(*) from tareas")).scalar_one() == 0
        assert s.execute(text("select count(*) from fuentes")).scalar_one() == 0


def test_las_tablas_de_ingesta_son_solo_del_sistema(motor_app, bd_limpia):
    a, _ = _crear_usuarias(motor_app)
    with sesion_sistema(motor_app) as s:
        s.execute(text("insert into claves_api (nombre, prefijo, hash, alcance) "
                       "values ('k', 'hk_x', 'h', 'ofertas')"))
    with sesion_de(motor_app, a) as s:
        for tabla in ("fuentes", "claves_api", "ejecuciones_ingesta", "calificaciones_fuente"):
            assert s.execute(text(f"select count(*) from {tabla}")).scalar_one() == 0, tabla


def test_origen_y_tareas_de_una_usuaria_siguen_aisladas(motor_app, bd_limpia):
    a, b = _crear_usuarias(motor_app)
    with sesion_de(motor_app, a) as s:
        s.execute(text("insert into origen (usuaria_id, entidad, entidad_id, campo, fragmento) "
                       "values (:u, 'perfil', 1, 'nombre', 'x')"), {"u": a})
        s.execute(text("insert into tareas (usuaria_id, tipo, entidad_id, tope_coste) "
                       "values (:u, 'perfilar', 1, 1)"), {"u": a})
    with sesion_de(motor_app, b) as s:
        assert s.execute(text("select count(*) from origen")).scalar_one() == 0
        assert s.execute(text("select count(*) from tareas")).scalar_one() == 0
    with pytest.raises(DBAPIError), sesion_de(motor_app, b) as s:
        s.execute(text("insert into origen (usuaria_id, entidad, entidad_id, campo, fragmento) "
                       "values (:u, 'perfil', 1, 'nombre', 'x')"), {"u": a})


def test_el_origen_del_catalogo_lo_lee_cualquiera_y_lo_escribe_el_sistema(motor_app, bd_limpia):
    a, _ = _crear_usuarias(motor_app)
    with sesion_sistema(motor_app) as s:
        s.execute(text("insert into origen (entidad, entidad_id, campo, fragmento) "
                       "values ('oferta', 1, 'titulo', 'x')"))
    with sesion_de(motor_app, a) as s:
        assert s.execute(text("select count(*) from origen")).scalar_one() == 1
    with pytest.raises(DBAPIError), sesion_de(motor_app, a) as s:
        s.execute(text("insert into origen (entidad, entidad_id, campo, fragmento) "
                       "values ('oferta', 1, 'titulo', 'y')"))
