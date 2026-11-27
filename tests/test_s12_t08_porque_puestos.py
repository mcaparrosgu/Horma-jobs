"""Spec 012, T08 (RF-12.6, 12.6c, 12.7): «Qué buscas» dice el nivel y el porqué de cada puesto sugerido."""
from pathlib import Path

import pytest

from horma.schemas.preferencias import PuestoSugerido
from horma.tools.puestos_del_perfil import porque
from horma.web.db import sesion_de
from horma.web.main import crear_app
from horma.web.repositories import perfiles
from tests.test_f2_t15_t19_api import IdentidadFalsa, archivos, entrar  # noqa: F401
from tests.test_f9a_d_api import uid


def _p(tipo, dato, nivel=2, marcado=False):
    return PuestoSugerido(titulo="X", dato=dato, nivel=nivel, tipo_dato=tipo, marcado=marcado)


@pytest.mark.parametrize("puesto, esperado", [
    (_p("puesto", "Camarera", nivel=1, marcado=True), "Lo has sido: Camarera"),
    (_p("puesto", "Camarera"), "Parecido a tu puesto: Camarera"),
    (_p("certificacion", "PL-300"), "Por tu certificación: PL-300"),
    (_p("titulacion", "Grado en Estadística"), "Por tu grado en Estadística"),
    (_p("titulacion", "Máster en Marketing Digital"), "Por tu máster en Marketing Digital"),
    (_p("titulacion", "Grado Superior en Administración y Finanzas"),
     "Por tu grado superior en Administración y Finanzas"),
    (_p("titulacion", "Graduado en ESO"), "Por tu titulación: Graduado en ESO"),
    (_p("titulacion", "BSc in Computer Science"), "Por tu titulación: BSc in Computer Science"),
    (_p("titulacion", "Grado en Estadística", marcado=True), "Para empezar, por tu grado en Estadística"),
    (_p("titulacion", "Técnico en Servicios de Restauración", marcado=True),
     "Para empezar, por tu titulación: Técnico en Servicios de Restauración"),
    (_p(None, "Analista"), "Por tu perfil: Analista"),  # guardados antes de la spec 012
])
def test_el_porque_dice_de_donde_sale(puesto, esperado):
    assert porque(puesto) == esperado


@pytest.mark.bd
def test_opciones_trae_nivel_porque_y_solo_el_nivel_1_marcado(motor_app, motor_migrador, bd_limpia,
                                                              archivos):  # noqa: F811
    c, _, _ = entrar(crear_app(engine=motor_app, identidad=IdentidadFalsa()))
    with sesion_de(motor_app, uid(motor_migrador)) as s:
        suyo = _p("puesto", "Camarera", nivel=1, marcado=True).model_copy(update={"titulo": "Camarera"})
        afin = _p("titulacion", "Grado en Estadística").model_copy(update={"titulo": "Estadística"})
        perfiles.aplicar_puestos_del_cv(s, uid(motor_migrador), [suyo.model_dump(), afin.model_dump()])
    puestos = c.get("/api/preferencias/opciones").json()["puestos"]
    assert [(p["valor"], p["nivel"], p["marcado"], p["porque"]) for p in puestos] == [
        ("Camarera", 1, True, "Lo has sido: Camarera"),
        ("Estadística", 2, False, "Por tu grado en Estadística")]


def test_la_pantalla_pinta_el_porque_de_la_api():
    js = Path("horma/web/static/ofertas.js").read_text(encoding="utf-8")
    assert "p.porque" in js and "p.tambien" in js and "Por tu perfil" not in js


def test_dos_puestos_con_porque_no_se_quedan_pegados():
    css = Path("horma/web/static/estilo.css").read_text(encoding="utf-8")
    assert ".casilla-puesto{ padding-block: 6px; }" in css
