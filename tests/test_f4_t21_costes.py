"""Fase 4 · T21: `/costes` (RF-4.7): solo admins, totales correctos y sin datos personales."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_f1_t10_t15_api_ingesta import ADMIN, IdentidadFalsa, entrar
from test_f3_t12_t13_bd_worker import _usuarias

from horma import config
from horma.web.db import sesion_de, sesion_sistema
from horma.web.main import crear_app

pytestmark = pytest.mark.bd

STATIC = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
PROHIBIDAS = {"usuaria_id", "tarea_id", "id"}


@pytest.fixture
def ajustes_prueba(monkeypatch):
    monkeypatch.setenv("HORMA_ADMINS", ADMIN)
    config.ajustes.cache_clear()
    yield
    config.ajustes.cache_clear()


@pytest.fixture
def cliente(motor_app, bd_limpia, ajustes_prueba):
    with TestClient(crear_app(engine=motor_app, identidad=IdentidadFalsa()), follow_redirects=False) as c:
        yield c


def _llamada(s, agente, modelo, coste, resultado="ok", *, hace="0 days", tarea=None):
    s.execute(text(
        "insert into llm_llamadas (tarea_id, agente, modelo, tokens_entrada, tokens_salida, coste, "
        "latencia_ms, resultado, creada_en) values (:t, :a, :m, 100, 50, :c, 200, :r, "
        "now() - cast(:h as interval))"), {"t": tarea, "a": agente, "m": modelo, "c": coste, "r": resultado,
                                           "h": hace})


def _sembrar(motor):
    with sesion_sistema(motor) as s:
        _llamada(s, "perfilador", "pequeno", 0.10)
        _llamada(s, "perfilador", "pequeno", 0.20, "salida_invalida")
        _llamada(s, "adaptador", "mayor", 0.50)
        _llamada(s, "adaptador", "mayor", 0.30, "error", hace="1 days 3 hours")
        _llamada(s, "adaptador", "mayor", 9.00, hace="45 days")  # fuera de la ventana de 30 días
    a, b = _usuarias(motor)
    for u, tipo, estado in ((a, 'candidatura', 'error'), (b, 'candidatura', 'error'),
                            (a, 'perfilar', 'error'), (a, 'perfilar', 'hecha')):
        with sesion_de(motor, u) as s:
            s.execute(text("insert into tareas (usuaria_id, tipo, entidad_id, estado, tope_coste, "
                           "motivo_error) values (:u, :t, 1, :e, 1, 'x')"), {"u": u, "t": tipo, "e": estado})


def test_sin_sesion_401_y_sin_ser_admin_403(cliente):
    assert cliente.get("/api/costes").status_code == 401 and cliente.get("/costes").status_code == 401
    entrar(cliente, "google-normal")
    assert cliente.get("/api/costes").status_code == 403 and cliente.get("/costes").status_code == 403


def test_la_pagina_la_ve_un_admin(cliente):
    entrar(cliente)
    r = cliente.get("/costes")
    assert r.status_code == 200 and '<script src="/static/costes.js"' in r.text


def test_totales_por_dia_agente_modelo_y_tasa_de_errores(cliente, motor_app):
    _sembrar(motor_app)
    entrar(cliente)
    r = cliente.get("/api/costes").json()
    agentes = {a["agente"]: a for a in r["agentes"]}
    assert agentes["perfilador"]["llamadas"] == 2 and agentes["perfilador"]["coste"] == pytest.approx(0.30)
    assert agentes["perfilador"]["tasa_errores"] == pytest.approx(0.5)
    assert agentes["adaptador"]["llamadas"] == 2 and agentes["adaptador"]["coste"] == pytest.approx(0.80)
    assert agentes["adaptador"]["tasa_errores"] == pytest.approx(0.5)
    assert agentes["adaptador"]["latencia_media_ms"] == 200
    modelos = {m["modelo"]: m for m in r["modelos"]}
    assert modelos["pequeno"]["coste"] == pytest.approx(0.30) and modelos["mayor"]["llamadas"] == 2
    assert sum(d["coste"] for d in r["dias"]) == pytest.approx(1.10)  # sin la llamada de hace 45 días
    assert sum(d["llamadas"] for d in r["dias"]) == 4 and len(r["dias"]) == 2
    assert r["dias"][0]["dia"] > r["dias"][1]["dia"]  # el más reciente primero
    assert {t["tipo"]: t["n"] for t in r["tareas_en_error"]} == {"candidatura": 2, "perfilar": 1}


def test_la_respuesta_no_lleva_ids_ni_texto(cliente, motor_app):
    _sembrar(motor_app)
    entrar(cliente)
    cuerpo = cliente.get("/api/costes").text
    for clave in ("usuaria_id", "tarea_id", "motivo_error", "texto"):
        assert clave not in cuerpo

    def claves(v):
        if isinstance(v, dict):
            for k, x in v.items():
                yield k
                yield from claves(x)
        elif isinstance(v, list):
            for x in v:
                yield from claves(x)

    assert not PROHIBIDAS & set(claves(cliente.get("/api/costes").json()))


def test_sin_datos_todo_vacio(cliente):
    entrar(cliente)
    r = cliente.get("/api/costes").json()
    assert r == {"dias": [], "agentes": [], "modelos": [], "tareas_en_error": [], "alertas": []}


def test_el_js_no_usa_innerhtml():
    js = (STATIC / "costes.js").read_text(encoding="utf-8")
    for prohibido in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(",
                      "new Function"):
        assert prohibido not in js


def test_en_el_movil_las_tablas_se_desplazan_dentro_de_su_caja():
    html = (STATIC / "costes.html").read_text(encoding="utf-8")
    css = (STATIC / "estilo.css").read_text(encoding="utf-8")
    assert len(re.findall(r'<div class="tabla-costes"[^>]*><table', html)) == 3  # ninguna tabla suelta
    regla = re.search(r"\.tabla-costes\s*\{([^}]*)\}", css).group(1)
    assert "overflow-x: auto" in regla and "max-width: 100%" in regla
    assert 'name="viewport"' in html
