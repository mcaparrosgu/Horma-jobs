"""Fase 5 · T12: las ofertas propias se puntúan solas (RF-5.3d), con la puerta simulada."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from horma import config
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.perfil import Perfil
from horma.web.db import sesion_de
from horma.web.main import crear_app
from horma.web.queue import worker
from horma.web.repositories import perfiles

pytestmark = pytest.mark.bd

TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior",
       "stack": []}
AUDITOR = {"generica": False, "fraude": False}
EXTRACCION = {"titulo": "Camarera de sala", "empresa": "Hotel Mar", "fecha_publicacion": "2026-11-01"}
CV = b"Ana Perez\nCamarera en Bar Sol, 2020-2023\nIngles B2\n"


class IdentidadFalsa:
    async def redirigir(self, request, redirect_uri):
        from starlette.responses import RedirectResponse
        return RedirectResponse("https://accounts.google.test/auth")

    async def sub_desde_callback(self, request) -> str:
        return request.query_params["code"]


@pytest.fixture
def app(motor_app, bd_limpia, tmp_path, monkeypatch):
    monkeypatch.setenv("RUTA_ARCHIVOS", str(tmp_path / "archivos"))
    config.ajustes.cache_clear()
    yield crear_app(engine=motor_app, identidad=IdentidadFalsa())
    config.ajustes.cache_clear()


def _entrar(app, sub="google-A"):
    c = TestClient(app, follow_redirects=False)
    assert c.get(f"/auth/google/callback?code={sub}").status_code == 302
    yo = c.get("/api/yo").json()
    return c, {"X-CSRF-Token": yo["csrf"]}


def _usuaria(motor_migrador, sub="google-A"):
    with motor_migrador.connect() as s:
        return s.execute(text("select id from usuarias where google_sub=:s"), {"s": sub}).scalar_one()


def _perfil_hecho(motor, u):
    base = {"taxonomia": TAX, "experiencias": [
        {"puesto": "Camarera", "empresa": "Bar Sol",
         "origen": {"fuente": "cv", "cv_id": 1, "fragmento": "Camarera en Bar Sol, 2020-2023"}}]}
    with sesion_de(motor, u) as s:
        pid, version = perfiles.nueva_version(s, u)
        perfiles.guardar_perfil(s, u, pid, Perfil.model_validate({**base, "version": version}),
                                "# Ana\nCamarera en Bar Sol, 2020-2023")


RELLENO = " Se busca persona con experiencia en atención al cliente, turnos rotativos y contrato indefinido."


def _pegar(c, h, motor, n=1):
    ids = []
    for i in range(n):
        ids.append(c.post("/ofertas", headers=h, json={"texto": f"Camarera de sala {i}. 2026-11-01.{RELLENO}"}
                          ).json()["id"])
    return ids


def _procesar_ofertas(motor, n):
    for _ in range(n):
        assert worker.procesar_una(motor, ProveedorSimulado([EXTRACCION, AUDITOR, TAX]),
                                   resolver=None) == "hecha"


def _matches(ids):
    return {"matches": [{"oferta_id": i, "nota": 85, "condiciones": "alto",
                         "cita_perfil": "Camarera en Bar Sol", "cita_oferta": "Camarera de sala",
                         "explicacion": "Tiene experiencia en sala. La oferta pide camarera de sala."}
                        for i in ids]}


def _tareas(motor_migrador, tipo):
    with motor_migrador.connect() as s:
        return s.execute(text("select estado, tope_coste, usuaria_id from tareas where tipo=:t "
                              "order by id"), {"t": tipo}).all()


def _notas(motor_migrador):
    with motor_migrador.connect() as s:
        return s.execute(text("select oferta_id, perfil_version, nota from matches "
                              "order by oferta_id, perfil_version")).all()


def test_la_oferta_pegada_queda_puntuada_sin_pulsar_recomendar(app, motor_app, motor_migrador):
    c, h = _entrar(app)
    _perfil_hecho(motor_app, _usuaria(motor_migrador))
    (oid,) = _pegar(c, h, motor_app)
    _procesar_ofertas(motor_app, 1)
    assert [t.estado for t in _tareas(motor_migrador, "puntuar_propias")] == ["pendiente"]
    assert worker.procesar_una(motor_app, ProveedorSimulado([_matches([oid])])) == "hecha"
    assert _notas(motor_migrador) == [(oid, 1, 85)]


def test_la_tarea_lleva_su_tope_de_coste_propio(app, motor_app, motor_migrador):
    c, h = _entrar(app)
    _perfil_hecho(motor_app, _usuaria(motor_migrador))
    _pegar(c, h, motor_app)
    _procesar_ofertas(motor_app, 1)
    (t,) = _tareas(motor_migrador, "puntuar_propias")
    assert float(t.tope_coste) == config.ajustes().tope_coste_puntuar_propias
    assert t.usuaria_id == _usuaria(motor_migrador)


def test_varias_ofertas_seguidas_comparten_una_sola_tarea(app, motor_app, motor_migrador):
    c, h = _entrar(app)
    _perfil_hecho(motor_app, _usuaria(motor_migrador))
    ids = _pegar(c, h, motor_app, n=2)
    _procesar_ofertas(motor_app, 2)
    assert len(_tareas(motor_migrador, "puntuar_propias")) == 1
    assert worker.procesar_una(motor_app, ProveedorSimulado([_matches(ids)])) == "hecha"
    assert [n for _, _, n in _notas(motor_migrador)] == [85, 85]


def test_una_oferta_del_catalogo_no_encola_nada(app, motor_app, motor_migrador):
    from horma.web.services import ofertas as servicio
    c, _ = _entrar(app)
    _perfil_hecho(motor_app, _usuaria(motor_migrador))
    servicio.recibir(motor_app, "Oferta del catálogo")
    _procesar_ofertas(motor_app, 1)
    assert _tareas(motor_migrador, "puntuar_propias") == []


def test_la_oferta_sin_perfil_se_puntua_sola_al_construirse_el_perfil(app, motor_app, motor_migrador):
    c, h = _entrar(app)
    (oid,) = _pegar(c, h, motor_app)
    _procesar_ofertas(motor_app, 1)
    # aún sin perfil: la tarea se encola pero no hay con qué puntuar, así que no llama al modelo
    prov = ProveedorSimulado([])
    assert worker.procesar_una(motor_app, prov) == "hecha" and prov.llamadas == []
    assert _notas(motor_migrador) == []
    cv = c.post("/api/cv", headers=h, files={"archivo": ("cv.md", CV)}, data={"clase": "fuente"}).json()
    extraccion = {"perfil": {"experiencias": [{
        "puesto": "Camarera", "empresa": "Bar Sol",
        "origen": {"fuente": "cv", "cv_id": cv["id"], "fragmento": "Camarera en Bar Sol, 2020-2023"}}]},
        "cv_maestro": "# Ana\nCamarera en Bar Sol, 2020-2023"}
    assert worker.procesar_una(motor_app, ProveedorSimulado([extraccion, TAX])) == "hecha"
    assert [t.estado for t in _tareas(motor_migrador, "puntuar_propias")] == ["hecha", "pendiente"]
    assert worker.procesar_una(motor_app, ProveedorSimulado([_matches([oid])])) == "hecha"
    assert _notas(motor_migrador) == [(oid, 1, 85)]


def test_tras_editar_el_perfil_las_propias_se_repuntuan_con_la_version_nueva(
        app, motor_app, motor_migrador):
    c, h = _entrar(app)
    _perfil_hecho(motor_app, _usuaria(motor_migrador))
    (oid,) = _pegar(c, h, motor_app)
    _procesar_ofertas(motor_app, 1)
    assert worker.procesar_una(motor_app, ProveedorSimulado([_matches([oid])])) == "hecha"
    cambio = {"campo": "experiencias", "indice": 0, "dato": {"puesto": "Camarera", "empresa": "Bar Luna"}}
    r = c.patch("/api/perfil/datos", headers=h, json=cambio)
    assert r.status_code == 201
    assert worker.procesar_una(motor_app, ProveedorSimulado([TAX])) == "hecha"  # clasificar_perfil
    assert worker.procesar_una(motor_app, ProveedorSimulado([_matches([oid])])) == "hecha"
    assert _notas(motor_migrador) == [(oid, 1, 85), (oid, 2, 85)]


def test_un_cambio_que_no_afecta_a_la_compatibilidad_no_repuntua(app, motor_app, motor_migrador):
    """RF-10.10c: corregir algo ajeno (el género de los puestos) no vuelve a puntuar ni a clasificar."""
    c, h = _entrar(app)
    _perfil_hecho(motor_app, _usuaria(motor_migrador))
    (oid,) = _pegar(c, h, motor_app)
    _procesar_ofertas(motor_app, 1)
    assert worker.procesar_una(motor_app, ProveedorSimulado([_matches([oid])])) == "hecha"
    cambio = {"campo": "genero_puestos", "dato": {"valor": "femenino"}}
    assert c.patch("/api/perfil/datos", headers=h, json=cambio).status_code == 201
    assert worker.procesar_una(motor_app, ProveedorSimulado([])) is None  # no hay tarea nueva
    assert _notas(motor_migrador) == [(oid, 1, 85)]
