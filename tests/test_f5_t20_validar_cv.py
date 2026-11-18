"""Fase 5 · T20: `validar_cv` y `muletillas_ia` (RF-5.4, RF-5.7)."""
import json

import pytest

from horma.tools.muletillas_ia import RUTA, muletillas_ia
from horma.tools.validar_cv import CV_PALABRAS_MAX, CV_PALABRAS_MIN, validar_cv

pytestmark = pytest.mark.usefixtures("limites_reales")


def _cv(palabras: int = 400, experiencia: str = "Camarera · Bar Sol · 2019-2021") -> str:
    relleno = " ".join(["servicio"] * palabras)
    formacion = "Ciclo medio · IES Sur · 2017-2019"
    return f"# Ana\n\n## Experiencia\n{experiencia}\n{relleno}\n\n## Formación\n{formacion}\n"


# --- validar_cv --------------------------------------------------------------------------------
def test_un_cv_normal_no_da_errores():
    assert validar_cv(_cv()) == []


def test_limites_en_el_plan():
    assert (CV_PALABRAS_MIN, CV_PALABRAS_MAX) == (250, 1000)


def test_cv_de_1200_palabras_es_demasiado_largo():
    errores = validar_cv(_cv(1200))
    assert len(errores) == 1 and "largo" in errores[0] and "1.000" in errores[0]


def test_cv_de_150_palabras_es_demasiado_corto():
    errores = validar_cv(_cv(150))
    assert len(errores) == 1 and "corto" in errores[0] and "250" in errores[0]


def test_sin_experiencia_ni_formacion():
    texto = "# Ana\n\n## Resumen\n" + " ".join(["hola"] * 400)
    errores = validar_cv(texto)
    assert len(errores) == 1 and "Experiencia" in errores[0] and "Formación" in errores[0]


def test_basta_con_formacion_o_con_experiencia():
    solo_formacion = "## Formación\nGrado · UB · 2015-2019\n" + " ".join(["a"] * 400)
    assert validar_cv(solo_formacion) == []


def test_fin_anterior_al_inicio():
    errores = validar_cv(_cv(experiencia="Camarera · Bar Sol · 2021-2019"))
    assert len(errores) == 1 and "2021-2019" in errores[0] and "anterior" in errores[0]


def test_fechas_con_mes_y_con_actual():
    ok = _cv(experiencia="Camarera · Bar Sol · 2019-03-2021-06\nJefa · Bar Luz · 2021-07-actual")
    assert validar_cv(ok) == []
    mal = _cv(experiencia="Camarera · Bar Sol · 2021-06-2021-03")
    assert len(validar_cv(mal)) == 1


def test_mes_inventado():
    errores = validar_cv(_cv(experiencia="Camarera · Bar Sol · 2019-13-2021"))
    assert len(errores) == 1 and "2019-13" in errores[0]


def test_varios_errores_a_la_vez():
    texto = "## Resumen\ncorto"
    assert len(validar_cv(texto)) == 2  # corto y sin secciones


# --- muletillas_ia -----------------------------------------------------------------------------
def test_detecta_con_y_sin_acentos_y_mayusculas():
    assert muletillas_ia("Apasionada por la atención al cliente.") == ["apasionada por"]
    assert muletillas_ia("APASIONADO POR los datos") == ["apasionado por"]
    assert muletillas_ia("En el dinámico mundo de la hostelería") == ["en el dinamico mundo de"]
    assert muletillas_ia("en el dinamico mundo de la hosteleria") == ["en el dinamico mundo de"]


def test_un_texto_normal_no_da_nada():
    assert muletillas_ia("Atendí la sala de un restaurante de 60 cubiertos durante dos años.") == []


def test_sin_repetidos_y_en_orden_de_aparicion():
    t = "Sinergias aquí. Apasionada por esto. Más sinergias. Apasionada por aquello."
    assert muletillas_ia(t) == ["sinergias", "apasionada por"]


def test_la_lista_es_un_json_con_expresiones_normalizadas():
    datos = json.loads(RUTA.read_text(encoding="utf-8"))
    assert len(datos) >= 15
    for x in datos:
        assert x == x.lower() and x.strip() == x
        assert not any(c in x for c in "áéíóúü")


def test_no_encaja_dentro_de_otra_palabra():
    assert muletillas_ia("Las sinergiasXY no cuentan") == []
