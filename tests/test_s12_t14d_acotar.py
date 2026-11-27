"""Spec 012 · T14d (RF-12.35; D-080, D-081 y D-085): suelos y topes de la nota, en código."""
import json
import shutil
from pathlib import Path

import pytest

from horma.evals import correr_set, marcas_de
from horma.flows.recomendar import crear
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.match import Marca
from horma.tools.acotar_nota import acotar_nota

RAIZ = Path(__file__).resolve().parent.parent / "evals"


def _nota(nota, marcas, relacion="mismo_puesto", requisitos=None, oferta="junior", perfil="junior",
          con_experiencia=True):
    """`marcas`: «es» = exigido sí; «ea» a medias; «en» no; «vs», «vn»; «x» no aplica."""
    tipos = {"e": "exigido", "v": "valorable", "x": "no_aplica"}
    cubre = {"s": "si", "a": "a_medias", "n": "no"}
    lista = [Marca(requisito=i, tipo=tipos[m[0]], cubierto=cubre[m[1]]) for i, m in enumerate(marcas, 1)]
    return acotar_nota(nota, lista, relacion, requisitos or ["Experiencia"] * len(lista), oferta, perfil,
                       con_experiencia)


@pytest.mark.parametrize("relacion", ["mismo_puesto", "afin"])
def test_regla_1_todos_los_exigidos_cubiertos_y_puesto_cercano(relacion):
    assert _nota(62, ["es", "es"], relacion) == 90
    assert _nota(96, ["es"], relacion) == 96  # un suelo no baja
    assert _nota(62, ["es", "va"], relacion) == 90


def test_regla_1_con_cuatro_o_mas_exigidos_cubiertos_sube_a_95():
    assert _nota(85, ["es"] * 4) == 95  # D-092: cumplir más de lo pedido desempata
    assert _nota(85, ["es"] * 3) == 90
    assert _nota(60, ["es"] * 4 + ["vn"]) == 85  # la regla 3 sigue mandando
    assert _nota(82, ["es"] * 4, "otro_oficio") == 55


def test_regla_2_sin_exigidos_que_apliquen():
    assert _nota(40, []) == 80
    assert _nota(40, [], "afin") == 40  # D-093: la oferta no trae requisitos, solo el mismo puesto
    assert _nota(40, ["vn", "xn"], "afin") == 80
    assert _nota(40, [], "otro_oficio") == 40


def test_regla_3_un_valorable_sin_cubrir_manda_sobre_la_1():
    assert _nota(60, ["es", "vn"]) == 85
    assert _nota(88, ["es", "vn"]) == 88


def test_regla_4_mismo_puesto_con_la_titulacion_sin_mayoria_de_no():
    requisitos = ["Grado en Enfermería", "Experiencia en cuidados críticos"]
    assert _nota(55, ["es", "ea"], requisitos=requisitos) == 70
    assert _nota(55, ["es", "ea"], "afin", requisitos=requisitos) == 55
    assert _nota(55, ["ea", "es"], requisitos=requisitos) == 55  # la titulación, sin cubrir del todo
    assert _nota(55, ["es", "ea"], requisitos=["Inglés", "Experiencia"]) == 55  # sin titulación
    assert _nota(55, ["es", "en"], requisitos=requisitos) == 70  # la mitad en «no» no es mayoría (D-091)
    assert _nota(55, ["es", "en", "en"], requisitos=[*requisitos, "Idioma"]) == 30


@pytest.mark.parametrize("requisito", ["grado en Derecho", "Máster en RR. HH.", "FP de Electricidad",
                                       "Ciclo de grado medio", "Titulo de Enfermería", "Ingeniería"])
def test_regla_4_reconoce_la_titulacion_por_su_primera_palabra(requisito):
    assert _nota(55, ["es", "ea"], requisitos=[requisito, "Experiencia"]) == 70


