"""S8, T39: puestos con género y barra (RF-10.14p)."""
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from horma.schemas.preferencias import Preferencias
from horma.tools.buscar_ofertas import buscar_ofertas
from horma.tools.normalizar_titulo import normalizar_titulo, variantes_genero
from horma.web.repositories.ofertas import contar_por_puesto


def _casa(puesto: str, titulo: str) -> bool:
    patrones = [f" {v} " for v in variantes_genero(normalizar_titulo(puesto))]
    return any(p in f" {normalizar_titulo(titulo)} " for p in patrones)


@pytest.mark.parametrize("titulo", ["Jefe/a de sala", "Jefa de sala", "Jefe(a) de sala", "Jefe de sala"])
def test_jefe_de_sala_casa_con_sus_variantes(titulo):
    assert _casa("Jefe de sala", titulo) and _casa("Jefa de sala", titulo)


def test_jefe_de_sala_no_casa_con_jefe_de_cocina():
    assert not _casa("Jefe de sala", "Jefe/a de cocina")
    assert not _casa("Jefe de sala", "Jefa de cocina")


def test_auxiliar_administrativo_casa_con_la_femenina():
    assert _casa("Auxiliar administrativo/a", "Auxiliar administrativa")
    assert _casa("Auxiliar administrativo", "Auxiliar administrativa")


def test_marcas_de_genero_se_quitan_y_lo_demas_no():
    assert normalizar_titulo("Camareros/as de sala") == "camarero de sala"
    assert normalizar_titulo("Senior Data Analyst (m/f)") == "senior data analyst m f"
    assert normalizar_titulo("Ventas/atención") == "venta atencion"


TABLA = """
CREATE TEMP TABLE ofertas (
    id int PRIMARY KEY, titulo_norm text, estado text, recomendable boolean, familia text,
    creada_en timestamptz, usuaria_id int, salario_anual_eur_min numeric, salario_anual_eur_max numeric
) ON COMMIT DROP
"""


@pytest.fixture
def conexion(motor_migrador):
    with motor_migrador.begin() as c:
        c.execute(text(TABLA))
        for i, t in enumerate(["Jefe/a de sala", "Jefa de sala", "Jefe(a) de sala", "Jefe de cocina"]):
            c.execute(text("INSERT INTO ofertas VALUES (:i, :t, 'procesada', true, null, '2026-11-01', "
                           "null, null, null)"), {"i": i + 1, "t": normalizar_titulo(t)})
        yield c


@pytest.mark.bd
def test_buscar_ofertas_encuentra_las_variantes(conexion):
    q = buscar_ofertas(Preferencias(puestos=["Jefe de sala"]))
    assert sorted(r[0] for r in conexion.execute(text(q.sql), q.parametros)) == [1, 2, 3]


@pytest.mark.bd
def test_contar_por_puesto_cuenta_igual(conexion):
    cuentas = contar_por_puesto(Session(bind=conexion), ["Jefe de sala", "Jefa de sala", "Jefe/a de sala"])
    assert cuentas == {"Jefe de sala": 3, "Jefa de sala": 3, "Jefe/a de sala": 3}


def test_migracion_recalcula_titulo_norm(bd_migrada, motor_migrador, bd_limpia):
    from alembic import command
    from alembic.config import Config

    from tests.conftest import RAIZ

    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", bd_migrada[1])
    command.downgrade(cfg, "0022")
    with motor_migrador.begin() as c:
        c.execute(text("insert into ofertas (texto_crudo, huella, titulo, titulo_norm, estado) "
                       "values ('t', 'h1', 'Jefe/a de sala', 'jefe a de sala', 'procesada')"))
    command.upgrade(cfg, "head")
    with motor_migrador.connect() as c:
        assert c.execute(text("select titulo_norm from ofertas")).scalar_one() == "jefe de sala"
