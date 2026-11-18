"""Fase 5 · prueba manual (18-nov): un perfil corto no bloquea «Regenerar» del CV base.

Antes, `validar_cv` exigía 250 palabras aunque el maestro tuviera ~100: el generador no puede inventar
y la regeneración se agotaba en 3 reintentos. Ahora el mínimo baja al 60 % de un maestro corto."""
import pytest

from horma.flows.generar_cv_base import crear as crear_generar
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.perfil import Perfil

pytestmark = pytest.mark.usefixtures("limites_reales")

TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior", "stack": []}
PUESTO = "Camarera en Bar Sol, 2020-2023"
RELLENO = " ".join(["atendiendo mesas y cobrando en sala"] * 15)  # 90 palabras
CONDENSADO = " ".join(["atendiendo mesas y cobrando en sala"] * 11)  # ~66: el modelo condensa un poco
MAESTRO = f"# Ana Pérez\n\n## Experiencia\n{PUESTO}\n{RELLENO}\n"  # ~100 palabras
APROBADO = {"veredicto_cv": "aprobado", "veredicto_carta": "aprobado", "problemas": []}


def _borrador(*lineas):
    cuerpo = ["## Experiencia", *lineas]
    return {"contenido": "\n".join(cuerpo), "traza": [{"frase": x, "fragmento": x} for x in cuerpo[1:]]}


def _estado():
    perfil = Perfil.model_validate({"taxonomia": TAX, "experiencias": [{
        "puesto": "Camarera", "empresa": "Bar Sol",
        "origen": {"fuente": "cv", "cv_id": 1, "fragmento": PUESTO}}]})
    return {"perfil": perfil.model_dump(mode="json"), "cv_maestro": MAESTRO}


def test_un_cv_base_fiel_a_un_perfil_corto_se_guarda():
    prov = ProveedorSimulado([_borrador(PUESTO, RELLENO), APROBADO])
    r = crear_generar(proveedor=prov).run(_estado())["cv_base"]
    assert len(r["guardados"]) == 1 and r["rechazados"] == []
    assert len(prov.llamadas) == 2  # generador y juez


def test_un_cv_base_algo_condensado_de_un_perfil_corto_tambien_se_guarda():
    prov = ProveedorSimulado([_borrador(PUESTO, CONDENSADO), APROBADO])  # 78 palabras (prueba manual)
    r = crear_generar(proveedor=prov).run(_estado())["cv_base"]
    assert len(r["guardados"]) == 1 and r["rechazados"] == []


def test_un_cv_base_que_recorta_demasiado_el_perfil_corto_sigue_rechazado():
    recortado = _borrador(PUESTO, " ".join(["atendiendo mesas y cobrando en sala"] * 5))  # ~36 palabras
    prov = ProveedorSimulado([recortado, recortado])
    r = crear_generar(proveedor=prov).run(_estado())["cv_base"]
    assert r["guardados"] == [] and len(r["rechazados"]) == 1
    assert any("demasiado corto" in x for x in r["rechazados"][0]["errores"])
