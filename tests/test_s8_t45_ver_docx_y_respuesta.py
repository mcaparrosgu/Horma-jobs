# ruff: noqa: F811
"""S8, T45: ver un DOCX y la respuesta que dice qué cambió (RF-10.14c, RF-10.14e)."""
import io

import pytest
from docx import Document

from horma.schemas.perfil import Perfil
from horma.web.db import sesion_de
from horma.web.repositories import perfiles
from horma.web.services import perfil as servicio_perfil
from tests.test_f2_t15_t19_api import app, archivos, entrar  # noqa: F401  (fixtures y ayudante)

pytestmark = pytest.mark.bd

AVISO = "Así se lee tu documento; el diseño original del Word no se puede mostrar aquí."


def _docx() -> bytes:
    d = Document()
    for p in ("Irene Navarro", "EXPERIENCIA", "Jefa de sala en Hotel Mar, 2019-2023"):
        d.add_paragraph(p)
    b = io.BytesIO()
    d.save(b)
    return b.getvalue()


def _subir(c, h, nombre="cv.docx"):
    return c.post("/api/cv", headers=h, files={"archivo": (nombre, _docx())}, data={"clase": "fuente"})


def test_ver_un_docx_da_su_texto_y_el_aviso_y_descargar_el_original(app):
    c, h, _ = entrar(app)
    cv_id = _subir(c, h).json()["id"]
    r = c.get(f"/api/cv/{cv_id}/texto")
    assert r.status_code == 200 and r.json()["aviso"] == AVISO
    assert "Jefa de sala en Hotel Mar, 2019-2023" in r.json()["texto"]
    d = c.get(f"/api/cv/{cv_id}/archivo")
    assert d.status_code == 200 and d.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert d.content[:2] == b"PK"   # el archivo original, sin tocar


def test_otra_usuaria_no_ve_el_texto_ni_descarga(app):
    c, h, _ = entrar(app)
    cv_id = _subir(c, h).json()["id"]
    otra, _, _ = entrar(app, "google-B")
    assert otra.get(f"/api/cv/{cv_id}/texto").status_code == 404
    assert otra.get(f"/api/cv/{cv_id}/archivo").status_code == 404
    assert otra.get("/api/cv/999/texto").status_code == 404


def test_guardar_una_respuesta_dice_que_campo_y_que_valor_cambian(motor_app, bd_limpia):
    from tests.test_f2_t13_t14_bd_worker import _usuarias
    u, _ = _usuarias(motor_app)
    perfil = Perfil.model_validate({"preguntas_pendientes": [
        {"campo": "habilidades", "motivo": "falta", "pregunta": "¿Qué nivel de Excel?"}]})
    with sesion_de(motor_app, u) as s:
        pid, _ = perfiles.nueva_version(s, u)
        perfiles.guardar_perfil(s, u, pid, perfil, "# x")
    r = servicio_perfil.responder(motor_app, u, 0, {"nombre": "Excel básico"})
    assert r["cambio"] == {"campo": "habilidades", "valor": "Excel básico"}
    perfil2 = servicio_perfil.ver(motor_app, u)["perfil"]
    assert [h["nombre"] for h in perfil2["habilidades"]] == ["Excel básico"]


def test_dar_una_pregunta_por_vista_no_inventa_un_cambio(motor_app, bd_limpia):
    from tests.test_f2_t13_t14_bd_worker import _usuarias
    u, _ = _usuarias(motor_app)
    perfil = Perfil.model_validate({"preguntas_pendientes": [
        {"campo": "habilidades", "motivo": "falta", "pregunta": "¿Algo más?"}]})
    with sesion_de(motor_app, u) as s:
        pid, _ = perfiles.nueva_version(s, u)
        perfiles.guardar_perfil(s, u, pid, perfil, "# x")
    assert "cambio" not in servicio_perfil.responder(motor_app, u, 0, None)
