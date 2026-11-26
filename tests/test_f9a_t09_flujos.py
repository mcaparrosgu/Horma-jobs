"""Fase 9a, T09: actividades, periodos cubiertos y puestos en los flujos (puerta simulada)."""
import pytest

from horma.flows.clasificar_perfil import crear as crear_clasificar
from horma.flows.perfilar import crear as crear_perfilar
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.perfil import Perfil

pytestmark = pytest.mark.usefixtures("juez_automatico")

TAX = {"sector": "tecnologia", "familia": "datos_ia", "nivel": "junior", "stack": ["excel"]}
CV = ("Ana Pérez\nAnalista de datos en Bar Sol, 2020-2023\nBaja por enfermedad, 2019-2020\n"
      "Voluntariado en Cruz Roja, 2018-2019\nHabilidades: Excel")


def _o(fragmento):
    return {"fuente": "cv", "cv_id": 1, "fragmento": fragmento}


def _perfilar(puestos, actividades):
    extraccion = {"perfil": {
        "experiencias": [{"puesto": "Analista de datos", "empresa": "Bar Sol", "inicio": "2020",
                          "fin": "2023", "origen": _o("Analista de datos en Bar Sol, 2020-2023")}],
        "habilidades": [{"nombre": "Excel", "origen": _o("Excel")}],
        "actividades": actividades}, "cv_maestro": ""}
    flujo = crear_perfilar(proveedor=ProveedorSimulado([extraccion, {**TAX, "puestos": puestos}]))
    return flujo.run({"cvs": [{"cv_id": 1, "nombre": "CV", "texto": CV}]})


ACTIVIDADES = [
    {"descripcion": "Baja por enfermedad", "inicio": "2019", "fin": "2020",
     "origen": _o("Baja por enfermedad, 2019-2020")},
    {"descripcion": "Voluntariado en Cruz Roja", "inicio": "2018", "fin": "2019",
     "origen": _o("Voluntariado en Cruz Roja, 2018-2019")}]


def test_una_baja_medica_pasa_a_periodo_cubierto_sin_texto_y_el_voluntariado_se_queda():
    e = _perfilar([], ACTIVIDADES)
    p = Perfil.model_validate(e["perfil"])
    assert [a.descripcion for a in p.actividades] == ["Voluntariado en Cruz Roja"]
    assert p.actividades[0].origen.fragmento == "Voluntariado en Cruz Roja, 2018-2019"
    assert [(x.inicio, x.fin) for x in p.periodos_cubiertos] == [("2019", "2020")]
    assert "enfermedad" not in str(e["perfil"]).lower() and "enfermedad" not in e["cv_maestro"].lower()
    assert "## Otras actividades\nVoluntariado en Cruz Roja · 2018-2019" in e["cv_maestro"]


def test_el_modelo_no_puede_crear_periodos_cubiertos():
    e = _perfilar([], [])
    assert e["perfil"]["periodos_cubiertos"] == []


def test_un_puesto_con_un_dato_que_no_esta_en_el_perfil_se_descarta():
    e = _perfilar([
        {"titulo": "Data Analyst", "idioma": "en", "dato": "Analista de datos"},
        {"titulo": "Científico de datos", "idioma": "es", "dato": "Doctorado en estadística"},
        {"titulo": "Analista de Excel", "idioma": "es", "dato": "excel"}], [])
    # El suyo va siempre (RF-12.6b); una habilidad no basta (RF-12.5).
    assert [p["titulo"] for p in e["puestos"]] == ["Analista de datos", "Data Analyst"]
    prefs = e["preferencias"]
    assert prefs["puestos"] == ["Analista de datos", "Data Analyst"]
    assert prefs["puestos_sugeridos"][1] == {"titulo": "Data Analyst", "dato": "Analista de datos",
                                             "nivel": 1, "tipo_dato": "puesto", "marcado": True}
    assert prefs["origen"]["puestos"] == "cv"
    assert "puestos" not in e["taxonomia"]


def test_clasificar_perfil_devuelve_puestos_respaldados():
    perfil = Perfil.model_validate({"experiencias": [{"puesto": "Camarera", "origen": {
        "fuente": "usuaria", "fragmento": "x"}}]})
    flujo = crear_clasificar(proveedor=ProveedorSimulado([{**TAX, "puestos": [
        {"titulo": "Camarera de sala", "idioma": "es", "dato": "Camarera"},
        {"titulo": "Chef", "idioma": "en", "dato": "Cocinero"}]}]))
    e = flujo.run({"perfil": perfil.model_dump(mode="json")})
    assert [p["titulo"] for p in e["puestos"]] == ["Camarero/a", "Camarero/a de sala"]


def test_un_cv_sin_experiencia_formacion_ni_idiomas_pregunta_por_cada_seccion():
    flujo = crear_perfilar(proveedor=ProveedorSimulado([{"perfil": {}, "cv_maestro": ""}, TAX]))
    e = flujo.run({"cvs": [{"cv_id": 1, "nombre": "CV", "texto": "Pablo\nBusco trabajo."}]})
    campos = [p["campo"] for p in e["perfil"]["preguntas_pendientes"]]
    assert campos == ["experiencias", "formacion", "idiomas"]
