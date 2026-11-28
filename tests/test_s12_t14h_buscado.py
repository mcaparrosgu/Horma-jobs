"""Spec 012 · T14h (RF-12.37, D-085): lo que ella busca no cuenta como otro oficio; se recalcula en código."""
from sqlalchemy import text

from horma.llm.simulado import ProveedorSimulado
from horma.web.db import sesion_de
from horma.web.queue import worker
from horma.web.services import preferencias
from tests.test_f2_t13_t14_bd_worker import _encolar, _match, _oferta_procesada, _perfilar_hecho, _usuarias

TITULO = "Teleoperador/a con inglés"


def _fila(motor, u):
    with sesion_de(motor, u) as s:
        return s.execute(text("select nota, nota_modelo, explicacion, huella_perfil from matches")).one()


def _marcar(motor, u, puestos):
    preferencias.guardar(motor, u, preferencias.ver(motor, u).model_copy(update={"puestos": puestos}))


def _puntuar(motor_app, puestos):
    a, _ = _usuarias(motor_app)
    pid = _perfilar_hecho(motor_app, a)
    _marcar(motor_app, a, puestos)
    while worker.procesar_una(motor_app, ProveedorSimulado([])):  # sus sinónimos (RF-12.4c)
        pass
    oferta = _oferta_procesada(motor_app, titulo=TITULO, requisitos='["Inglés B2"]', pais="ES")
    with sesion_de(motor_app, a) as s:
        s.execute(text("update preferencias set familias = '{}'"))
    _encolar(motor_app, a, "recomendar", pid)
    match = {**_match(oferta, nota=82), "marcas": [{"requisito": 1, "tipo": "exigido", "cubierto": "si"}],
             "cita_oferta": "Inglés B2"}
    prov = ProveedorSimulado([{"matches": [match]}])
    assert worker.procesar_una(motor_app, prov) == "hecha"
    return a


def test_marcarlo_quita_la_franja_y_desmarcarlo_la_devuelve_sin_llamar_al_modelo(motor_app, bd_limpia):
    a = _puntuar(motor_app, [])
    antes = _fila(motor_app, a)
    assert (antes.nota, antes.nota_modelo) == (55, 82)
    assert antes.explicacion.startswith("Tienes opciones por esto.")

    _marcar(motor_app, a, ["Teleoperador/a"])
    marcado = _fila(motor_app, a)
    assert marcado.nota == 82 and marcado.explicacion.startswith("Te la recomendamos por esto.")
    assert marcado.huella_perfil == antes.huella_perfil

    _marcar(motor_app, a, [])
    assert _fila(motor_app, a) == antes


def test_al_puntuar_ya_cuenta_lo_marcado(motor_app, bd_limpia):
    a = _puntuar(motor_app, ["Teleoperador/a"])
    assert _fila(motor_app, a).nota == 82
