"""Paso 1 · T03 (spec 011, parte 1): la medición cuenta bien y solo la ven administradoras (RF-11.1)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_f1_t10_t15_api_ingesta import ADMIN, IdentidadFalsa, entrar

from horma import config
from horma.tools.resolver_destino import Destino
from horma.web.db import sesion_sistema
from horma.web.main import crear_app
from horma.web.services.envios import resumir

URLS = [
    "https://a.teamtailor.com/jobs/1", "https://b.teamtailor.com/jobs/2",
    "https://jobs.lever.co/x/1", "https://www.infojobs.net/of-i1",
    "https://www.linkedin.com/jobs/view/1", "https://propia.example/empleo", None,
]


def _resolver(url):
    if "linkedin" in url or "propia" in url:
        return Destino(portal=None, automatico=False, motivo="x")
    nombre = "Teamtailor" if "teamtailor" in url else "Lever" if "lever" in url else "InfoJobs"
    return Destino(portal=nombre, automatico=True, exige_cuenta=nombre == "InfoJobs", url_final=url)


def test_la_tabla_cuenta_portal_ofertas_y_exige_cuenta():
    r = resumir(URLS, _resolver)
    assert r["total"] == 7 and r["automaticas"] == 4 and r["no_automaticas"] == 3 and r["exigen_cuenta"] == 1
    assert [(f["portal"], f["ofertas"], f["exige_cuenta"]) for f in r["filas"]] == [
        ("Teamtailor", 2, False), ("InfoJobs", 1, True), ("Lever", 1, False), ("No automático", 3, False)]


def test_una_direccion_repetida_se_resuelve_una_sola_vez():
    llamadas = []

    def contando(url):
        llamadas.append(url)
        return _resolver(url)

    resumir(["https://jobs.lever.co/x/1"] * 5, contando)
    assert llamadas == ["https://jobs.lever.co/x/1"]


@pytest.mark.bd
def test_la_api_solo_la_ven_administradoras(motor_app, bd_limpia, monkeypatch):
    monkeypatch.setenv("HORMA_ADMINS", ADMIN)
    config.ajustes.cache_clear()
    with sesion_sistema(motor_app) as s:
        for i, u in enumerate(["https://jobs.lever.co/x/1", "https://www.linkedin.com/jobs/view/1"]):
            s.execute(text("insert into ofertas (texto_crudo, url, huella) values (:t, :u, :h)"),
                      {"t": f"oferta {i}", "u": u, "h": f"h{i}"})
    with TestClient(crear_app(engine=motor_app, identidad=IdentidadFalsa()), follow_redirects=False) as c:
        assert c.get("/api/admin/envios/medicion").status_code == 401
        h = entrar(c, "google-normal")
        assert c.get("/api/admin/envios/medicion").status_code == 403
        assert c.get("/envios").status_code == 403
        c.post("/auth/logout", headers=h)
        entrar(c)
        r = c.get("/api/admin/envios/medicion")
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo["total"] == 2 and cuerpo["automaticas"] == 1 and cuerpo["no_automaticas"] == 1
        assert c.get("/envios").status_code == 200
    config.ajustes.cache_clear()
