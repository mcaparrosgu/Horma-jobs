"""Simplificación S2 · T11: la pantalla y los endpoints del CV base desaparecen (RF-10.3e)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from horma.web.db import sesion_sistema
from tests.test_f3_t14_t17_api import app, archivos, entrar  # noqa: F401

pytestmark = pytest.mark.bd

STATIC = Path(__file__).parent.parent / "horma" / "web" / "static"


def test_cv_base_redirige_a_perfil(app):  # noqa: F811
    r = TestClient(app, follow_redirects=False).get("/cv-base")
    assert r.status_code == 308 and r.headers["location"] == "/perfil"


def test_los_endpoints_del_cv_base_ya_no_existen(app):  # noqa: F811
    c, h, _ = entrar(app)
    assert c.get("/api/cv-base").status_code in (404, 405)
    assert c.post("/api/cv-base", headers=h).status_code in (404, 405)
    assert c.patch("/api/cv-base/1", headers=h, json={"nombre": "x"}).status_code in (404, 405)
    assert c.post("/api/cv-base/1/regenerar", headers=h).status_code in (404, 405)
    assert c.put("/api/cv-base/1/visibilidad", headers=h, json={"visibilidad": {}}).status_code in (404, 405)
    assert c.get("/api/cv-base/1/versiones").status_code in (404, 405)
    assert c.delete("/api/cv-base/1", headers=h).status_code in (404, 405)


def test_la_pantalla_del_cv_base_se_ha_borrado():
    assert not (STATIC / "cv-base.html").exists() and not (STATIC / "cv-base.js").exists()


def test_las_tablas_del_cv_base_siguen(app, motor_app):  # noqa: F811
    with sesion_sistema(motor_app) as s:
        for t in ("cv_base", "cv_base_versiones"):
            assert s.execute(text("select to_regclass(:t)"), {"t": t}).scalar() is not None
