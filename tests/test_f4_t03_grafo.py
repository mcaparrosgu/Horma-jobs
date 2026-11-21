"""Fase 4 · T03: LangGraphFlow con los mismos pasos y aristas que PlainFlow (RF-4.1, RF-4.1b)."""
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from test_f3_t08_t09_flujos import APROBADO, CARTA, CARTA_2, _correr, _cv, _estado, _juez

from horma.flows import candidatura
from horma.flows.base import ErrorDePaso, Flow
from horma.flows.grafo import LangGraphFlow
from horma.llm.simulado import ProveedorSimulado


def _grafo(respuestas, **kw):
    prov = ProveedorSimulado(respuestas)
    return candidatura.crear_grafo(proveedor=prov, **kw), prov


def test_cumple_la_interfaz_y_tiene_los_mismos_pasos():
    g, _ = _grafo([])
    assert isinstance(g, Flow) and g.pasos() == candidatura.crear(ProveedorSimulado([])).pasos()
    assert g.pausas == {"entregar"} and g.inicio == "elegir_cv_base"


def test_todas_las_claves_que_escriben_los_pasos_estan_declaradas():
    # Se corre el flujo plano con la vuelta única (todos los pasos) y se mira cada clave que quedó escrita.
    juez = _juez(("carta", "Trabajé en Bar Sol desde 2020.", "promesa"))
    e, _ = _correr([_cv(), CARTA, juez, CARTA_2])
    assert set(e) - {"en_pausa"} <= candidatura.CLAVES_ESTADO


def test_run_se_para_y_reanudar_termina_con_inmemorysaver():
    g, prov = _grafo([_cv(), CARTA, APROBADO], checkpointer=InMemorySaver())
    e = g.run(_estado(), hilo="candidatura-1")
    assert e["en_pausa"] == "entregar" and e["preparacion"] == "lista" and len(prov.llamadas) == 3
    cambios = {"cv_contenido": "## Experiencia\nEditado", "carta_contenido": "Hola\nUn saludo"}
    e = g.reanudar("candidatura-1", cambios)
    assert e["en_pausa"] is None and e["cv_contenido"] == "## Experiencia\nEditado"
    assert e["cv_pdf"][:4] == b"%PDF" and e["carta_pdf"][:4] == b"%PDF" and len(prov.llamadas) == 3


def test_sin_hilo_usa_uno_efimero_y_se_puede_reanudar():
    g, _ = _grafo([_cv(), CARTA, APROBADO])
    e = g.run(_estado())
    assert e["en_pausa"] == "entregar"
    assert g.reanudar(g.ultimo_hilo, {})["en_pausa"] is None


def test_reanudar_sin_checkpoint_da_error_de_paso():
    g, _ = _grafo([], checkpointer=InMemorySaver())
    with pytest.raises(ErrorDePaso):
        g.reanudar("no-existe", {})


def test_reanudar_tras_terminar_da_error():
    g, _ = _grafo([_cv(), CARTA, APROBADO])
    g.run(_estado(), hilo="h")
    g.reanudar("h", {})
    with pytest.raises(ErrorDePaso):
        g.reanudar("h", {})


def test_volver_a_correr_el_mismo_hilo_empieza_de_cero():
    g, prov = _grafo([_cv(), CARTA, APROBADO, _cv(), CARTA, APROBADO])
    g.run(_estado(), hilo="h")
    e = g.run(_estado(), hilo="h")
    assert e["en_pausa"] == "entregar" and len(prov.llamadas) == 6


def test_un_fallo_en_un_nodo_llega_como_error_de_paso_con_su_nombre():
    g, _ = _grafo([])  # sin respuestas del modelo, falla el primer nodo que lo llama (RF-10.3)
    with pytest.raises(ErrorDePaso) as exc:
        g.run(_estado(cvs=[]), hilo="h")
    assert exc.value.paso == "redactar_cv"


def test_un_flujo_sin_pausas_corre_hasta_el_final():
    g = LangGraphFlow("lineal", pasos={"a": lambda e: {**e, "x": 1}, "b": lambda e: {**e, "y": 2}},
                      aristas={"a": "b"}, inicio="a", finales={"b"}, claves={"x", "y"})
    assert g.run({}) == {"x": 1, "y": 2}
    with pytest.raises(ErrorDePaso):
        g.reanudar("h", {})


def test_una_clave_de_entrada_no_declarada_falla_en_voz_alta_en_vez_de_perderse():
    g, _ = _grafo([])
    with pytest.raises(ErrorDePaso, match="no_existe"):
        g.run(_estado(no_existe=1))
