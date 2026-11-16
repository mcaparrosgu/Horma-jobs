"""Fase 4 · T06: el worker corre `candidatura` con un hilo del checkpointer de Postgres y «Reintentar» lo
borra antes de encolar (RF-4.3)."""
import pytest
from sqlalchemy import text
from test_f3_t12_t13_bd_worker import (
    FELIZ,
    _candidatura,
    _encolar,
    _fila,
    _oferta,
    _perfil_y_cv_base,
    _usuarias,
)

from horma import config
from horma.llm.simulado import ProveedorSimulado
from horma.web import checkpointer
from horma.web.queue import worker
from horma.web.services import candidaturas as servicio

pytestmark = pytest.mark.bd


@pytest.fixture
def langgraph(monkeypatch):
    monkeypatch.setenv("HORMA_FLOW_IMPL", "langgraph")
    config.ajustes.cache_clear()
    yield
    config.ajustes.cache_clear()


def _cfg(cid):
    return {"configurable": {"thread_id": checkpointer.hilo_de(cid)}}


def _preparar(motor):
    a, _ = _usuarias(motor)
    _perfil_y_cv_base(motor, a)
    cid = _candidatura(motor, a, _oferta(motor))
    _encolar(motor, a, "candidatura", cid)
    return a, cid


def _n_checkpoints(motor_migrador, cid):
    with motor_migrador.connect() as c:
        return c.execute(text("select count(*) from checkpoints where thread_id = :t"),
                         {"t": checkpointer.hilo_de(cid)}).scalar_one()


def test_tras_preparar_queda_en_borrador_y_su_hilo_existe_en_pausa(motor_app, bd_limpia, langgraph):
    a, cid = _preparar(motor_app)
    prov = ProveedorSimulado(FELIZ)
    assert worker.procesar_una(motor_app, prov) == "hecha" and len(prov.llamadas) == 3
    f = _fila(motor_app, a, cid)
    assert f["estado"] == "borrador" and f["preparacion"] == "lista" and f["cv_contenido"]
    assert f["cv_pdf"] is None and f["entregada_en"] is None  # `entregar` aún no se ha ejecutado
    estado = checkpointer.obtener(motor_app).get_tuple(_cfg(cid))
    assert estado is not None and estado.checkpoint["channel_values"]["cv_contenido"] == f["cv_contenido"]


def test_reintentar_borra_el_hilo_y_empieza_de_cero(motor_app, motor_migrador, bd_limpia, langgraph):
    a, cid = _preparar(motor_app)
    assert worker.procesar_una(motor_app, ProveedorSimulado(FELIZ)) == "hecha"
    primera = _n_checkpoints(motor_migrador, cid)
    assert primera > 0
    with motor_migrador.begin() as c:
        c.execute(text("update candidaturas set preparacion = 'error', motivo_error = 'x' where id = :i"),
                  {"i": cid})
    servicio.reintentar(motor_app, a, cid)
    assert _n_checkpoints(motor_migrador, cid) == 0  # borrado antes de encolar
    assert worker.procesar_una(motor_app, ProveedorSimulado(FELIZ)) == "hecha"
    assert _n_checkpoints(motor_migrador, cid) == primera  # no arrastra la vuelta anterior


def test_con_plain_todo_sigue_como_antes_y_no_hay_hilo(motor_app, motor_migrador, bd_limpia):
    assert config.ajustes().horma_flow_impl == "plain"
    a, cid = _preparar(motor_app)
    assert worker.procesar_una(motor_app, ProveedorSimulado(FELIZ)) == "hecha"
    f = _fila(motor_app, a, cid)
    assert f["estado"] == "borrador" and f["preparacion"] == "lista"
    assert _n_checkpoints(motor_migrador, cid) == 0
