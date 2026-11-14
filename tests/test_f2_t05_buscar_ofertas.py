"""Fase 2 · T05: buscar_ofertas construye el filtro duro en SQL y el pre-orden (RF-2.11, RF-1.9).

El dato que falta pasa el filtro (P2); solo se descarta lo que existe y no coincide. Las pruebas de
comportamiento corren contra Postgres con una tabla temporal `ofertas` con las columnas que usa la
consulta (las crea la migración 0003 en T13)."""
import pytest
from sqlalchemy import text

from horma.schemas.preferencias import Preferencias
from horma.schemas.taxonomia import Taxonomia
from horma.tools.buscar_ofertas import Consulta, buscar_ofertas


def test_sin_preferencias_la_consulta_no_filtra_nada_mas():
    c = buscar_ofertas(Preferencias())
    assert isinstance(c, Consulta)
    assert c.parametros == {}
    assert "ANY(" not in c.sql and "sueldo" not in c.sql.replace("sueldo_comparable", "")
    assert "estado = 'procesada'" in c.sql and "recomendable" in c.sql


def test_solo_se_pasan_los_parametros_de_los_filtros_activos():
    c = buscar_ofertas(Preferencias(paises=["ES"], sueldo_minimo=30000))
    assert set(c.parametros) == {"paises", "sueldo_minimo"}
    assert c.parametros["paises"] == ["ES"]


# --- comportamiento en Postgres ----------------------------------------------------------------
TABLA = """
CREATE TEMP TABLE ofertas (
    id int PRIMARY KEY, estado text, recomendable boolean, remoto boolean, sector text, familia text,
    nivel text, pais text, tipo_contrato text, idiomas_norm text[], salario_publicado boolean,
    salario_anual_eur_min numeric, salario_anual_eur_max numeric, creada_en timestamptz
) ON COMMIT DROP
"""
_DEFECTO = dict(estado="procesada", recomendable=True, remoto=None, sector="hosteleria_turismo",
                familia="hosteleria_restauracion", nivel="junior", pais="ES", tipo_contrato="indefinido",
                idiomas_norm=["es"], salario_publicado=True, salario_anual_eur_min=None,
                salario_anual_eur_max=None, creada_en="2026-11-01")


@pytest.fixture
def conexion(motor_migrador):
    with motor_migrador.begin() as c:
        c.execute(text(TABLA))
        yield c


def _insertar(c, id, **campos):
    fila = {**_DEFECTO, "id": id, **campos}
    columnas = ", ".join(fila)
    marcas = ", ".join(f"CAST(:{k} AS text[])" if k == "idiomas_norm" else f":{k}" for k in fila)
    c.execute(text(f"INSERT INTO ofertas ({columnas}) VALUES ({marcas})"), fila)


def _buscar(c, prefs=None, taxonomia=None, **kw):
    consulta = buscar_ofertas(prefs or Preferencias(), taxonomia, **kw)
    return [tuple(f) for f in c.execute(text(consulta.sql), consulta.parametros).fetchall()]


def _ids(c, prefs=None, taxonomia=None, **kw):
    return [f[0] for f in _buscar(c, prefs, taxonomia, **kw)]


@pytest.mark.bd
def test_nunca_salen_las_no_recomendables_ni_las_no_procesadas(conexion):
    _insertar(conexion, 1)
    _insertar(conexion, 2, recomendable=False)
    _insertar(conexion, 3, estado="pendiente")
    _insertar(conexion, 4, estado="error")
    assert _ids(conexion) == [1]


@pytest.mark.bd
def test_pais_el_dato_ausente_y_remoto_pasan(conexion):
    _insertar(conexion, 1, pais="ES")
    _insertar(conexion, 2, pais="DE")
    _insertar(conexion, 3, pais=None)
    _insertar(conexion, 4, pais="REMOTO")
    assert sorted(_ids(conexion, Preferencias(paises=["ES"]))) == [1, 3, 4]


