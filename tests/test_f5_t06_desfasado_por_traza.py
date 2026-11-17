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


@pytest.mark.bd
def test_la_api_marca_desfasado_solo_al_cv_afectado_y_dice_que_cambio(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    _editar(c, h, "Camarera de sala")  # desde aquí el maestro lo compone el código
    with sesion_de(motor_app, u) as s:
        vigente = perfiles.vigente(s)
        lineas = [x.lstrip("-# ").strip() for x in vigente["cv_maestro"].splitlines() if x.strip("-# ")]
        linea = next(x for x in lineas if "Camarera" in x)
        otra = next(x for x in lineas if "Camarera" not in x)
        perfiles.guardar_cv_base(s, u, vigente["version"], {"guardados": [
            {"destino": {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion"},
             "contenido": "x", "traza": [{"frase": linea, "fragmento": linea}], "intentos": 1},
            {"destino": {"sector": "construccion", "familia": "construccion_oficios"},
             "contenido": "y", "traza": [{"frase": otra, "fragmento": otra}], "intentos": 1},
        ], "rechazados": []})
    assert all(not x["desfasado"] for x in c.get("/api/cv-base").json()["cv_base"])
    _editar(c, h, "Jefa de sala")
    por_sector = {x["sector"]: x for x in c.get("/api/cv-base").json()["cv_base"]}
    assert por_sector["hosteleria_turismo"]["desfasado"] is True
    assert por_sector["hosteleria_turismo"]["cambios"] == [linea]
    assert por_sector["construccion"]["desfasado"] is False
    assert por_sector["construccion"]["cambios"] == []
