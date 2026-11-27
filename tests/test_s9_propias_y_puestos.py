"""S9 · RF-10.6g y RF-10.6h: la oferta que añade la usuaria se ve siempre (si ella las incluye) y su puesto
entra en «Qué buscas» si ninguno de sus puestos lo cubre."""
import pytest

from horma.llm.simulado import ProveedorSimulado
from horma.schemas.preferencias import Preferencias
from horma.tools.normalizar_titulo import casa_con_puestos
from horma.web.queue import worker
from tests.test_f5_t13_recomendadas_propias import _entrar, _pegar, app  # noqa: F401 (fixture)


def test_casa_con_puestos_usa_la_misma_regla_que_el_filtro():
    assert casa_con_puestos("Jefa de sala", ["Jefe de sala"])            # género
    assert casa_con_puestos("Auxiliar administrativa de RRHH", ["Auxiliar administrativo/a"])
    assert not casa_con_puestos("Gestor/a administrativo/a", ["Auxiliar administrativo/a"])
    assert not casa_con_puestos("Recepcionista", [])


def test_incluir_propias_viene_marcada_por_defecto():
    assert Preferencias().incluir_propias is True


@pytest.mark.bd
def test_la_propia_se_ve_y_su_puesto_se_anade_a_que_buscas(app, motor_app):  # noqa: F811
    c, h = _entrar(app)
    prefs = c.get("/api/preferencias").json()
    assert c.put("/api/preferencias", headers=h,
                 json={**prefs, "puestos": ["Jefe de sala"]}).status_code == 200
    worker.procesar_una(motor_app, ProveedorSimulado([]))  # los sinónimos del puesto (RF-12.4c)
    ok = {"generica": False, "fraude": False}
    oid = _pegar(c, h, motor_app, "Recepcionista en Hotel Mar. Publicada 2026-11-01",
                 {"titulo": "Recepcionista", "empresa": "Hotel Mar", "fecha_publicacion": "2026-11-01"}, ok)
    ids = [x["id"] for x in c.get("/api/recomendaciones").json()["recomendaciones"]]
    assert oid in ids                                                    # RF-10.6g
    prefs = c.get("/api/preferencias").json()
    assert prefs["puestos"] == ["Jefe de sala", "Recepcionista"]          # RF-10.6h
    assert prefs["origen"]["puestos"] == "usuaria"
    # Otra que ya cubre un puesto (con otro género) no añade nada
    _pegar(c, h, motor_app, "Jefa de sala en Bar Sol. Publicada 2026-11-02",
           {"titulo": "Jefa de sala", "empresa": "Bar Sol", "fecha_publicacion": "2026-11-02"}, ok)
    assert c.get("/api/preferencias").json()["puestos"] == ["Jefe de sala", "Recepcionista"]
    # Desmarcada la casilla, las propias no salen
    prefs = c.get("/api/preferencias").json()
    c.put("/api/preferencias", headers=h, json={**prefs, "incluir_propias": False})
    assert oid not in [x["id"] for x in c.get("/api/recomendaciones").json()["recomendaciones"]]


@pytest.mark.bd
def test_sin_puestos_no_se_anade_ninguno(app, motor_app):  # noqa: F811
    """Con la lista vacía no filtra nada: añadir uno empezaría a esconder ofertas."""
    c, h = _entrar(app)
    _pegar(c, h, motor_app, "Recepcionista en Hotel Mar. Publicada 2026-11-01",
           {"titulo": "Recepcionista", "empresa": "Hotel Mar", "fecha_publicacion": "2026-11-01"},
           {"generica": False, "fraude": False})
    assert c.get("/api/preferencias").json()["puestos"] == []
