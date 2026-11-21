"""Simplificación S2 · T09: la candidatura se prepara sin CV base (RF-10.3, RF-10.3b, RF-10.3c, RF-10.3d)."""
from pathlib import Path

import pytest

from horma.config import Ajustes
from horma.flows.registry import IMPLEMENTACIONES, crear_flujo
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.candidatura import EstadoCandidatura
from tests.test_f3_t08_t09_flujos import (
    APROBADO,
    CARTA,
    MAESTRO,
    OFERTA,
    _cv,
    _cv_base,
    _juez,
)

AGENTES = Path(__file__).parent.parent / "horma" / "agents"


def _estado(**extra):
    return {"usuaria_id": 7, "perfil_version": 2, "oferta": OFERTA, "cv_maestro": MAESTRO, **extra}


@pytest.fixture(params=IMPLEMENTACIONES)
def impl(request):
    return request.param


def _correr(impl, respuestas, estado):
    prov = ProveedorSimulado(respuestas)
    return crear_flujo("candidatura", impl, proveedor=prov).run(estado), prov


def test_sin_cv_base_el_flujo_redacta_con_solo_el_maestro(impl):
    e, prov = _correr(impl, [_cv(), CARTA, APROBADO], _estado())
    assert len(prov.llamadas) == 3
    assert e["cv_base_id"] is None and e["cv_base_motivo"] is None
    assert e["preparacion"] == "lista" and e["avisos"] == []
    assert EstadoCandidatura.model_validate(e).cv_base_id is None


def test_una_lista_vacia_de_cv_base_es_lo_mismo_que_no_pasarla(impl):
    e, _ = _correr(impl, [_cv(), CARTA, APROBADO], _estado(cvs_base=[]))
    assert e["cv_base_id"] is None and e["preparacion"] == "lista"


def test_el_redactor_y_el_juez_no_reciben_cv_base_si_no_hay(impl):
    _, prov = _correr(impl, [_cv(), CARTA, APROBADO], _estado())
    assert '"cv_base":null' in prov.llamadas[0]["usuario"]
    assert "Ana Pérez" in prov.llamadas[0]["usuario"]  # el maestro sigue llegando


def test_comprobar_acepta_frases_del_maestro_y_rechaza_una_inventada(impl):
    flujo = crear_flujo("candidatura", impl, proveedor=ProveedorSimulado([]))
    base = {**_estado(), "cv_contenido": _cv()["contenido"], "cv_traza": _cv()["traza"],
            "carta_contenido": CARTA["contenido"], "carta_traza": CARTA["traza"]}
    ok = flujo.run_step("elegir_cv_base", dict(_estado()))
    ok = flujo.run_step("comprobar", {**ok, **{k: base[k] for k in (
        "cv_contenido", "cv_traza", "carta_contenido", "carta_traza")}})
    assert ok["errores_cv"] == []
    inventada = {**ok, "cv_contenido": "## Experiencia\nDirectora en Hotel Ritz, 2010-2015",
                 "cv_traza": [{"frase": "Directora en Hotel Ritz, 2010-2015",
                               "fragmento": "Directora en Hotel Ritz, 2010-2015"}]}
    assert flujo.run_step("comprobar", inventada)["errores_cv"]


def test_la_longitud_elegida_llega_al_redactor(impl):
    _, prov = _correr(impl, [_cv(), CARTA, APROBADO], _estado(longitud_cv="sintetizar"))
    assert "sintetizar" in prov.llamadas[0]["usuario"]
    _, prov = _correr(impl, [_cv(), CARTA, APROBADO], _estado())
    assert "sintetizar" not in prov.llamadas[0]["usuario"]


def test_el_respaldo_usa_un_cv_base_si_se_le_pasa(impl):
    e, _ = _correr(impl, [_cv(), CARTA, APROBADO], _estado(cvs_base=[_cv_base()]))
    assert e["cv_base_id"] == 1


def test_el_juez_sigue_pudiendo_corregir_sin_cv_base(impl):
    e, _ = _correr(impl, [_cv(), CARTA, _juez(("carta", "Trabajé en Bar Sol desde 2020.", "inflado")),
                          CARTA, ], _estado())
    assert e["vuelta_hecha"] is True


def test_el_respaldo_esta_apagado_por_defecto():
    assert Ajustes(_env_file=None).horma_cv_base_respaldo is False


def test_el_prompt_del_redactor_explica_la_condensacion_y_la_longitud():
    p = (AGENTES / "redactor_cv" / "prompt.md").read_text(encoding="utf-8")
    assert "puesto · empresa · fechas" in p and "sintetizar" in p and "mantener" in p
