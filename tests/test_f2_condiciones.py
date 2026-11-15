"""Condiciones de una oferta frente a lo que busca la usuaria: calculadas con código (RF-2.12)."""
import pytest

from horma.schemas.oferta import Auditoria, Oferta
from horma.schemas.preferencias import Preferencias
from horma.schemas.taxonomia import Taxonomia
from horma.tools.evaluar_condiciones import evaluar_condiciones


def oferta(**campos) -> Oferta:
    base = {"titulo": "Camarera", "contrato": "indefinido", "ubicacion": "Valencia", "remoto": False,
            "salario": {"minimo": 17000, "maximo": 19000, "moneda": "EUR"}, "idiomas": [],
            "auditoria": Auditoria(fantasma=False, fraude=False, salario_publicado=True),
            "taxonomia": Taxonomia(sector="hosteleria_turismo", familia="hosteleria_restauracion",
                                   nivel="junior", stack=[])}
    return Oferta.model_validate({**base, **campos})


def test_sin_condiciones_marcadas_es_alto():
    assert evaluar_condiciones(oferta(), Preferencias()) == "alto"


def test_todas_cumplidas_es_alto():
    p = Preferencias(contratos=["indefinido"], paises=["ES"], sueldo_minimo=16000)
    assert evaluar_condiciones(oferta(), p) == "alto"


@pytest.mark.parametrize("prefs", [
    {"contratos": ["temporal"]},
    {"paises": ["FR"]},
    {"solo_remoto": True},
    {"sueldo_minimo": 30000},
    {"idiomas": ["fr"]},
])
def test_una_condicion_incumplida_es_bajo(prefs):
    assert evaluar_condiciones(oferta(idiomas=["inglés"]), Preferencias(**prefs)) == "bajo"


def test_un_dato_que_la_oferta_no_dice_no_cuenta_en_contra_pero_baja_a_medio_si_ella_lo_pidio():
    sin_sueldo = oferta(salario=None)
    assert evaluar_condiciones(sin_sueldo, Preferencias()) == "alto"  # no pidió sueldo
    assert evaluar_condiciones(sin_sueldo, Preferencias(sueldo_minimo=16000)) == "medio"


def test_incumplir_una_gana_a_no_tener_dato_de_otra():
    p = Preferencias(contratos=["temporal"], sueldo_minimo=16000)
    assert evaluar_condiciones(oferta(salario=None), p) == "bajo"
