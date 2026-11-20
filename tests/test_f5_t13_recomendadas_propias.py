"""Fase 5 · T13: Recomendadas lleva TODAS las propias, con su marca y el aviso del auditor (RF-5.3e)."""
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
FUERA = {"sector": "tecnologia", "familia": "desarrollo_software", "nivel": "senior", "stack": []}


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
    return c, {"X-CSRF-Token": c.get("/api/yo").json()["csrf"]}


def _perfil(motor, motor_migrador):
    with motor_migrador.connect() as s:
        u = s.execute(text("select id from usuarias where google_sub='google-A'")).scalar_one()
    base = {"taxonomia": TAX, "experiencias": [
        {"puesto": "Camarera", "empresa": "Bar Sol",
         "origen": {"fuente": "cv", "cv_id": 1, "fragmento": "Camarera en Bar Sol, 2020-2023"}}]}
    with sesion_de(motor, u) as s:
        pid, version = perfiles.nueva_version(s, u)
        perfiles.guardar_perfil(s, u, pid, Perfil.model_validate({**base, "version": version}), "# Ana")


def _matches(ids, nota=85):
    return {"matches": [{"oferta_id": i, "nota": nota, "condiciones": "alto",
                         "cita_perfil": "Camarera en Bar Sol", "cita_oferta": "Camarera de sala",
                         "explicacion": "Tiene experiencia en sala. La oferta pide camarera de sala."}
                        for i in ids]}


def _pegar(c, h, motor, texto, extraccion, auditor, tax=TAX):
    oid = c.post("/ofertas", headers=h, json={"texto": texto}).json()["id"]
    prov = ProveedorSimulado([extraccion, auditor, tax])
    while worker.procesar_una(motor, prov, resolver=None):
        pass
    return oid


def test_las_propias_salen_aunque_no_pasen_filtros_ni_rango_ni_el_auditor(app, motor_app, motor_migrador):
    c, h = _entrar(app)
    base = {"titulo": "Camarera de sala", "empresa": "Hotel Mar", "fecha_publicacion": "2026-11-01"}
    ok = {"generica": False, "fraude": False}
    # 1) no pasa los filtros de Preferencias (otro sector y nivel) y su nota queda fuera del rango
    fuera = _pegar(c, h, motor_app, "Programador senior en Acme. Publicada 2026-11-01", base, ok, FUERA)
    # 2) pegada dos veces: no se duplica, sigue siendo una sola
    primera = _pegar(c, h, motor_app, "Camarera de sala en Hotel Mar. Publicada 2026-11-01", base, ok)
    repetida = _pegar(c, h, motor_app, "Camarera de sala en Hotel Mar. Publicada 2026-11-01", base, ok)
    assert repetida == primera
    # 3) marcada como fraude por el auditor (con una señal literal del texto)
    fraude = _pegar(c, h, motor_app, "Camarera. Paga 50 € por adelantado. Publicada 2026-11-01", base,
                    {"generica": False, "fraude": True, "senales_fraude": ["Paga 50 € por adelantado"]})
    ids = [fuera, primera, fraude]
    _perfil(motor_app, motor_migrador)  # el perfil llega después: nada se ha puntuado todavía
    c.put("/api/preferencias", headers=h, json={**c.get("/api/preferencias").json(),
                                                 "familias": ["hosteleria_restauracion"],
                                                 "niveles": ["junior"], "rango_min": 90, "rango_max": 100})
    assert c.post("/api/recomendar", headers=h).status_code == 202  # puntúa también las propias
    while worker.procesar_una(motor_app, ProveedorSimulado([_matches(ids, 40)])):
        pass
    r = {x["id"]: x for x in c.get("/api/recomendaciones").json()["recomendaciones"]}
    assert set(ids) <= set(r)
    for i in ids:
        assert r[i]["propia"] is True and r[i]["nota"] == 40 and r[i]["analizada_en"]
    assert r[fraude]["aviso_auditor"].startswith("Posibles señales de fraude")
    assert "Paga 50 € por adelantado" in r[fraude]["aviso_auditor"]
    assert r[primera]["aviso_auditor"] is None
    # y desde ahí se puede preparar la candidatura, también con la marcada como fraude
    for i in (fraude, primera):
        assert c.post("/api/candidaturas", headers=h, json={"oferta_id": i}).status_code != 404


def test_las_del_catalogo_siguen_sin_marca_y_con_sus_filtros(app, motor_app, motor_migrador):
    from horma.web.db import sesion_sistema
    c, h = _entrar(app)
    _perfil(motor_app, motor_migrador)
    with sesion_sistema(motor_app) as s:
        s.execute(text("insert into ofertas (texto_crudo, estado, titulo, sector, familia, nivel, fantasma, "
                       "fraude, salario_publicado) values ('t', 'procesada', 'Del catálogo', 'tecnologia', "
                       "'desarrollo_software', 'senior', false, false, false)"))
    c.put("/api/preferencias", headers=h, json={**c.get("/api/preferencias").json(),
                                                 "familias": ["hosteleria_restauracion"]})
    assert c.get("/api/recomendaciones").json()["recomendaciones"] == []


def test_el_aviso_de_fantasma_no_sale_en_las_propias_pero_el_de_fraude_si():          # P19, 20-nov
    from horma.web.routers.recomendaciones import _aviso_auditor
    base = {"fraude": False, "senales_fraude": [], "fantasma": True, "motivos_fantasma": ["sin_fecha"]}
    assert _aviso_auditor(base) is None
    assert _aviso_auditor({**base, "fraude": True, "senales_fraude": ["Paga 50 €"]}) == "Posibles señales de fraude: Paga 50 €"
