import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from horma.schemas.oferta import OfertaExtraida
from horma.web.db import sesion_de, sesion_sin_usuaria

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


def test_una_usuaria_no_lee_las_ofertas_de_otra(motor_app, bd_limpia):
    """RF-0.10: leer datos de otra usuaria falla (no devuelve nada)."""
    a, b = _crear_usuarias(motor_app)
    with sesion_de(motor_app, a) as s:
        s.execute(text("insert into ofertas (usuaria_id, texto_crudo) values (:u, 'oferta de A')"),
                  {"u": a})
    with sesion_de(motor_app, b) as s:
        assert s.execute(text("select count(*) from ofertas")).scalar_one() == 0
        assert s.execute(text("select count(*) from ofertas where usuaria_id=:u"),
                         {"u": a}).scalar_one() == 0
    with sesion_de(motor_app, a) as s:
        assert s.execute(text("select count(*) from ofertas")).scalar_one() == 1


def test_una_usuaria_no_puede_escribir_a_nombre_de_otra(motor_app, bd_limpia):
    a, b = _crear_usuarias(motor_app)
    with pytest.raises(DBAPIError), sesion_de(motor_app, b) as s:
        s.execute(text("insert into ofertas (usuaria_id, texto_crudo) values (:u, 'x')"),
                  {"u": a})


def test_sin_usuaria_en_sesion_no_se_ve_nada(motor_app, bd_limpia):
    a, _ = _crear_usuarias(motor_app)
    with sesion_de(motor_app, a) as s:
        s.execute(text("insert into ofertas (usuaria_id, texto_crudo) values (:u, 'x')"), {"u": a})
    with sesion_sin_usuaria(motor_app) as s:
        assert s.execute(text("select count(*) from ofertas")).scalar_one() == 0
        assert s.execute(text("select count(*) from tareas")).scalar_one() == 0


def test_origen_y_tareas_tambien_estan_aisladas(motor_app, bd_limpia):
    a, b = _crear_usuarias(motor_app)
    with sesion_de(motor_app, a) as s:
        oid = s.execute(text(
            "insert into ofertas (usuaria_id, texto_crudo) values (:u, 'x') returning id"),
            {"u": a}).scalar_one()
        s.execute(text("insert into origen (usuaria_id, entidad, entidad_id, campo, fragmento) "
                       "values (:u, 'oferta', :o, 'titulo', 'x')"), {"u": a, "o": oid})
        s.execute(text("insert into tareas (usuaria_id, tipo, entidad_id, tope_coste) "
                       "values (:u, 'extraer_oferta', :o, 1)"), {"u": a, "o": oid})
    with sesion_de(motor_app, b) as s:
        assert s.execute(text("select count(*) from origen")).scalar_one() == 0
        assert s.execute(text("select count(*) from tareas")).scalar_one() == 0
