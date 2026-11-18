"""Fase 4 · T04: elección de la implementación por configuración y equivalencia (RF-4.1b, RF-4.2)."""
import json
from pathlib import Path

import pytest
from test_f3_t08_t09_flujos import APROBADO, CARTA, CARTA_2, CARTA_MALA, CV_MALO, _cv, _estado, _juez
from typer.testing import CliRunner

from horma import config
from horma.cli import app as cli
from horma.evals import SETS, EsperadoCv, _entrada_cv
from horma.flows.grafo import LangGraphFlow
from horma.flows.plain import PlainFlow
from horma.flows.registry import IMPLEMENTACIONES, crear_flujo
from horma.llm.simulado import ProveedorSimulado

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _desde_la_raiz(monkeypatch):
    monkeypatch.chdir(RAIZ)
    config.ajustes.cache_clear()
    yield
    config.ajustes.cache_clear()


def test_por_defecto_es_plain_y_el_valor_viene_de_la_configuracion(monkeypatch):
    assert config.ajustes().horma_flow_impl == "plain"
    assert IMPLEMENTACIONES == ("plain", "langgraph")
    assert isinstance(crear_flujo("candidatura", proveedor=ProveedorSimulado([])), PlainFlow)
    monkeypatch.setenv("HORMA_FLOW_IMPL", "langgraph")
    config.ajustes.cache_clear()
    assert isinstance(crear_flujo("candidatura", proveedor=ProveedorSimulado([])), LangGraphFlow)


def test_el_registro_construye_la_implementacion_pedida_y_langgraph_solo_afecta_a_candidatura():
    assert type(crear_flujo("candidatura", "plain", proveedor=ProveedorSimulado([]))) is PlainFlow
    assert isinstance(crear_flujo("candidatura", "langgraph", proveedor=ProveedorSimulado([])), LangGraphFlow)
    # P1: los demás flujos siguen siendo lineales aunque se pida langgraph.
    otro = crear_flujo("clasificar_respuesta", "langgraph", proveedor=ProveedorSimulado([]))
    assert type(otro) is PlainFlow


def test_un_valor_desconocido_da_un_error_claro():
    with pytest.raises(ValueError) as exc:
        crear_flujo("candidatura", "otra", proveedor=ProveedorSimulado([]))
    assert "otra" in str(exc.value) and "plain" in str(exc.value) and "langgraph" in str(exc.value)


ESCENARIOS = {
    "feliz": [_cv(), CARTA, APROBADO],
    "vuelta_carta": [_cv(), CARTA, _juez(("carta", "Trabajé en Bar Sol desde 2020.", "promesa")), CARTA_2],
    "vuelta_cv": [_cv(), CARTA, _juez(("cv", "Manejo de TPV", "inflado")), _cv(), CARTA_2],
    "mal_en_comprobar": [CV_MALO, CARTA_MALA, _juez(), _cv(), CARTA],
}


@pytest.mark.parametrize("escenario", ESCENARIOS)
def test_las_dos_implementaciones_dan_el_mismo_estado_final_y_las_mismas_llamadas(escenario):
    resultados = {}
    for impl in IMPLEMENTACIONES:
        prov = ProveedorSimulado(ESCENARIOS[escenario])
        e = crear_flujo("candidatura", impl, proveedor=prov).run(_estado())
        resultados[impl] = (e, [ll["usuario"] for ll in prov.llamadas])
    assert resultados["plain"] == resultados["langgraph"]


def _consola(tmp_path, *extra, impl="plain", monkeypatch=None):
    caso = RAIZ / "evals/cv/casos/10-flujo-camarera-con-tres-cv-base"
    e = _entrada_cv(caso)
    esperado = EsperadoCv.model_validate_json((caso / "esperado.json").read_text(encoding="utf-8"))
    resp = tmp_path / "r.json"
    resp.write_text(json.dumps(SETS["cv"].simuladas(esperado, e)), encoding="utf-8")
    ofertas = tmp_path / "o.json"
    ofertas.write_text(json.dumps({"ofertas": [{"oferta_id": 5, "oferta": e["oferta"]}]}), encoding="utf-8")
    orden = ["flujo", "correr", "candidatura", "--usuaria", e["usuaria"], "--oferta", "5", "--ofertas",
             str(ofertas), "--simulado", "--respuestas", str(resp), *extra]
    return CliRunner().invoke(cli, orden, input="\n" * 20)


def test_flujo_correr_paso_a_paso_con_traza_funciona_con_langgraph(tmp_path, monkeypatch):
    monkeypatch.setenv("HORMA_FLOW_IMPL", "langgraph")
    config.ajustes.cache_clear()
    r = _consola(tmp_path, "--paso-a-paso", "--traza", str(tmp_path / "t"))
    assert r.exit_code == 0, r.output
    assert "componer" in r.output and "En pausa" in r.output
    assert sorted(p.name for p in (tmp_path / "t").iterdir())[-1].endswith("componer.json")


@pytest.mark.usefixtures("limites_reales")
@pytest.mark.parametrize("impl", IMPLEMENTACIONES)
def test_eval_correr_cv_simulado_aprueba_con_las_dos(impl):
    r = CliRunner().invoke(cli, ["eval", "correr", "cv", "--simulado", "--flujo", impl])
    assert r.exit_code == 0, r.output
    assert "APROBADO" in r.output


def test_eval_correr_con_un_flujo_desconocido_da_error():
    r = CliRunner().invoke(cli, ["eval", "correr", "cv", "--simulado", "--flujo", "otra"])
    assert r.exit_code == 2 and "otra" in r.output
