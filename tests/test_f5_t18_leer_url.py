"""Fase 5 · T18: `leer_pagina`, tabla `importaciones` y `POST /ofertas/url` (RF-5.3f, RF-5.3g, RF-5.3j)."""
import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from horma import config
from horma.llm.simulado import ProveedorSimulado
from horma.tools import validar_url as validar
from horma.tools.leer_pagina import MAX_CARACTERES, LecturaFallida, leer_pagina
from horma.web.main import crear_app
from horma.web.queue import worker

TOKEN = "token-secreto-de-prueba"
URL = "https://job-boards.greenhouse.io/hotelmar/jobs/1"
PAGINA = "# Camarera de sala\n\nHotel Mar busca camarera de sala para la temporada. " * 12


# --- leer_pagina (sin base de datos) -----------------------------------------------------------
def _cliente(responder):
    return httpx.Client(transport=httpx.MockTransport(responder))


def _ok(markdown=PAGINA):
    return lambda req: httpx.Response(201, json=[{"markdown": markdown, "metadata": {}}])


def test_lee_la_pagina_con_el_token_en_la_cabecera_y_sin_proxies():
    vistas = []

    def responder(req):
        vistas.append(req)
        return httpx.Response(201, json=[{"markdown": PAGINA}])

    assert leer_pagina(URL, cliente=_cliente(responder), token=TOKEN) == PAGINA.strip()
    (req,) = vistas
    assert req.method == "POST" and req.url.host == "api.apify.com"
    assert "apify~rag-web-browser" in req.url.path
    assert req.headers["authorization"] == f"Bearer {TOKEN}"
    assert TOKEN not in str(req.url)
    cuerpo = json.loads(req.content)
    assert cuerpo["query"] == URL and cuerpo["maxResults"] == 1
    assert not [k for k in cuerpo if "proxy" in k.lower() or "unblock" in k.lower()]


def test_el_texto_leido_tiene_un_tamano_maximo():
    texto = leer_pagina(URL, cliente=_cliente(_ok("palabra " * 20000)), token=TOKEN)
    assert len(texto) == MAX_CARACTERES


@pytest.mark.parametrize("respuesta", [
    httpx.Response(500, text="boom"),
    httpx.Response(402, json={"error": "sin crédito"}),
    httpx.Response(201, json=[]),
    httpx.Response(201, json=[{"markdown": ""}]),
    httpx.Response(201, json=[{"markdown": "Acceso denegado"}]),
    httpx.Response(201, text="no es json"),
    httpx.Response(201, json={"no": "una lista"}),
])
def test_un_fallo_o_una_pagina_vacia_dan_lectura_fallida(respuesta):
    with pytest.raises(LecturaFallida) as e:
        leer_pagina(URL, cliente=_cliente(lambda req: respuesta), token=TOKEN)
    assert TOKEN not in str(e.value)


PAGINAS_DE_ERROR = [  # lo que devolvió Apify en la prueba real de T19 (18-nov) y otras páginas típicas
    "Not found - 404 error. Sorry, we couldn't find anything here. The job posting you're looking for "
    "might have closed, or it has been removed. (404 error). [Jobs at Tinybird](https://jobs.lever.co/tinybird)",
    "Barcelona Jobs: Tech, Creative & Multilingual Roles [Skip to main content](https://x.test/#main) " * 3,
    "Esta oferta ya no está disponible. La página que buscas no existe o ha sido eliminada. " * 5,
    "Access denied. Please verify you are human: complete the CAPTCHA to continue. " * 6,
    "Oferta no encontrada (error 404). Vuelve al listado de empleos de la empresa. " * 5,
]


@pytest.mark.parametrize("pagina", PAGINAS_DE_ERROR)
def test_una_pagina_de_error_o_sin_oferta_no_se_da_por_leida(pagina):
    with pytest.raises(LecturaFallida):
        leer_pagina(URL, cliente=_cliente(_ok(pagina)), token=TOKEN)


