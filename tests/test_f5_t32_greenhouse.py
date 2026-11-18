"""Fase 5 · T32: Greenhouse empresa a empresa (RF-5.5c). Respuestas grabadas inventadas."""
import json

import httpx

from horma.ingesta import leer_fuente
from horma.tools import greenhouse, normalizar
from horma.tools.semilla import fuentes_semilla

LISTA = {"jobs": [{
    "id": 77, "title": "Camarera de sala", "updated_at": "2026-11-10T10:00:00-05:00",
    "absolute_url": "https://job-boards.greenhouse.io/acme/jobs/77",
    "location": {"name": "Madrid"}, "content": "&lt;p&gt;Sala y barra&lt;/p&gt;"}], "meta": {"total": 1}}


def _http(manejador):
    return httpx.Client(transport=httpx.MockTransport(manejador))


def test_el_mapeo_admite_un_texto_fijo_con_igual():
    t = normalizar.oferta_a_texto({"t": "X"}, {"titulo": "t", "empresa": "=Acme SL"}).texto
    assert "Empresa: Acme SL" in t


def test_la_fuente_de_una_empresa_lee_ofertas_con_enlace_al_original():
    f = greenhouse.fuente_de("acme", "Acme")
    assert f.nombre == "gh-acme" and f.activa is False and f.cada_horas >= 12
    assert f.atribucion and "Greenhouse" in f.atribucion
    visto = []

    def responder(r):
        visto.append(str(r.url))
        return httpx.Response(200, json=LISTA)

    [o] = leer_fuente(f, _http(responder), limite=5)
    assert visto == ["https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true"]
    assert o.url == "https://job-boards.greenhouse.io/acme/jobs/77" and o.id_externo == "77"
    assert "Empresa: Acme" in o.texto and "Camarera de sala" in o.texto
    assert "Sala y barra" in o.texto and "<p>" not in o.texto


def test_validar_token_da_el_nombre_o_none():
    def responder(r):
        if r.url.path.endswith("/acme"):
            return httpx.Response(200, json={"name": "Acme Corp", "content": ""})
        return httpx.Response(404, json={"status": 404})

    assert greenhouse.validar_token("acme", _http(responder)) == "Acme Corp"
    assert greenhouse.validar_token("nadie", _http(responder)) is None
    assert greenhouse.validar_token("con espacio", _http(responder)) is None  # ni se pide


def test_la_semilla_incluye_las_empresas_de_greenhouse_inactivas(tmp_path):
    ruta = tmp_path / "greenhouse.json"
    ruta.write_text(json.dumps({"empresas": [{"token": "acme", "nombre": "Acme"}]}), encoding="utf-8")
    assert [f.nombre for f in greenhouse.fuentes_de(ruta)] == ["gh-acme"]
    assert all(f.activa is False for f in fuentes_semilla())
