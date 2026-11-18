"""Fase 5 · T24: subir cartas de presentación y marcar «Lo escribí yo» (RF-5.6)."""
from pathlib import Path

import pytest
from sqlalchemy import text
from test_f2_t15_t19_api import _propietario, _tareas, admin, app, archivos, entrar, subir  # noqa: F401

from horma.web.db import sesion_de
from horma.web.repositories import perfiles

pytestmark = [pytest.mark.bd, pytest.mark.usefixtures("estilo_real")]

CARTA = "Hola equipo,\n\nMe interesa el puesto porque ya he llevado una sala de 40 mesas.\n".encode()


def _carta(c, h, **datos):
    return c.post("/api/cv", headers=h, files={"archivo": ("carta.md", CARTA)},
                  data={"clase": "carta", **datos})


def test_una_carta_se_sube_y_no_entra_en_perfilar(app, motor_app):  # noqa: F811
    c, h, _ = entrar(app)
    r = _carta(c, h, nombre="Carta hostelería")
    assert r.status_code == 201, r.text
    assert r.json()["clase"] == "carta" and r.json()["perfil_id"] is None
    assert _tareas(motor_app, "perfilar") == []
    with admin() as s:
        assert s.execute(text("select count(*) from perfiles")).scalar_one() == 0
        fila = s.execute(text("select clase, texto, escrito_por_ella from cv_archivos")).one()
    assert fila.clase == "carta" and "sala de 40 mesas" in fila.texto and fila.escrito_por_ella is False


def test_una_carta_no_llega_a_los_cvs_fuente_del_perfil(app, motor_app):  # noqa: F811
    c, h, _ = entrar(app)
    _carta(c, h, nombre="Carta")
    assert subir(c, h, nombre="Mi CV").status_code == 201
    with admin() as s:
        uid = s.execute(text("select id from usuarias")).scalar_one()
    with sesion_de(motor_app, uid) as s:
        textos = [f["texto"] for f in perfiles.cvs_fuente(s)]
    assert len(textos) == 1 and "sala de 40 mesas" not in textos[0]


def test_la_marca_lo_escribi_yo_se_guarda_al_subir_y_se_puede_cambiar(app):  # noqa: F811
    c, h, _ = entrar(app)
    cv = _carta(c, h, nombre="Carta", escrito_por_ella="true").json()
    lista = c.get("/api/cv").json()
    assert lista[0]["escrito_por_ella"] is True
    r = c.put(f"/api/cv/{cv['id']}/escrito-por-ella", headers=h, json={"escrito_por_ella": False})
    assert r.status_code == 200 and r.json() == {"id": cv["id"], "escrito_por_ella": False}
    assert c.get("/api/cv").json()[0]["escrito_por_ella"] is False
    # también se puede marcar un CV de clase «fuente»
    otro = subir(c, h, nombre="CV", escrito_por_ella="true").json()
    assert {x["id"]: x["escrito_por_ella"] for x in c.get("/api/cv").json()}[otro["id"]] is True


def test_cambiar_la_marca_pide_sesion_csrf_y_es_solo_de_su_duena(app):  # noqa: F811
    c, h, _ = entrar(app)
    cv = _carta(c, h, nombre="Carta").json()
    assert c.put(f"/api/cv/{cv['id']}/escrito-por-ella", json={"escrito_por_ella": True}).status_code == 403
    otra, h2, _ = entrar(app, "google-B")
    r = otra.put(f"/api/cv/{cv['id']}/escrito-por-ella", headers=h2, json={"escrito_por_ella": True})
    assert r.status_code == 404


def test_una_clase_desconocida_sigue_rechazada(app):  # noqa: F811
    c, h, _ = entrar(app)
    r = c.post("/api/cv", headers=h, files={"archivo": ("x.md", CARTA)}, data={"clase": "otra"})
    assert r.status_code == 422


def test_la_pantalla_ofrece_cartas_y_la_marca():
    html = Path("horma/web/static/perfil.html").read_text(encoding="utf-8")
    js = Path("horma/web/static/perfil.js").read_text(encoding="utf-8")
    assert 'value="carta"' in html and 'id="escrito-por-ella"' in html
    assert "escrito-por-ella" in js and "Lo escribí yo" in js
