"""M19 a 390 px: el móvil no pinta un PDF dentro de la página; el visor enseña cada página como imagen."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_f2_t02_convertir_cv import _pdf
from tests.test_f2_t15_t19_api import (  # noqa: F401 - fixtures
    _propietario,
    app,
    archivos,
    entrar,
    subir,
)

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"


@pytest.mark.bd
def test_las_paginas_de_un_pdf_salen_como_imagen_solo_a_su_duena(app):  # noqa: F811
    a, ha, _ = entrar(app, "google-A")
    b, _, _ = entrar(app, "google-B")
    pdf = _pdf("Ana Perez camarera en Bar Sol")
    cv_id = subir(a, ha, contenido=pdf, nombre_archivo="cv.pdf").json()["id"]
    assert a.get(f"/api/cv/{cv_id}/paginas").json() == {"paginas": 1}
    img = a.get(f"/api/cv/{cv_id}/paginas/1")
    assert img.status_code == 200 and img.content.startswith(b"\x89PNG")
    assert img.headers["cache-control"] == "private, no-store"
    assert a.get(f"/api/cv/{cv_id}/paginas/2").status_code == 404
    assert a.get(f"/api/cv/{cv_id}/paginas/0").status_code == 404
    assert b.get(f"/api/cv/{cv_id}/paginas").status_code == 404
    assert b.get(f"/api/cv/{cv_id}/paginas/1").status_code == 404
    assert TestClient(app).get(f"/api/cv/{cv_id}/paginas/1").status_code == 401


@pytest.mark.bd
def test_un_documento_que_no_es_pdf_no_tiene_paginas(app):  # noqa: F811
    a, ha, _ = entrar(app, "google-A")
    cv_id = subir(a, ha).json()["id"]
    assert a.get(f"/api/cv/{cv_id}/paginas").status_code == 404


def test_el_visor_usa_imagenes_en_movil():
    js = (ESTATICOS / "perfil.js").read_text(encoding="utf-8")
    assert 'matchMedia("(max-width: 900px)")' in js
    assert "/paginas/${n}" in js
