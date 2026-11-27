"""Spec 012 · T12, T28 y T29: el `matcher` copia ciega, sin condiciones y citas comprobadas."""
import json

from horma.agents.matcher.agent import Matcher
from horma.flows.recomendar import crear
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.match import SIN_COMPROBAR
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias
from horma.tools.huella_perfil import huella_compatibilidad
from horma.web.services.recomendaciones import en_su_genero


def _o(texto):
    return {"fuente": "cv", "cv_id": 1, "fragmento": texto}


def _perfil(nombre="Lucía Ferrer", puesto="Camarera", descripcion="Lucía fue encargada de turno"):
    return Perfil.model_validate({
        "nombre": nombre, "experiencias": [{"puesto": puesto, "empresa": "Bar Sol", "inicio": "2021",
                                            "fin": "2024", "descripcion": descripcion, "origen": _o(puesto)}],
        "taxonomia": {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion",
                      "nivel": "junior", "stack": []}}).model_dump(mode="json")


def _oferta(i):
    return {"oferta_id": i, "oferta": {
        "titulo": "Camarero/a de sala", "requisitos": ["Experiencia en sala"],
        "auditoria": {"fantasma": False, "fraude": False, "salario_publicado": False},
        "taxonomia": {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion",
                      "nivel": "junior", "stack": []}}}


def _match(i, nota=80, cita_perfil="Camarero/a", cita_oferta="Experiencia en sala"):
    return {"oferta_id": i, "nota": nota, "condiciones": "medio",
            "explicacion": "Tienes experiencia en sala. La oferta pide experiencia en sala.",
            "cita_perfil": cita_perfil, "cita_oferta": cita_oferta}


def _recomendar(respuestas, ids=(1,), perfil=None, prefs=None):
    prov = ProveedorSimulado(respuestas)
    e = crear(proveedor=prov).run({
        "perfil": perfil or _perfil(), "preferencias": (prefs or Preferencias()).model_dump(mode="json"),
        "candidatas": [_oferta(i) for i in ids]})
    return prov, {m["oferta_id"]: m for m in e["recomendaciones"]}


# --- T12: citas comprobadas con un reintento (RF-12.19, S6) ----------------------------------------
def test_una_cita_inventada_se_pide_una_vez_mas_solo_para_esa_oferta():
    prov, r = _recomendar([{"matches": [_match(1), _match(2, cita_perfil="Maître")]},
                           {"matches": [_match(2, nota=70)]}], ids=(1, 2))
    assert len(prov.llamadas) == 2
    assert '"oferta_id":1' not in prov.llamadas[1]["usuario"]
    assert r[2]["nota"] == 70 and not r[2]["retirada"] and r[2]["cita_perfil"] == "Camarero/a"


def test_si_vuelve_a_fallar_se_retira_la_explicacion_y_se_conserva_la_nota():
    mala = {"matches": [_match(1, cita_oferta="Se valora francés")]}
    prov, r = _recomendar([mala, mala])
    assert len(prov.llamadas) == 2
    assert r[1] == {**r[1], "nota": 80, "retirada": True, "explicacion": SIN_COMPROBAR,
                    "cita_perfil": "", "cita_oferta": ""}


def test_si_el_reintento_falla_entero_la_nota_se_conserva():
    prov, r = _recomendar([{"matches": [_match(1, cita_perfil="Maître")]}, RuntimeError("sin red")])
    assert r[1]["nota"] == 80 and r[1]["explicacion"] == SIN_COMPROBAR


def test_una_oferta_sin_resultado_queda_sin_puntuar():
    _, r = _recomendar([{"matches": [_match(1)]}], ids=(1, 2))
    assert set(r) == {1}


def test_el_prompt_pide_las_franjas_citas_literales_y_calla_las_instrucciones():
    prompt = Matcher.prompt()
    for trozo in ("70-100", "50-69", "30-49", "0-29", "literal", "instrucciones", "adjetivos"):
        assert trozo in prompt, trozo
    assert "condiciones de trabajo que busca" not in prompt


# --- T28: copia ciega y sin condiciones (RF-12.30, RF-12.31) ---------------------------------------
def test_el_modelo_no_recibe_el_nombre_ni_el_genero_ni_las_condiciones():
    prov, _ = _recomendar([{"matches": [_match(1)]}], prefs=Preferencias(sueldo_minimo=19999))
    enviado = prov.llamadas[0]["usuario"]
    for trozo in ("Lucía", "Camarera", "19999", "sueldo_minimo", "encargada"):
        assert trozo not in enviado, trozo
    assert "Camarero/a" in enviado and json.loads(enviado)["perfil"]["taxonomia"]


def test_cambiar_el_nombre_no_cambia_la_huella_y_anadir_experiencia_si():
    base = Perfil.model_validate(_perfil(descripcion="Sala y barra"))
    otro_nombre = base.model_copy(update={"nombre": "Marta Soler"})
    assert huella_compatibilidad(base) == huella_compatibilidad(otro_nombre)
    assert huella_compatibilidad(base) != huella_compatibilidad(Perfil.model_validate(_perfil()))


# --- T29: citas contra la copia --------------------------------------------------------------------
def test_la_cita_de_la_copia_existe_y_se_ensena_en_su_genero():
    _, r = _recomendar([{"matches": [_match(1, cita_perfil="encargado/a de turno")]}])
    assert not r[1]["retirada"]
    fila = en_su_genero([dict(r[1])], "femenino")[0]
    assert fila["cita_perfil"] == "encargada de turno"
    assert en_su_genero([dict(r[1])], None)[0]["cita_perfil"] == "encargado/a de turno"


def test_una_cita_con_su_nombre_no_existe_y_se_pide_otra_vez():
    prov, r = _recomendar([{"matches": [_match(1, cita_perfil="Lucía fue encargada")]},
                           {"matches": [_match(1)]}])
    assert len(prov.llamadas) == 2 and r[1]["cita_perfil"] == "Camarero/a"