def test_regla_5_sin_lo_exigido():
    assert _nota(50, ["en", "en", "es"]) == 30
    assert _nota(50, ["en", "es"]) == 50  # la mitad no es mayoría
    assert _nota(50, ["en", "ea"]) == 30  # la mitad en «no» y ningún «sí» (D-091)
    assert _nota(50, ["en", "en", "es"], "otro_oficio") == 20
    assert _nota(50, ["en"], oferta="senior", perfil="junior") == 20
    assert _nota(50, ["en"], "afin", oferta="senior", perfil="junior") == 10  # D-091
    assert _nota(50, ["en"], "otro_oficio", oferta="senior", perfil="junior") == 10
    assert _nota(50, ["en"], oferta="sin_especificar", perfil="junior") == 30
    assert _nota(50, ["en"], oferta="senior", perfil=None) == 30
    assert _nota(12, ["en"]) == 12  # un tope no sube


def test_regla_6_otro_oficio_que_cumple_todo_queda_entre_30_y_55():
    assert _nota(82, ["es", "es"], "otro_oficio") == 55
    assert _nota(10, ["es"], "otro_oficio") == 30
    assert _nota(45, ["es"], "otro_oficio") == 45
    assert _nota(82, ["es"], "otro_oficio", con_experiencia=False) == 82  # sin experiencia no hay oficio (D-091)


def test_regla_7_pedir_menos_nivel_no_cambia_la_nota():
    for marcas, relacion in ((["es", "en"], "afin"), (["en"], "mismo_puesto"), (["es"], "otro_oficio")):
        assert (_nota(45, marcas, relacion, oferta="junior", perfil="senior")
                == _nota(45, marcas, relacion, oferta="senior", perfil="senior"))


@pytest.mark.parametrize("base", [["es"], ["en", "en", "es"], ["es", "vn"], []])
@pytest.mark.parametrize("relacion", ["mismo_puesto", "otro_oficio"])
def test_un_requisito_que_no_aplica_nunca_cambia_la_nota(base, relacion):
    for cubierto in ("xs", "xa", "xn"):
        assert _nota(50, [*base, cubierto], relacion) == _nota(50, base, relacion)


# --- en el flujo y en la traza del eval ------------------------------------------------------------
def _recomendar(puesto, nota=55):
    oferta = {"titulo": "Camarero/a", "requisitos": ["Experiencia en sala"],
              "auditoria": {"fantasma": False, "fraude": False, "salario_publicado": False},
              "taxonomia": {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion",
                            "nivel": "junior"}}
    match = {"oferta_id": 1, "nota": nota, "condiciones": "medio", "relacion": "mismo_puesto",
             "marcas": [{"requisito": 1, "tipo": "exigido", "cubierto": "si"}], "cita_perfil": "Camarero/a", "cita_oferta": "sala",
             "explicacion": "Tienes experiencia en sala. La oferta pide experiencia en sala."}
    perfil = {"experiencias": [{"puesto": puesto, "origen": {"fuente": "cv", "cv_id": 1,
                                                             "fragmento": puesto}}]}
    return crear(proveedor=ProveedorSimulado([{"matches": [match]}])).run(
        {"perfil": perfil, "preferencias": {}, "candidatas": [{"oferta_id": 1, "oferta": oferta}]})


def test_la_franja_usa_la_nota_acotada_y_dos_gemelas_reciben_la_misma():
    ellas = [_recomendar(p)["recomendaciones"][0] for p in ("Camarera", "Camarero")]
    assert [m["nota"] for m in ellas] == [90, 90]
    assert ellas[0]["explicacion"].startswith("Te la recomendamos por esto.")


def test_el_eval_graba_la_nota_del_modelo_las_marcas_y_la_relacion(tmp_path):
    caso = "01-camarera-camarera-sala"
    shutil.copytree(RAIZ / "recomendacion" / "casos" / caso, tmp_path / "recomendacion" / "casos" / caso)
    r = correr_set("recomendacion", raiz=tmp_path, simulado=True)
    [[salida]] = [r["detalle"][0]["salidas"]]
    assert salida["nota_modelo"] == 90 and salida["marcas"] and salida["relacion"] == "otro_oficio"
    assert json.dumps(r)  # se guarda tal cual en `resultados/`
