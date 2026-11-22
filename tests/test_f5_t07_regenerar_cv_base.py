"""Fase 5 · T07: el flujo con destinos dados genera solo esos. Las tareas de generar y regenerar CV base
se aparcaron en S6 (RF-10.11d); el flujo se conserva."""
# ruff: noqa: F401, F811  (fixtures importadas de otro módulo)
import pytest
from sqlalchemy import text
from test_f2_t13_t14_bd_worker import BUENO, MALO, TAX, _encolar, _perfilar_hecho, _usuarias
from test_f2_t15_t19_api import _perfil_hecho, _propietario, _tareas, _usuaria_id, app, archivos, entrar

from horma.flows import generar_cv_base
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.perfil import Perfil
from horma.web.db import sesion_de
from horma.web.queue import worker
from horma.web.repositories import perfiles

pytestmark = pytest.mark.usefixtures("juez_automatico")


_BAR = "Camarera · Bar Sol · 2020-2023"
_LINEAS = ["## Idiomas", "Inglés B2", "## Experiencia", _BAR]  # mismo contenido que BUENO, otro orden
NUEVO = {"contenido": "\n".join(_LINEAS), "traza": BUENO["traza"]}


def test_el_flujo_con_destinos_dados_genera_solo_esos():
    perfil = Perfil.model_validate({"taxonomia": TAX})
    estado = {"perfil": perfil.model_dump(mode="json"), "cv_maestro": BUENO["contenido"],
              "preferencias": {"familias": ["ventas_comercial"]},
              "destinos": [{"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion"}]}
    prov = ProveedorSimulado([NUEVO])
    salida = generar_cv_base.crear(proveedor=prov).run(estado)
    assert [g["destino"]["familia"] for g in salida["cv_base"]["guardados"]] == ["hosteleria_restauracion"]
    assert len(prov.llamadas) == 1
