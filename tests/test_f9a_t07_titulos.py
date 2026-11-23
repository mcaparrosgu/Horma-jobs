"""Fase 9a, T07: normalizar_titulo y buscar_ofertas con puestos y excluidos (RF-9.3c, RF-9.3d)."""
import pytest
from sqlalchemy import text

from horma.schemas.preferencias import Preferencias
from horma.tools.buscar_ofertas import buscar_ofertas
from horma.tools.normalizar_titulo import normalizar_titulo


def test_normalizar_titulo():
    assert normalizar_titulo("Senior Data Analyst (m/f)") == "senior data analyst m f"
    assert normalizar_titulo("Analistas de Datos – Barcelona") == "analista de dato barcelona"
    assert normalizar_titulo("Camarero/a de Sala") == "camarero de sala"
    assert normalizar_titulo("Business Analyst") == "business analyst"
    assert normalizar_titulo(None) == "" and normalizar_titulo("  ") == ""


def test_puesto_y_titulo_se_normalizan_igual():
    assert normalizar_titulo("Camareros") == normalizar_titulo("camarero")
    assert normalizar_titulo("Directores") == normalizar_titulo("director")


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
        yield c


def _oferta(c, id, titulo, familia="datos_ia"):
    c.execute(text("INSERT INTO ofertas VALUES "
                   "(:i, :t, 'procesada', true, :f, '2026-11-01', null, null, null)"),
              {"i": id, "t": normalizar_titulo(titulo), "f": familia})


def _ids(c, **prefs):
    q = buscar_ofertas(Preferencias(**prefs))
    return sorted(r[0] for r in c.execute(text(q.sql), q.parametros).fetchall())


@pytest.mark.bd
def test_puesto_casa_por_frase_completa(conexion):
    _oferta(conexion, 1, "Senior Data Analyst (m/f)")
    _oferta(conexion, 2, "Data Entry Clerk")
    _oferta(conexion, 3, "Data Analysts")
    assert _ids(conexion, puestos=["Data Analyst"]) == [1, 3]


@pytest.mark.bd
def test_oferta_de_otra_familia_entra_por_titulo(conexion):
    _oferta(conexion, 1, "Analista de datos", familia="finanzas_contabilidad")
    _oferta(conexion, 2, "Contable", familia="finanzas_contabilidad")
    _oferta(conexion, 3, "Programador", familia="datos_ia")
    assert _ids(conexion, familias=["datos_ia"], puestos=["analista de datos"]) == [1, 3]


@pytest.mark.bd
def test_excluidos_sacan_la_oferta(conexion):
    _oferta(conexion, 1, "Data Analyst")
    _oferta(conexion, 2, "Data Analyst Senior Manager")
    assert _ids(conexion, excluidos=["manager"]) == [1]


@pytest.mark.bd
def test_sin_puestos_ni_familias_no_filtra(conexion):
    _oferta(conexion, 1, "Cualquier cosa")
    assert _ids(conexion) == [1]
    q = buscar_ofertas(Preferencias())
    assert "titulo_norm" not in q.sql
