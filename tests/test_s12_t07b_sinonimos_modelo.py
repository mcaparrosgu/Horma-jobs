"""Spec 012, T07b (RF-12.4c, 12.4d): el modelo da las otras formas de cada puesto una vez."""
import pytest

from horma.llm.simulado import ProveedorSimulado
from horma.web.main import crear_app
from horma.web.queue import worker
from tests.test_f2_t15_t19_api import IdentidadFalsa, _oferta, _propietario, archivos, entrar  # noqa: F401

pytestmark = pytest.mark.bd
RESPUESTA = {"puestos": [{"puesto": "Peluquera", "otras": ["Stylist"]}]}


@pytest.fixture
def app(motor_app, bd_limpia, archivos):  # noqa: F811
    return crear_app(engine=motor_app, identidad=IdentidadFalsa())


def _guardar(c, h, **cambios):
    p = c.get("/api/preferencias").json()
    r = c.put("/api/preferencias", headers=h, json={**p, **cambios})
    assert r.status_code == 200, r.text


def test_guardar_un_puesto_pide_sus_formas_una_vez_y_la_busqueda_las_usa(app, motor_app, motor_migrador):
    c, h, _ = entrar(app)
    _oferta(motor_app, titulo="Senior Stylist", familia="otros")
    _guardar(c, h, puestos=["Peluquera"])
    modelo = ProveedorSimulado([RESPUESTA])
    assert worker.procesar_una(motor_app, modelo) == "hecha"
    assert len(modelo.llamadas) == 1 and "Peluquera" in modelo.llamadas[0]["usuario"]
    assert c.get("/api/preferencias").json()["sinonimos"] == {"Peluquera": ["Stylist"]}
    (p,) = c.get("/api/preferencias/opciones").json()["puestos"]
    assert (p["n"], p["tambien"]) == (1, ["Stylist"])
    _guardar(c, h)
    assert worker.procesar_una(motor_app, ProveedorSimulado([])) is None  # ya las tiene


def test_lo_que_envia_el_navegador_no_pisa_las_formas(app, motor_app):
    c, h, _ = entrar(app)
    _guardar(c, h, puestos=["Peluquera"])
    worker.procesar_una(motor_app, ProveedorSimulado([RESPUESTA]))
    _guardar(c, h, sinonimos={"Peluquera": ["Directora"]})
    assert c.get("/api/preferencias").json()["sinonimos"] == {"Peluquera": ["Stylist"]}
