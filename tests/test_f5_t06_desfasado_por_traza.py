"""Fase 5 · T06: un CV base solo está desfasado si su traza usa un dato que cambió (RF-5.1e)."""
# ruff: noqa: F401, F811  (fixtures importadas de otro módulo)
import pytest
from test_f2_t15_t19_api import _perfil_hecho, _propietario, _usuaria_id, app, archivos, entrar

from horma.tools.cv_base_afectado import cv_base_afectado, lineas_cambiadas
from horma.web.db import sesion_de
from horma.web.repositories import perfiles

MAESTRO = ("## Experiencia\n- Camarera · Bar Sol · 2020-2023\n- Peón · Obras Norte · 2018-2019\n"
           "## Formación\n- Graduado escolar · IES Sur · 2016\n")
_BAR, _OBRA = "Camarera · Bar Sol · 2020-2023", "Peón · Obras Norte · 2018-2019"
TRAZA_HOSTELERIA = [{"frase": _BAR, "fragmento": _BAR}]
TRAZA_CONSTRUCCION = [{"frase": _OBRA, "fragmento": _OBRA}]


def test_editar_la_experiencia_de_hosteleria_marca_solo_el_cv_que_la_cita():
    nuevo = MAESTRO.replace("Camarera · Bar Sol", "Camarera de sala · Bar Sol")
    assert cv_base_afectado(TRAZA_HOSTELERIA, nuevo) is True
    assert cv_base_afectado(TRAZA_CONSTRUCCION, nuevo) is False


def test_devuelve_las_lineas_que_cambiaron():
    nuevo = MAESTRO.replace("Camarera · Bar Sol", "Camarera de sala · Bar Sol")
    assert lineas_cambiadas(TRAZA_HOSTELERIA + TRAZA_CONSTRUCCION, nuevo) == [
        "Camarera · Bar Sol · 2020-2023"]


def test_un_dato_quitado_tambien_marca_y_un_cambio_de_formato_no():
    sin_bar = MAESTRO.replace("- Camarera · Bar Sol · 2020-2023\n", "")
    assert cv_base_afectado(TRAZA_HOSTELERIA, sin_bar) is True
    otro_formato = MAESTRO.replace("- Camarera · Bar Sol · 2020-2023", "- **camarera · bar sol · 2020-2023**")
    assert cv_base_afectado(TRAZA_HOSTELERIA, otro_formato) is False


def test_sin_traza_no_hay_nada_que_haya_cambiado():
    assert cv_base_afectado([], MAESTRO) is False


def _editar(c, h, puesto):
    r = c.patch("/api/perfil/datos", headers=h, json={
        "campo": "experiencias", "indice": 0,
        "dato": {"puesto": puesto, "empresa": "Bar Sol", "inicio": "2020", "fin": "2023"}})
    assert r.status_code == 201
