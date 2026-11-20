"""Fase 5 · T14-T15: pestaña «Añadir oferta» y marca «Añadida por ti» en Ofertas (RF-5.3b/c/e)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from horma.llm.simulado import ProveedorSimulado
from horma.web.main import crear_app
from horma.web.queue import worker
from horma.web.services import ofertas as servicio

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior", "stack": []}


class IdentidadFalsa:
    async def redirigir(self, request, redirect_uri):
        from starlette.responses import RedirectResponse
        return RedirectResponse("https://accounts.google.test/auth")

    async def sub_desde_callback(self, request) -> str:
        return request.query_params["code"]


def leer(nombre):
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


def test_el_formulario_sale_de_la_portada_y_vive_en_su_pestana():
    index, app_js = leer("index.html"), leer("catalogo.js")
    assert "<textarea" not in index and "Procesar oferta" not in index and 'id="formulario"' not in index
    assert "formulario" not in app_js
    nueva = leer("anadir-oferta.html")
    assert "<textarea" in nueva and 'id="formulario"' in nueva and 'id="pestanas"' in nueva
    assert "/static/anadir-oferta.js" in nueva and "<script>" not in nueva
    js = leer("anadir-oferta.js")
    assert '"/ofertas"' in js and "POST" in js and "/api/recomendaciones" in js and "/api/ofertas/propias" in js  # noqa: E501
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js


@pytest.mark.bd
def test_la_pagina_se_sirve_con_sesion_y_sin_ella_va_a_la_portada(motor_app, bd_limpia):
    app = crear_app(engine=motor_app, identidad=IdentidadFalsa())
    c = TestClient(app, follow_redirects=False)
    assert c.get("/anadir-oferta").status_code == 302
    assert c.get("/auth/google/callback?code=google-A").status_code == 302
    r = c.get("/anadir-oferta")
    assert r.status_code == 200 and '<script src="/static/anadir-oferta.js"' in r.text


@pytest.mark.bd
def test_ofertas_marca_como_propia_solo_a_su_duena(motor_app, bd_limpia, monkeypatch):
    monkeypatch.setenv("HORMA_ADMINS", "google-A,google-B")
    from horma import config
    config.ajustes.cache_clear()
    app = crear_app(engine=motor_app, identidad=IdentidadFalsa())
    ana, berta = (TestClient(app, follow_redirects=False) for _ in range(2))
    ana.get("/auth/google/callback?code=google-A")
    berta.get("/auth/google/callback?code=google-B")
    servicio.recibir(motor_app, "Oferta del catálogo")
    h = {"X-CSRF-Token": ana.get("/api/yo").json()["csrf"]}
    assert ana.post("/ofertas", headers=h, json={"texto": "Camarera. 2026-11-01"}).status_code == 201
    prov = ProveedorSimulado([{"titulo": "Del catálogo"}, {"generica": False, "fraude": False}, TAX])
    while worker.procesar_una(motor_app, prov, resolver=None):
        pass
    marcas = {o["id"]: o["propia"] for o in ana.get("/ofertas").json()}
    assert sorted(marcas.values()) == [False, True]
    assert [o["propia"] for o in berta.get("/ofertas").json()] == [False]
    assert "Añadida por una usuaria" in leer("catalogo.js")
    config.ajustes.cache_clear()
