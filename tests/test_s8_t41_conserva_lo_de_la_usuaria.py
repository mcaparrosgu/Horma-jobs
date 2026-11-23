"""S8, T41: `perfilar` conserva lo que escribió la usuaria (RF-10.14, base de T42)."""
import pytest
from sqlalchemy import text

from horma.flows.perfilar import crear as crear_perfilar
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.perfil import Perfil
from horma.web.db import sesion_de
from horma.web.repositories import perfiles

pytestmark = pytest.mark.usefixtures("juez_automatico")

TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior", "stack": []}
CV2 = "Irene Navarro\nJefa de sala en Hotel Mar, 2019-2023\nExcel básico"
USUARIA = {"fuente": "usuaria", "fragmento": "lo escribí yo"}


def _correr(de_usuaria, perfil_cv):
    flujo = crear_perfilar(proveedor=ProveedorSimulado([{"perfil": perfil_cv}, TAX]))
    return Perfil.model_validate(flujo.run(
        {"cvs": [{"cv_id": 2, "nombre": "B", "texto": CV2}], "de_usuaria": de_usuaria})["perfil"])


def test_un_cv_nuevo_no_borra_lo_que_escribio_ella():
    de_usuaria = {"experiencias": [{"puesto": "Camarera", "empresa": "Bar Sol", "origen": USUARIA}],
                  "habilidades": [{"nombre": "Catas de vino", "origen": USUARIA}],
                  "resumen": {"valor": "Resumen mío", "origen": USUARIA}}
    p = _correr(de_usuaria, {
        "experiencias": [{"puesto": "Jefa de sala", "empresa": "Hotel Mar",
                          "origen": {"fuente": "cv", "cv_id": 2,
                                     "fragmento": "Jefa de sala en Hotel Mar, 2019-2023"}}],
        "habilidades": [{"nombre": "Excel básico",
                         "origen": {"fuente": "cv", "cv_id": 2, "fragmento": "Excel básico"}}]})
    assert {x.puesto for x in p.experiencias} == {"Camarera", "Jefa de sala"}
    assert {h.nombre for h in p.habilidades} == {"Catas de vino", "Excel básico"}
    assert p.resumen.valor == "Resumen mío" and p.resumen.origen.fuente == "usuaria"


def test_lo_suyo_manda_sobre_lo_que_dice_el_cv_de_lo_mismo():
    de_usuaria = {"experiencias": [{"puesto": "Jefa de sala", "empresa": "Hotel Mar",
                                    "descripcion": "Corregida por mí", "origen": USUARIA}]}
    p = _correr(de_usuaria, {"experiencias": [
        {"puesto": "Jefa de sala", "empresa": "Hotel Mar", "descripcion": "Del CV",
         "origen": {"fuente": "cv", "cv_id": 2, "fragmento": "Jefa de sala en Hotel Mar, 2019-2023"}}]})
    assert [x.descripcion for x in p.experiencias] == ["Corregida por mí"]


def test_el_nombre_que_edito_ella_manda_sobre_el_del_cv():   # T61 (N4, P11)
    p = _correr({"nombre": "Irene Navarro", "genero_puestos": "femenino"},
                {"nombre": "Irene Navarro Soler", "experiencias": []})
    assert p.nombre == "Irene Navarro" and p.genero_puestos == "femenino"


def test_sin_nombre_suyo_se_usa_el_del_cv():
    perfil = _correr({"habilidades": []}, {"nombre": "Irene Navarro Soler", "experiencias": []})
    assert perfil.nombre == "Irene Navarro Soler"


def test_sin_nada_suyo_el_flujo_es_el_de_siempre():
    p = _correr(None, {"experiencias": []})
    assert p.experiencias == []


def test_lo_de_la_usuaria_sale_del_perfil_vigente(motor_app, motor_migrador, bd_limpia):
    with motor_migrador.begin() as c:
        u = c.execute(text("insert into usuarias (google_sub) values ('s8') returning id")).scalar_one()
    perfil = Perfil.model_validate({
        "nombre": "Irene", "experiencias": [
            {"puesto": "Camarera", "origen": {"fuente": "usuaria", "fragmento": "Camarera"}},
            {"puesto": "Jefa de sala", "origen": {"fuente": "cv", "cv_id": 1, "fragmento": "Jefa de sala"}}],
        "habilidades": [{"nombre": "TPV", "origen": {"fuente": "usuaria", "fragmento": "TPV"}}]})
    with sesion_de(motor_app, u) as s:
        pid, _ = perfiles.nueva_version(s, u)
        perfiles.guardar_perfil(s, u, pid, perfil, "# Irene")
        suyo = perfiles.lo_de_la_usuaria(s, u)
    assert [x["puesto"] for x in suyo["experiencias"]] == ["Camarera"]
    assert [x["nombre"] for x in suyo["habilidades"]] == ["TPV"] and suyo["nombre"] == "Irene"
