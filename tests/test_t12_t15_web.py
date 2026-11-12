from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from horma.llm.simulado import ProveedorSimulado
from horma.web.main import crear_app
from horma.web.queue import worker

pytestmark = pytest.mark.bd

TEXTO = ("Se busca camarera en Bar La Marina, Valencia.\nContrato indefinido, presencial.\n"
         "Salario: entre 16000 y 18000 euros brutos anuales.")
OFERTA = {"titulo": "Camarera", "empresa": "Bar La Marina", "ubicacion": "Valencia",
          "contrato": "indefinido", "remoto": False,
          "salario": {"minimo": 16000, "maximo": 18000, "moneda": "EUR"}}


class IdentidadFalsa:
    """Sustituye a Google: el `code` de la URL es directamente el identificador de la usuaria."""

    async def redirigir(self, request, redirect_uri):
        from starlette.responses import RedirectResponse

        return RedirectResponse("https://accounts.google.test/auth")

    async def sub_desde_callback(self, request) -> str:
        return request.query_params["code"]


@pytest.fixture
def cliente(motor_app, bd_limpia):
    app = crear_app(engine=motor_app, identidad=IdentidadFalsa())
    with TestClient(app, follow_redirects=False) as c:
        yield c


def entrar(c, sub="google-A") -> str:
    r = c.get(f"/auth/google/callback?code={sub}")
    assert r.status_code == 302
    return c.get("/api/yo").json()["csrf"]


# --- T12: acceso, sesión, CSRF ---------------------------------------------------------------
def test_sin_sesion_la_api_responde_401(cliente):
    assert cliente.get("/ofertas").status_code == 401
    assert cliente.post("/ofertas", json={"texto": "x"}).status_code == 401
    assert cliente.get("/api/yo").status_code == 401


def test_login_redirige_al_proveedor(cliente):
    r = cliente.get("/auth/google/login")
    assert r.status_code in (302, 307) and "google" in r.headers["location"]


def test_cookie_de_sesion_es_httponly_y_samesite(cliente):
    r = cliente.get("/auth/google/callback?code=google-A")
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_post_sin_csrf_o_con_csrf_falso_es_403(cliente):
    csrf = entrar(cliente)
    assert cliente.post("/ofertas", json={"texto": TEXTO}).status_code == 403
    assert cliente.post("/ofertas", json={"texto": TEXTO},
                        headers={"X-CSRF-Token": "falso"}).status_code == 403
    assert cliente.post("/ofertas", json={"texto": TEXTO},
                        headers={"X-CSRF-Token": csrf}).status_code == 201


def test_logout_cierra_la_sesion(cliente):
    csrf = entrar(cliente)
    assert cliente.post("/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    assert cliente.get("/api/yo").status_code == 401


# --- T13: API de ofertas ---------------------------------------------------------------------
def test_texto_vacio_o_enorme_se_rechaza(cliente):
    csrf = entrar(cliente)
    h = {"X-CSRF-Token": csrf}
    assert cliente.post("/ofertas", json={"texto": ""}, headers=h).status_code == 422
    assert cliente.post("/ofertas", json={"texto": "a" * 20001}, headers=h).status_code == 422


def test_cada_usuaria_lista_solo_sus_ofertas(cliente):
    csrf_a = entrar(cliente, "google-A")
    cliente.post("/ofertas", json={"texto": TEXTO}, headers={"X-CSRF-Token": csrf_a})
    assert len(cliente.get("/ofertas").json()) == 1
    cliente.post("/auth/logout", headers={"X-CSRF-Token": csrf_a})
    entrar(cliente, "google-B")
    assert cliente.get("/ofertas").json() == []


# --- T14: web plana, CSP y escape ------------------------------------------------------------
def test_la_portada_lleva_csp_estricta_y_cabeceras_de_seguridad(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    csp = r.headers["content-security-policy"]
    assert "default-src 'self'" in csp and "script-src 'self'" in csp
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in csp


def test_el_js_pinta_siempre_con_textcontent():
    static = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
    js = (static / "app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js and "eval(" not in js
    assert "textContent" in js
    assert "<script" not in (static / "index.html").read_text(encoding="utf-8").replace(
        '<script src="/static/app.js"', "")


# --- T15: camino completo --------------------------------------------------------------------
def test_camino_completo_oferta_pegada_worker_y_lista(cliente, motor_app):
    csrf = entrar(cliente)
    r = cliente.post("/ofertas", json={"texto": TEXTO}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 201 and r.json()["estado"] == "pendiente"
    assert cliente.get("/ofertas").json()[0]["estado"] == "pendiente"

    assert worker.procesar_una(motor_app, ProveedorSimulado([OFERTA])) == "hecha"

    oferta = cliente.get("/ofertas").json()[0]
    assert oferta["estado"] == "procesada" and oferta["titulo"] == "Camarera"
    assert oferta["empresa"] == "Bar La Marina" and oferta["salario_minimo"] == 16000


def test_una_oferta_con_script_se_guarda_como_texto_y_no_rompe_nada(cliente, motor_app):
    csrf = entrar(cliente)
    cliente.post("/ofertas", json={"texto": "<script>alert(1)</script> Cajero en Tienda X"},
                 headers={"X-CSRF-Token": csrf})
    worker.procesar_una(motor_app, ProveedorSimulado([{"titulo": "<script>alert(1)</script>"}]))
    r = cliente.get("/ofertas")
    assert r.headers["content-type"].startswith("application/json")
    assert r.json()[0]["titulo"] == "<script>alert(1)</script>"  # dato inerte; el JS lo pinta como texto