def test_una_oferta_larga_que_menciona_404_o_not_found_si_se_lee():
    oferta = ("Camarera de sala. Funciones: atender mesas, montar eventos y gestionar reservas. "
              "Si no encuentras la sala (not found), pregunta en recepción. "
              "Error 404 en la caja: avisa al jefe. ") * 25
    assert len(oferta) > 1500
    assert leer_pagina(URL, cliente=_cliente(_ok(oferta)), token=TOKEN)


def test_un_tiempo_agotado_da_lectura_fallida():
    def responder(req):
        raise httpx.ReadTimeout("lento", request=req)

    with pytest.raises(LecturaFallida):
        leer_pagina(URL, cliente=_cliente(responder), token=TOKEN)


def test_sin_token_no_se_llama_a_nadie():
    def responder(req):
        raise AssertionError("no debería llamar")

    with pytest.raises(LecturaFallida):
        leer_pagina(URL, cliente=_cliente(responder), token="")


def test_el_token_no_sale_en_ningun_log(caplog):
    caplog.set_level(logging.DEBUG)
    with pytest.raises(LecturaFallida):
        leer_pagina(URL, cliente=_cliente(lambda req: httpx.Response(500)), token=TOKEN)
    leer_pagina(URL, cliente=_cliente(_ok()), token=TOKEN)
    assert TOKEN not in caplog.text


def test_la_pestana_tiene_el_campo_de_url_y_pinta_con_textcontent():
    from pathlib import Path
    est = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
    html = (est / "anadir-oferta.html").read_text(encoding="utf-8")
    js = (est / "anadir-oferta.js").read_text(encoding="utf-8")
    assert 'id="url"' in html and "Apify" in html
    assert "/ofertas/url" in js and "innerHTML" not in js and "insertAdjacentHTML" not in js


# --- API y worker (con base de datos) ----------------------------------------------------------
TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior", "stack": []}
EXTRACCION = {"titulo": "Camarera de sala", "empresa": "Hotel Mar", "fecha_publicacion": "2026-11-01"}
AUDITOR = {"generica": False, "fraude": False}


class IdentidadFalsa:
    async def redirigir(self, request, redirect_uri):
        from starlette.responses import RedirectResponse
        return RedirectResponse("https://accounts.google.test/auth")

    async def sub_desde_callback(self, request) -> str:
        return request.query_params["code"]


@pytest.fixture
def app(motor_app, bd_limpia, tmp_path, monkeypatch):
    monkeypatch.setenv("RUTA_ARCHIVOS", str(tmp_path / "archivos"))
    monkeypatch.setenv("LIMITE_URL_HORA", "3")
    monkeypatch.setattr(validar, "_resolver", lambda host: ["151.101.1.1"])
    config.ajustes.cache_clear()
    yield crear_app(engine=motor_app, identidad=IdentidadFalsa())
    config.ajustes.cache_clear()


def _entrar(app, sub="google-A"):
    c = TestClient(app, follow_redirects=False)
    assert c.get(f"/auth/google/callback?code={sub}").status_code == 302
    return c, {"X-CSRF-Token": c.get("/api/yo").json()["csrf"]}


def _importaciones(motor_migrador):
    with motor_migrador.connect() as s:
        return s.execute(text("select id, usuaria_id, url, estado, motivo, oferta_id from importaciones "
                              "order by id")).mappings().all()


