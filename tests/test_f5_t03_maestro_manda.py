"""Fase 5 · T03: el maestro lo compone siempre el código a partir del perfil (RF-5.1, RF-5.1b)."""
# ruff: noqa: F401, F811  (fixtures importadas de otro módulo)
import pytest
from test_f2_t08_t10_flujos import CV1, TAX, _extraccion, _o, _perfilar
from test_f2_t15_t19_api import (
    _perfil_hecho,
    _propietario,
    _usuaria_id,
    app,
    archivos,
    entrar,
)

from horma.agents.extractor_perfil.schemas import SalidaExtractorPerfil
from horma.schemas.perfil import Perfil
from horma.tools.componer_cv_maestro import componer_cv_maestro
from horma.tools.verificar_trazabilidad import verificar_trazabilidad
from horma.web.db import sesion_de
from horma.web.repositories import perfiles

BAR = {"puesto": "Camarera", "empresa": "Bar Sol", "inicio": "2020", "fin": "2023",
       "origen": _o(1, "Camarera en Bar Sol, 2020-2023")}


# --- el flujo `perfilar` (sin base de datos) -------------------------------------------------------
def test_perfilar_compone_el_maestro_con_codigo_aunque_el_extractor_no_lo_escriba():
    ext = {"perfil": {"experiencias": [BAR]}}  # sin `cv_maestro`: el extractor ya no lo escribe
    _, e = _perfilar(ext)
    assert e["cv_maestro"] == componer_cv_maestro(Perfil.model_validate(e["perfil"]))
    assert "Camarera · Bar Sol · 2020-2023" in e["cv_maestro"]


def test_perfilar_ignora_un_maestro_que_el_modelo_aun_escriba():
    ext = {"perfil": {"experiencias": [BAR]}, "cv_maestro": "# Inventado\nDirectora en el Ritz"}
    _, e = _perfilar(ext)
    assert "Ritz" not in e["cv_maestro"] and "Camarera" in e["cv_maestro"]


def test_la_salida_del_extractor_ya_no_pide_maestro():
    assert "cv_maestro" not in SalidaExtractorPerfil.model_fields
    assert CV1 and TAX and _extraccion  # (los datos de ejemplo siguen importables)


# --- editar en la API ------------------------------------------------------------------------------
pytestmark_bd = pytest.mark.bd


def _maestro_vigente(motor, usuaria) -> str:
    with sesion_de(motor, usuaria) as s:
        return perfiles.vigente(s)["cv_maestro"]


@pytest.mark.bd
def test_editar_una_experiencia_cambia_el_maestro_de_la_version_nueva(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    assert "Camarera de sala" not in _maestro_vigente(motor_app, u)
    r = c.patch("/api/perfil/datos", headers=h, json={
        "campo": "experiencias", "indice": 0,
        "dato": {"puesto": "Camarera de sala", "empresa": "Bar Sol", "inicio": "2020", "fin": "2023"}})
    assert r.status_code == 201
    maestro = _maestro_vigente(motor_app, u)
    assert "Camarera de sala · Bar Sol · 2020-2023" in maestro
    assert "Camarera en Bar Sol, 2020-2023" not in maestro  # el texto viejo no se arrastra


@pytest.mark.bd
def test_un_cv_adaptado_con_el_dato_editado_no_da_errores_de_trazabilidad(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    c.patch("/api/perfil/datos", headers=h, json={
        "campo": "experiencias", "indice": 0,
        "dato": {"puesto": "Camarera de sala", "empresa": "Bar Sol", "inicio": "2020", "fin": "2023"}})
    maestro = _maestro_vigente(motor_app, u)
    contenido = "## Experiencia\nCamarera de sala · Bar Sol · 2020-2023"
    traza = [{"frase": "Camarera de sala · Bar Sol · 2020-2023",
              "fragmento": "Camarera de sala · Bar Sol · 2020-2023"}]
    assert verificar_trazabilidad(contenido, traza, maestro) == []


@pytest.mark.bd
def test_lo_borrado_no_aparece_en_el_maestro(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    r = c.patch("/api/perfil/datos", headers=h, json={"campo": "experiencias", "indice": 0, "dato": None})
    assert r.status_code == 201
    maestro = _maestro_vigente(motor_app, u)
    assert "Bar Sol" not in maestro and "Camarera" not in maestro
