"""T15 y T16 (RF-4.6, RF-4.6c): PWA, cabeceras de producción, arranque seguro y /salud. Sin BD."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from horma.config import Ajustes
from horma.web import main as principal

ESTATICOS = Path(__file__).resolve().parent.parent / "horma/web/static"
PROHIBIDO = ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function")
SECRETO = "s" * 40
BUENA = dict(session_secret=SECRETO, google_redirect_uri="https://horma.example/auth/google/callback",
             database_url="postgresql+psycopg://horma_app:Xk9-largo-y-unico@postgres:5432/horma")


def _app(monkeypatch, **cambios):
    ajustes = Ajustes(_env_file=None, **cambios)
    monkeypatch.setattr(principal, "ajustes", lambda: ajustes)
    return principal.crear_app(engine=create_engine("sqlite://"), identidad=object())


@pytest.fixture
def cliente(monkeypatch):
    with TestClient(_app(monkeypatch, app_env="development"), follow_redirects=False) as c:
        yield c


# --- T15: PWA -------------------------------------------------------------------------------
def test_el_manifest_se_sirve_con_su_tipo_y_tiene_los_iconos(cliente):
    r = cliente.get("/manifest.webmanifest")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/manifest+json")
    m = r.json()
    assert m["name"] == "Horma" and m["display"] == "standalone" and m["start_url"] == "/"
    tamanos = {(i["sizes"], i["purpose"]) for i in m["icons"]}
    assert {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")} <= tamanos
    for i in m["icons"]:
        assert cliente.get(i["src"]).status_code == 200


def test_el_service_worker_se_sirve_en_la_raiz_y_se_revalida(cliente):
    r = cliente.get("/sw.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]
    assert r.headers["cache-control"] == "no-cache"


def test_el_service_worker_no_guarda_nada_de_la_api():
    js = (ESTATICOS / "sw.js").read_text(encoding="utf-8")
    assert 'startsWith("/api/")' in js and 'startsWith("/auth/")' in js
    # El único sitio donde se escribe en la caché es la rama de /static/, que va después del descarte
    assert js.count("c.put(") == 1
    assert js.index('startsWith("/api/")') < js.index('startsWith("/static/")') < js.index("c.put(")
    assert 'method !== "GET"' in js


def test_existe_la_pagina_sin_conexion_y_el_sw_la_precarga(cliente):
    assert cliente.get("/static/offline.html").status_code == 200
    assert "Sin conexión" in (ESTATICOS / "offline.html").read_text(encoding="utf-8")
    sw = (ESTATICOS / "sw.js").read_text(encoding="utf-8")
    assert "/static/offline.html" in sw and "/static/tokens.css" in sw  # fase 6: el estilo 2c también sin red


def test_la_csp_permite_manifest_y_worker_propios(cliente):
    csp = cliente.get("/salud").headers["content-security-policy"]
    assert "manifest-src 'self'" in csp and "worker-src 'self'" in csp


def test_todas_las_paginas_enlazan_el_manifest_y_registran_el_sw():
    for html in ESTATICOS.glob("*.html"):
        if html.name == "offline.html":
            continue
        t = html.read_text(encoding="utf-8")
        assert 'rel="manifest"' in t and "/static/pwa.js" in t, html.name


def test_el_js_de_la_pwa_no_usa_innerhtml():
    for nombre in ("sw.js", "pwa.js"):
        js = (ESTATICOS / nombre).read_text(encoding="utf-8")
        assert not [p for p in PROHIBIDO if p in js], nombre


# --- T16: cabeceras, arranque en producción y /salud ----------------------------------------
def test_en_produccion_salen_hsts_y_permissions_policy(monkeypatch):
    with TestClient(_app(monkeypatch, app_env="produccion", **BUENA)) as c:
        h = c.get("/salud").headers
    assert "max-age=" in h["strict-transport-security"]
    assert "camera=()" in h["permissions-policy"]


def test_en_desarrollo_no_sale_hsts(cliente):
    h = cliente.get("/salud").headers
    assert "strict-transport-security" not in h and "permissions-policy" not in h


@pytest.mark.parametrize("cambio", [
    dict(session_secret="corto"),
    dict(session_secret=""),
    dict(session_secret="cambia-esto-por-un-secreto-largo-de-verdad"),
    dict(database_url="postgresql+psycopg://horma_app:@postgres:5432/horma"),
    dict(database_url="postgresql+psycopg://horma_app:<HORMA_APP_PASSWORD>@postgres:5432/horma"),
    dict(database_url="postgresql+psycopg://horma_app:password@postgres:5432/horma"),
    dict(google_redirect_uri="http://horma.example/auth/google/callback"),
    dict(google_redirect_uri="http://localhost:8000/auth/google/callback"),
])
def test_en_produccion_no_arranca_con_secretos_de_ejemplo(monkeypatch, cambio):
    with pytest.raises(RuntimeError, match="producción"):
        _app(monkeypatch, app_env="produccion", **{**BUENA, **cambio})


def test_en_produccion_con_todo_bien_arranca(monkeypatch):
    assert _app(monkeypatch, app_env="produccion", **BUENA) is not None


def test_el_mensaje_de_arranque_no_revela_los_secretos(monkeypatch):
    with pytest.raises(RuntimeError) as e:
        _app(monkeypatch, app_env="produccion", **{**BUENA, "session_secret": "corto"})
    assert "corto" not in str(e.value) and "Xk9" not in str(e.value)


def test_salud_responde_sin_datos_y_sin_sesion(cliente):
    r = cliente.get("/salud")
    assert r.status_code == 200 and json.loads(r.text) == {"estado": "ok"}
