"""Fase 5 · T27: los redactores y el juez reciben la guía de estilo (RF-5.6e), con la puerta simulada."""
import json

import pytest
from test_f3_t08_t09_flujos import APROBADO, CARTA, _agente, _cv, _estado

from horma.agents.juez_candidatura.agent import JuezCandidatura
from horma.agents.juez_candidatura.schemas import EntradaJuezCandidatura
from horma.agents.redactor_carta.agent import RedactorCarta
from horma.agents.redactor_carta.schemas import EntradaRedactorCarta
from horma.agents.redactor_cv.agent import RedactorCv
from horma.agents.redactor_cv.schemas import EntradaRedactorCv
from horma.flows.registry import IMPLEMENTACIONES, crear_flujo
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.estilo import GuiaEstilo

GUIA = {"registro": "cercano", "persona": "primera", "longitud_frase": "corta", "vinetas": "con verbo",
        "expresiones": [{"rasgo": "dice «he llevado»", "cita": "he llevado una sala"}], "evita": []}


def _correr(impl, guia=None):
    prov = ProveedorSimulado([_cv(), CARTA, APROBADO])
    estado = _estado(**({"guia_estilo": guia} if guia is not None else {}))
    return crear_flujo("candidatura", impl, proveedor=prov).run(estado), prov


@pytest.mark.parametrize("impl", IMPLEMENTACIONES)
def test_la_guia_llega_a_las_tres_llamadas(impl):
    salida, prov = _correr(impl, GUIA)
    assert [_agente(prov, i) for i in range(3)] == ["cv", "carta", "juez"]
    for ll in prov.llamadas:
        assert json.loads(ll["usuario"])["guia_estilo"]["registro"] == "cercano"
    assert salida["preparacion"] == "lista"


@pytest.mark.parametrize("impl", IMPLEMENTACIONES)
def test_sin_guia_todo_sale_igual_que_antes(impl):
    con, prov_con = _correr(impl, GUIA)
    sin, prov_sin = _correr(impl)
    assert len(prov_sin.llamadas) == len(prov_con.llamadas) == 3
    for ll in prov_sin.llamadas:
        assert json.loads(ll["usuario"])["guia_estilo"] is None
    for clave in ("cv_contenido", "carta_contenido", "cv_traza", "carta_traza", "avisos", "preparacion"):
        assert sin[clave] == con[clave]  # la guía cambia lo que dice el modelo, no lo que comprueba el código


@pytest.mark.parametrize("impl", IMPLEMENTACIONES)
def test_la_trazabilidad_no_cambia_con_guia(impl):
    """Una frase sin origen se rechaza aunque venga con guía: el estilo no añade hechos."""
    inventado = {"contenido": "## Experiencia\nDirectora en Hotel Ritz, 2010-2015", "traza": []}
    prov = ProveedorSimulado([inventado, CARTA, APROBADO, inventado, CARTA, APROBADO])
    salida = crear_flujo("candidatura", impl, proveedor=prov).run(_estado(guia_estilo=GUIA))
    assert any(a["documento"] == "cv" for a in salida["avisos"])
    assert salida["preparacion"] == "pendiente_de_ti"


def test_los_prompts_dicen_que_la_guia_es_forma_y_nunca_hechos():
    for agente in (RedactorCv, RedactorCarta, JuezCandidatura):
        p = " ".join(agente.prompt().split())
        assert "guia_estilo" in p and "no fiable" in p
    for agente in (RedactorCv, RedactorCarta):
        p = " ".join(agente.prompt().split())
        assert "NUNCA en los hechos" in p and "traza" in p
    assert "suena_a_ia" in " ".join(JuezCandidatura.prompt().split())


def test_la_guia_es_opcional_en_las_tres_entradas():
    for modelo in (EntradaRedactorCv, EntradaRedactorCarta, EntradaJuezCandidatura):
        assert modelo.model_fields["guia_estilo"].default is None
        assert modelo.model_fields["guia_estilo"].annotation == GuiaEstilo | None


@pytest.mark.bd
def test_el_worker_carga_la_guia_de_la_usuaria(motor_app, bd_limpia):
    from test_f3_t12_t13_bd_worker import FELIZ, _candidatura, _encolar, _oferta, _perfil_y_cv_base, _usuarias

    from horma.web.db import sesion_de
    from horma.web.queue import worker
    from horma.web.repositories import estilo as repo_estilo

    a, _ = _usuarias(motor_app)
    _perfil_y_cv_base(motor_app, a)
    cid = _candidatura(motor_app, a, _oferta(motor_app))
    _encolar(motor_app, a, "candidatura", cid)
    with sesion_de(motor_app, a) as s:
        repo_estilo.guardar(s, a, GuiaEstilo.model_validate(GUIA), "usuaria")
    prov = ProveedorSimulado(FELIZ)
    assert worker.procesar_una(motor_app, prov) == "hecha"
    for ll in prov.llamadas:
        assert json.loads(ll["usuario"])["guia_estilo"]["registro"] == "cercano"


@pytest.mark.bd
def test_el_worker_sin_guia_manda_none(motor_app, bd_limpia):
    from test_f3_t12_t13_bd_worker import FELIZ, _candidatura, _encolar, _oferta, _perfil_y_cv_base, _usuarias

    from horma.web.queue import worker

    a, _ = _usuarias(motor_app)
    _perfil_y_cv_base(motor_app, a)
    cid = _candidatura(motor_app, a, _oferta(motor_app))
    _encolar(motor_app, a, "candidatura", cid)
    prov = ProveedorSimulado(FELIZ)
    assert worker.procesar_una(motor_app, prov) == "hecha"
    assert json.loads(prov.llamadas[0]["usuario"])["guia_estilo"] is None