@pytest.mark.bd
def test_pais_remoto_elegido_acepta_ofertas_remotas_de_cualquier_pais(conexion):
    _insertar(conexion, 1, pais="DE", remoto=True)
    _insertar(conexion, 2, pais="DE", remoto=False)
    assert _ids(conexion, Preferencias(paises=["REMOTO"])) == [1]


@pytest.mark.bd
def test_contrato_nivel_familia_y_sector(conexion):
    _insertar(conexion, 1)
    _insertar(conexion, 2, tipo_contrato="temporal")
    _insertar(conexion, 3, tipo_contrato=None)
    assert sorted(_ids(conexion, Preferencias(contratos=["indefinido"]))) == [1, 3]

    _insertar(conexion, 4, nivel="senior")
    _insertar(conexion, 5, nivel="sin_especificar")
    assert sorted(_ids(conexion, Preferencias(niveles=["senior"]))) == [4, 5]

    _insertar(conexion, 6, familia="legal", sector="servicios_profesionales")
    assert 6 not in _ids(conexion, Preferencias(familias=["hosteleria_restauracion"]))
    assert _ids(conexion, Preferencias(sectores=["servicios_profesionales"])) == [6]


@pytest.mark.bd
def test_idiomas_pasan_si_hay_coincidencia_o_la_oferta_no_pide_ninguno(conexion):
    _insertar(conexion, 1, idiomas_norm=["en"])
    _insertar(conexion, 2, idiomas_norm=["es", "en"])
    _insertar(conexion, 3, idiomas_norm=[])
    _insertar(conexion, 4, idiomas_norm=None)
    assert sorted(_ids(conexion, Preferencias(idiomas=["es"]))) == [2, 3, 4]


@pytest.mark.bd
def test_sueldo_minimo_y_ofertas_no_comparables(conexion):
    _insertar(conexion, 1, salario_anual_eur_min=35000, salario_anual_eur_max=40000)
    _insertar(conexion, 2, salario_anual_eur_min=15000, salario_anual_eur_max=20000)
    _insertar(conexion, 3)  # sin sueldo comparable: pasa, marcada
    _insertar(conexion, 4, salario_anual_eur_min=32000)  # solo mínimo
    filas = _buscar(conexion, Preferencias(sueldo_minimo=30000))
    assert sorted(f[0] for f in filas) == [1, 3, 4]
    comparable = {f[0]: f[1] for f in filas}
    assert comparable == {1: True, 3: False, 4: True}


@pytest.mark.bd
def test_solo_remoto_y_solo_salario(conexion):
    _insertar(conexion, 1, remoto=True)
    _insertar(conexion, 2, remoto=False)
    _insertar(conexion, 3, remoto=None)
    assert sorted(_ids(conexion, Preferencias(solo_remoto=True))) == [1, 3]
    _insertar(conexion, 4, salario_publicado=False)
    assert 4 not in _ids(conexion, Preferencias(solo_salario=True))


@pytest.mark.bd
def test_orden_taxonomia_primero_y_despues_fecha(conexion):
    _insertar(conexion, 1, familia="legal", creada_en="2026-11-10")  # más nueva pero no coincide
    _insertar(conexion, 2, creada_en="2026-11-02")
    _insertar(conexion, 3, creada_en="2026-11-05")
    perfil = Taxonomia(sector="hosteleria_turismo", familia="hosteleria_restauracion", nivel="junior")
    assert _ids(conexion, Preferencias(), perfil) == [3, 2, 1]


@pytest.mark.bd
def test_orden_recientes_ignora_la_taxonomia(conexion):
    _insertar(conexion, 1, familia="legal", creada_en="2026-11-10")
    _insertar(conexion, 2, creada_en="2026-11-02")
    perfil = Taxonomia(sector="hosteleria_turismo", familia="hosteleria_restauracion", nivel="junior")
    assert _ids(conexion, Preferencias(orden="recientes"), perfil) == [1, 2]


@pytest.mark.bd
def test_excluir_ids_y_limite(conexion):
    for i in range(1, 6):
        _insertar(conexion, i, creada_en=f"2026-11-0{i}")
    assert _ids(conexion, excluir_ids=[5, 4]) == [3, 2, 1]
    assert _ids(conexion, limite=2) == [5, 4]
