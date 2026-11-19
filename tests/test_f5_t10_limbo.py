"""Fase 5 · T10: reproduce el «limbo» de las ofertas pegadas (RF-5.3).

Una oferta que la usuaria pega en la web debe llegar a Recomendadas YA puntuada, sin pulsar
«Recomendar». Hoy no pasa por tres causas, una por caso:
- sin nota: nada encola el matcher al terminar `procesar_oferta` (caso base);
- repetida: antes `para_procesar` la marcaba `repetida` → fantasma; ahora la segunda no se crea;
- sin fecha: el flujo marca `sin_fecha` → fantasma → no recomendable.
Los tres casos fallaron hasta T12 (puntuar solo) y T13 (RF-5.3e, P17: todas las propias salen)."""
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
TEXTO = "Camarera de sala en Hotel Mar, Valencia. Publicada: 2026-11-01"
CON_FECHA = {"titulo": "Camarera de sala", "empresa": "Hotel Mar", "fecha_publicacion": "2026-11-01"}
SIN_FECHA = {"titulo": "Camarera de sala", "empresa": "Hotel Mar"}


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


def _con_perfil(motor, motor_admin, sub="google-A"):
    with motor_admin.connect() as s:
        u = s.execute(text("select id from usuarias where google_sub=:s"), {"s": sub}).scalar_one()
    base = {"taxonomia": TAX, "experiencias": [
        {"puesto": "Camarera", "empresa": "Bar Sol",
         "origen": {"fuente": "cv", "cv_id": 1, "fragmento": "Camarera en Bar Sol, 2020-2023"}}]}
    with sesion_de(motor, u) as s:
        pid, version = perfiles.nueva_version(s, u)
        perfiles.guardar_perfil(s, u, pid, Perfil.model_validate({**base, "version": version}),
                                "# Ana\nCamarera en Bar Sol, 2020-2023")


def _pegar(c, h, textos):
    ids = []
    for texto in textos:
        r = c.post("/ofertas", headers=h, json={"texto": texto})
        if r.json()["id"] in ids:  # la misma oferta otra vez: no se duplica (200, el mismo id)
            assert r.status_code == 200
            continue
        assert r.status_code == 201
        ids.append(r.json()["id"])
    return ids


def _matches(ids):
    return {"matches": [{"oferta_id": i, "nota": 85, "condiciones": "alto",
                         "cita_perfil": "Camarera en Bar Sol", "cita_oferta": "Camarera de sala",
                         "explicacion": "Tiene experiencia en sala. La oferta pide camarera de sala."}
                        for i in ids]}


def _recomendadas(c):
    return {x["id"]: x for x in c.get("/api/recomendaciones").json()["recomendaciones"]}


def _correr_el_worker(motor, ids, extraccion):
    """Deja correr la cola SIN que la usuaria pulse «Recomendar»: procesa cada oferta y, después, lo que
    el sistema haya encolado por su cuenta (puntuarlas), con las respuestas en el orden en que se piden."""
    prov = ProveedorSimulado([extraccion, AUDITOR, TAX] * len(ids) + [_matches(ids)])
    while worker.procesar_una(motor, prov, resolver=None):
        pass


@pytest.mark.parametrize("extraccion, repetir", [
    pytest.param(CON_FECHA, False, id="una oferta pegada"),
    pytest.param(CON_FECHA, True, id="la misma oferta pegada dos veces (repetida)"),
    pytest.param(SIN_FECHA, False, id="oferta sin fecha (sin_fecha)"),
])
def test_una_oferta_pegada_llega_a_recomendadas_puntuada_sin_pulsar_recomendar(
        app, motor_app, motor_migrador, extraccion, repetir):
    c, h = _entrar(app)
    _con_perfil(motor_app, motor_migrador)
    ids = _pegar(c, h, [TEXTO] * (2 if repetir else 1))
    assert len(ids) == 1  # pegarla dos veces deja una sola
    _correr_el_worker(motor_app, ids, extraccion)  # nadie llama a /api/recomendar
    salida = _recomendadas(c)
    for oferta_id in ids:
        assert oferta_id in salida, f"la oferta {oferta_id} no llega a Recomendadas"
        assert salida[oferta_id]["nota"] == 85, f"la oferta {oferta_id} llega sin puntuar"
