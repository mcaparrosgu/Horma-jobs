"""Fase 5 · T09: un borrador de una versión anterior del perfil avisa y se puede rehacer (RF-5.1f)."""
# ruff: noqa: F401, F811  (fixtures importadas de otro módulo)
import pytest
from sqlalchemy import text
from test_f3_t14_t17_api import _candidatura, _escenario, _fila, _oferta, _perfil, app, archivos, entrar

from horma.web.db import sesion_de
from horma.web.queue import worker

pytestmark = pytest.mark.bd


def _tareas_de(motor, u, cid):
    with sesion_de(motor, u) as s:
        return s.execute(text("select tipo, tope_coste from tareas where entidad_id = :i "
                              "and tipo = 'candidatura'"), {"i": cid}).all()


def test_el_borrador_con_el_perfil_vigente_no_sale_desfasado(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    assert c.get(f"/api/candidaturas/{cid}").json()["desfasada"] is False


def test_tras_editar_el_perfil_el_borrador_sale_desfasado(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    _perfil(motor_app, u, version=2)
    assert c.get(f"/api/candidaturas/{cid}").json()["desfasada"] is True


def test_solo_los_borradores_avisan(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    assert c.post(f"/api/candidaturas/{cid}/aprobar", headers=h).status_code == 200
    _perfil(motor_app, u, version=2)
    assert c.get(f"/api/candidaturas/{cid}").json()["desfasada"] is False


def test_rehacer_un_borrador_desfasado_encola_la_misma_candidatura_con_el_tope_de_siempre(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    _perfil(motor_app, u, version=2)
    r = c.post(f"/api/candidaturas/{cid}/reintentar", headers=h)
    assert r.status_code == 202 and r.json()["id"] == cid
    assert _fila(motor_app, u, cid)["preparacion"] == "en_curso"
    assert [(t.tipo, float(t.tope_coste)) for t in _tareas_de(motor_app, u, cid)] == [("candidatura", 1.0)]
    assert c.post(f"/api/candidaturas/{cid}/reintentar", headers=h).status_code == 409  # ya en curso


def test_rehacer_prepara_con_la_version_vigente_del_perfil(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    _perfil(motor_app, u, version=2)
    c.post(f"/api/candidaturas/{cid}/reintentar", headers=h)
    with sesion_de(motor_app, u) as s:
        entrada = worker._Candidatura().cargar(s, {"entidad_id": cid, "usuaria_id": u})
    assert entrada["perfil_version"] == 2


def test_un_borrador_al_dia_o_una_candidatura_aprobada_no_se_rehace(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    assert c.post(f"/api/candidaturas/{cid}/reintentar", headers=h).status_code == 409  # al día
    c.post(f"/api/candidaturas/{cid}/aprobar", headers=h)
    _perfil(motor_app, u, version=2)
    assert c.post(f"/api/candidaturas/{cid}/reintentar", headers=h).status_code == 409  # ya aprobada


def test_se_puede_aprobar_un_borrador_desfasado_sin_rehacerlo(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    _perfil(motor_app, u, version=2)
    assert c.post(f"/api/candidaturas/{cid}/aprobar", headers=h).status_code == 200
    assert _fila(motor_app, u, cid)["estado"] == "aprobada"


def test_la_pantalla_avisa_y_ofrece_volver_a_preparar():
    from pathlib import Path
    ruta = Path(__file__).resolve().parent.parent / "horma" / "web" / "static" / "candidatura.js"
    js = ruta.read_text("utf-8")
    assert "Preparada con una versión anterior de tu perfil" in js and "Volver a preparar" in js
    assert "desfasada" in js