@pytest.mark.bd
def test_una_url_acaba_en_oferta_propia_con_su_url(app, motor_app, motor_migrador):
    c, h = _entrar(app)
    r = c.post("/ofertas/url", headers=h, json={"url": URL})
    assert r.status_code == 202 and r.json()["estado"] == "pendiente"
    importacion = r.json()["id"]
    leidas = []
    assert worker.procesar_una(motor_app, lector=lambda u: leidas.append(u) or PAGINA) == "hecha"
    assert leidas == [URL]
    (fila,) = _importaciones(motor_migrador)
    assert fila["estado"] == "leida" and fila["oferta_id"] and fila["id"] == importacion
    assert c.get(f"/ofertas/url/{importacion}").json() == {
        "id": importacion, "estado": "leida", "motivo": None, "oferta_id": fila["oferta_id"]}
    with motor_migrador.connect() as s:
        oferta = s.execute(text("select usuaria_id, url, texto_crudo from ofertas")).one()
    assert oferta.usuaria_id == fila["usuaria_id"] and oferta.url == URL and "Hotel Mar" in oferta.texto_crudo
    # sigue como una pegada: la oferta se procesa y es privada
    prov = ProveedorSimulado([EXTRACCION, AUDITOR, TAX])
    assert worker.procesar_una(motor_app, prov, resolver=None) == "hecha"


@pytest.mark.bd
def test_un_fallo_deja_la_importacion_en_error_con_motivo_fijo(app, motor_app, motor_migrador):
    c, h = _entrar(app)
    importacion = c.post("/ofertas/url", headers=h, json={"url": URL}).json()["id"]

    def falla(_url):
        raise LecturaFallida("detalle interno con https://api.apify.com/x?token=secreto")

    assert worker.procesar_una(motor_app, lector=falla) == "error"
    (fila,) = _importaciones(motor_migrador)
    assert fila["estado"] == "error" and fila["oferta_id"] is None
    assert "pega el texto" in fila["motivo"].lower() and "secreto" not in fila["motivo"]
    assert c.get(f"/ofertas/url/{importacion}").json()["estado"] == "error"
    with motor_migrador.connect() as s:
        assert s.execute(text("select count(*) from ofertas")).scalar_one() == 0


@pytest.mark.bd
@pytest.mark.parametrize("url", [
    "https://es.linkedin.com/jobs/view/1", "https://www.infojobs.net/oferta/1",
    "http://empresa.com/oferta", "https://127.0.0.1/oferta", "https://usuaria:clave@empresa.com/x",
])
def test_una_url_no_valida_o_vetada_da_422_con_el_motivo_y_no_encola(app, motor_migrador, url):
    c, h = _entrar(app)
    r = c.post("/ofertas/url", headers=h, json={"url": url})
    assert r.status_code == 422 and r.json()["detail"]
    assert _importaciones(motor_migrador) == []
    with motor_migrador.connect() as s:
        assert s.execute(text("select count(*) from tareas")).scalar_one() == 0


@pytest.mark.bd
def test_un_portal_vetado_pide_pegar_el_texto(app):
    c, h = _entrar(app)
    r = c.post("/ofertas/url", headers=h, json={"url": "https://es.linkedin.com/jobs/view/1"})
    assert "pega el texto" in r.json()["detail"].lower()


@pytest.mark.bd
def test_pasarse_del_limite_da_429(app):
    c, h = _entrar(app)
    codigos = [c.post("/ofertas/url", headers=h, json={"url": f"{URL}{i}"}).status_code for i in range(4)]
    assert codigos == [202, 202, 202, 429]
    otra, h2 = _entrar(app, "google-B")  # el límite es por usuaria
    assert otra.post("/ofertas/url", headers=h2, json={"url": URL}).status_code == 202


@pytest.mark.bd
def test_sin_sesion_o_sin_csrf_no_pasa(app):
    c = TestClient(app, follow_redirects=False)
    assert c.post("/ofertas/url", json={"url": URL}).status_code == 401
    c2, _ = _entrar(app)
    assert c2.post("/ofertas/url", json={"url": URL}).status_code == 403


@pytest.mark.bd
def test_la_importacion_es_solo_de_su_duena(app):
    ana, h = _entrar(app)
    berta, _ = _entrar(app, "google-B")
    importacion = ana.post("/ofertas/url", headers=h, json={"url": URL}).json()["id"]
    assert ana.get(f"/ofertas/url/{importacion}").status_code == 200
    assert berta.get(f"/ofertas/url/{importacion}").status_code == 404
