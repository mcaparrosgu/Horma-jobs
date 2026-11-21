"""Simplificación S4 · T16: GET /api/perfil/cv.pdf (RF-10.4, RF-10.4b)."""
import io

import pytest
from pypdf import PdfReader

from horma.schemas.perfil import Perfil
from horma.web.db import sesion_de
from horma.web.repositories import perfiles
from tests.test_f9a_d_api import ORIG, app, entrar, uid  # noqa: F401

pytestmark = pytest.mark.bd

MAESTRO = "# Ana Pérez\n\n## Experiencia\n\n- Camarera en Hotel Mar (2018-2019)\n"


def con_perfil(motor_app, u):
    with sesion_de(motor_app, u) as s:
        pid, version = perfiles.nueva_version(s, u)
        perfiles.guardar_perfil(s, u, pid, Perfil.model_validate({
            "version": version, "nombre": "Ana Pérez",
            "experiencias": [{"puesto": "Camarera", "empresa": "Hotel Mar", "inicio": "2018-01",
                              "fin": "2019-02", "descripcion": "x", "origen": ORIG}]}), MAESTRO)


def test_da_pdf_con_nombre_y_experiencia(app, motor_app, motor_migrador):  # noqa: F811
    c, _ = entrar(app)
    con_perfil(motor_app, uid(motor_migrador))
    r = c.get("/api/perfil/cv.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    texto = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "Ana Pérez" in texto and "Camarera en Hotel Mar" in texto


def test_sin_perfil_404(app):  # noqa: F811
    c, _ = entrar(app)
    assert c.get("/api/perfil/cv.pdf").status_code == 404


def test_otra_usuaria_no_ve_el_de_la_primera(app, motor_app, motor_migrador):  # noqa: F811
    entrar(app, "google-A")
    con_perfil(motor_app, uid(motor_migrador))
    b, _ = entrar(app, "google-B")
    assert b.get("/api/perfil/cv.pdf").status_code == 404
