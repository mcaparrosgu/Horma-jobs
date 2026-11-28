"""Spec 012 · T14c (RF-12.34 y 12.18, D-080): marcas por requisito, relación y franja puesta por código."""
import pytest

from horma.agents.matcher.agent import Matcher
from horma.agents.matcher.schemas import SalidaMatcher
from horma.flows.recomendar import crear
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.match import SIN_COMPROBAR, sin_frase_de_franja
from horma.schemas.preferencias import Preferencias

PERFIL = {"experiencias": [{"puesto": "Camarera", "empresa": "Bar Sol",
                            "origen": {"fuente": "cv", "cv_id": 1, "fragmento": "Camarera"}}]}
REQUISITOS = ["Experiencia en sala", "Menor de 30 años"]
EXPLICACION = "Tienes experiencia en sala. La oferta pide experiencia en sala."


def _oferta():
    return {"oferta_id": 1, "oferta": {
        "titulo": "Camarero/a de sala", "requisitos": REQUISITOS,
        "auditoria": {"fantasma": False, "fraude": False, "salario_publicado": False},
        "taxonomia": {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion",
                      "nivel": "junior"}}}


def _marca(i, tipo="exigido", cubierto="a_medias"):
    return {"requisito": i, "tipo": tipo, "cubierto": cubierto}


def _match(nota=80, marcas=None, **cambios):
    return {"oferta_id": 1, "nota": nota, "condiciones": "medio", "explicacion": EXPLICACION,
            "cita_perfil": "Camarero/a", "cita_oferta": "Experiencia en sala", "relacion": "mismo_puesto",
            "marcas": [_marca(1), _marca(2)] if marcas is None else marcas, **cambios}


def _recomendar(*matches):
    prov = ProveedorSimulado([{"matches": [m]} for m in matches])
    e = crear(proveedor=prov).run({"perfil": PERFIL, "preferencias": Preferencias().model_dump(mode="json"),
                                   "candidatas": [_oferta()]})
    return e["recomendaciones"]


@pytest.mark.parametrize("marcas", [[], [_marca(1)], [_marca(1), _marca(1)], [_marca(1), _marca(3)]])
def test_sin_una_marca_por_requisito_la_oferta_queda_sin_puntuar(marcas):
    assert _recomendar(_match(marcas=marcas)) == []


def test_el_modelo_esta_obligado_a_dar_marcas_y_relacion():
    for falta in ("marcas", "relacion"):
        m = _match()
        del m[falta]
        with pytest.raises(ValueError):
            SalidaMatcher.model_validate({"matches": [m]})


def test_un_rasgo_personal_sale_no_aplica_lo_marque_como_lo_marque_el_modelo():
    [r] = _recomendar(_match(marcas=[_marca(1), _marca(2, "exigido", "no")]))
    assert [m["tipo"] for m in r["marcas"]] == ["exigido", "no_aplica"]
    assert r["relacion"] == "mismo_puesto"


@pytest.mark.parametrize("nota, frase", [
    (100, "Te la recomendamos por esto."), (70, "Te la recomendamos por esto."),
    (69, "Tienes opciones por esto."), (50, "Tienes opciones por esto."),
    (49, "No te la recomendamos, aunque puedes intentarlo."),
    (30, "No te la recomendamos, aunque puedes intentarlo."),
    (29, "No te la recomendamos."), (0, "No te la recomendamos.")])
def test_la_frase_de_franja_la_pone_el_codigo(nota, frase):
    [r] = _recomendar(_match(nota=nota))
    assert r["explicacion"] == f"{frase} {EXPLICACION}"
    assert sin_frase_de_franja(r["explicacion"]) == EXPLICACION


def test_si_el_modelo_escribe_una_frase_de_franja_no_se_repite():
    [r] = _recomendar(_match(explicacion=f"Tienes opciones por esto. {EXPLICACION}"))
    assert r["explicacion"] == f"Te la recomendamos por esto. {EXPLICACION}"


def test_una_explicacion_retirada_queda_sin_frase_delante():
    mala = _match(cita_perfil="Maître")
    [r] = _recomendar(mala, mala)
    assert r["explicacion"] == SIN_COMPROBAR


def test_el_prompt_pide_marcas_relacion_y_las_cuatro_reglas():
    prompt = Matcher.prompt()
    for trozo in ("`marcas`", "`relacion`", "no_aplica", "a_medias", "otro_oficio", "que la oferta no pide",
                  "no opines del nivel", "no consta", "desde 2019"):
        assert trozo in prompt, trozo
    for fuera in ("De 90 a 100 solo si", "La primera frase depende"):
        assert fuera not in prompt, fuera
