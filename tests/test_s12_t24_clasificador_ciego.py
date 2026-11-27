"""Spec 012, T24 (RF-12.30f a 12.30h): el clasificador lee la copia ciega y lo que se ve sale en su género."""
import pytest

from horma.flows.clasificar_perfil import crear
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias, PuestoSugerido
from horma.tools.huella_perfil import huella_clasificacion
from horma.tools.puestos_del_perfil import en_su_genero
from horma.web.db import sesion_de
from horma.web.repositories import perfiles
from tests.test_s5_t21_cache import app, entrar, perfil_hecho, tareas, usuaria  # noqa: F401

TAX = {"sector": "otros", "familia": "hosteleria_restauracion", "nivel": "junior", "stack": []}
ORIGEN = {"fuente": "usuaria", "fragmento": "x"}


def _perfil(genero=None, nombre="Lucía Ferrer", **extra) -> Perfil:
    return Perfil.model_validate({
        "nombre": nombre, "genero_puestos": genero,
        "titular": {"valor": "Camarera", "origen": ORIGEN},
        "experiencias": [{"puesto": "Camarera", "empresa": "Bar Sol",
                          "descripcion": "camarera de terraza", "origen": ORIGEN}], **extra})


def _clasificar(perfil: Perfil, titulo="Camarero/a de sala", dato="Camarero/a"):
    prov = ProveedorSimulado([{**TAX, "puestos": [
        {"titulo": titulo, "idioma": "es", "dato": dato, "relacion": "mismo"}]}])
    e = crear(proveedor=prov).run({"perfil": perfil.model_dump(mode="json")})
    return [p for p in e["puestos"] if p["titulo"] not in ("Camarera", "Camarero", "Camarero/a")], \
        prov.llamadas[0]["usuario"]


def test_el_modelo_no_recibe_el_nombre_ni_el_genero():
    _, enviado = _clasificar(_perfil("femenino"))
    for fuera in ("Lucía", "Ferrer", "Camarera", "camarera", "femenino"):
        assert fuera not in enviado
    assert "Camarero/a" in enviado


@pytest.mark.parametrize("genero, titulo", [("femenino", "Camarera de sala"),
                                            ("masculino", "Camarero de sala"),
                                            (None, "Camarero/a de sala")])
def test_el_titulo_sale_en_su_genero_y_el_dato_es_el_del_perfil(genero, titulo):
    puestos, _ = _clasificar(_perfil(genero))
    assert [(p["titulo"], p["dato"], p["nivel"]) for p in puestos] == [(titulo, "Camarera", 1)]


def test_un_titulo_que_el_modelo_devuelve_en_un_genero_pasa_al_de_ella():
    puestos, _ = _clasificar(_perfil("masculino"), titulo="Camarera de sala", dato="Camarera")
    assert puestos[0]["titulo"] == "Camarero de sala"


def test_su_puesto_sale_marcado_aunque_el_modelo_no_lo_devuelva():
    """RF-12.6b (D-052)."""
    prov = ProveedorSimulado([{**TAX, "puestos": []}])
    e = crear(proveedor=prov).run({"perfil": _perfil("femenino").model_dump(mode="json")})
    assert e["puestos"] == [{"titulo": "Camarera", "dato": "Camarera", "nivel": 1, "tipo_dato": "puesto",
                             "marcado": True}]


def test_la_huella_de_clasificacion_ignora_nombre_genero_y_titular_pero_no_una_certificacion():
    base = huella_clasificacion(_perfil("femenino"))
    assert huella_clasificacion(_perfil("masculino", nombre="Lucas Ferrer")) == base
    assert huella_clasificacion(_perfil("femenino", titular=None)) == base
    cert = [{"nombre": "Manipulador de alimentos", "origen": ORIGEN}]
    assert huella_clasificacion(_perfil("femenino", certificaciones=cert)) != base


def test_cambiar_el_genero_reescribe_sugeridos_y_marcados_sin_tocar_los_suyos():
    prefs = Preferencias(puestos=["Camarera de sala", "Jefa de barra mía"], puestos_sugeridos=[
        PuestoSugerido(titulo="Camarera de sala", dato="Camarera", nivel=1, tipo_dato="puesto",
                       marcado=True)])
    nuevas = en_su_genero(prefs, "masculino")
    assert nuevas.puestos == ["Camarero de sala", "Jefa de barra mía"]
    assert [(p.titulo, p.dato) for p in nuevas.puestos_sugeridos] == [("Camarero de sala", "Camarera")]


@pytest.mark.bd
def test_cambiar_el_genero_desde_el_perfil_reescribe_los_puestos(app, motor_app, motor_migrador):  # noqa: F811
    c, h = entrar(app)
    u = usuaria(motor_migrador)
    perfil_hecho(motor_app, u, _perfil("femenino"))
    with sesion_de(motor_app, u) as s:
        perfiles.guardar_preferencias(s, u, Preferencias(puestos=["Camarera de sala"], puestos_sugeridos=[
            PuestoSugerido(titulo="Camarera de sala", dato="Camarera", marcado=True)]))
    r = c.patch("/api/perfil/datos", headers=h, json={"campo": "genero_puestos",
                                                      "dato": {"valor": "masculino"}})
    assert r.status_code == 201, r.text
    with sesion_de(motor_app, u) as s:
        assert perfiles.preferencias(s).puestos == ["Camarero de sala"]
    assert tareas(motor_migrador, "clasificar_perfil") == 0  # sin llamar al modelo
