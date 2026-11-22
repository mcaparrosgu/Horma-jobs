"""Fase 4 · T24: tres falsos avisos de la prueba final (F1, F2, F3). Cada uno tiene su caso que antes
avisaba sin motivo y su contrapartida que debe seguir avisando."""
from horma.tools.medir_ats import medir_ats
from horma.tools.rasgos_personales import rasgos_personales
from horma.tools.verificar_trazabilidad import FORMULAS_CORTESIA, verificar_trazabilidad

# --- F1: «Se valora experiencia previa» no es una palabra clave que falte a quien tiene experiencia -----
CV_CAMARERA = """# Ines Inventada

## Experiencia
Camarera · Cafetería Marina · 2020-2024
- Atención de 40 mesas en turnos de fin de semana
"""


def _oferta(*requisitos: str) -> dict:
    return {"requisitos": list(requisitos),
            "taxonomia": {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion",
                          "nivel": "junior", "stack": []}}


def test_f1_las_palabras_de_cortesia_del_requisito_no_cuentan_como_hueco():
    m = medir_ats(CV_CAMARERA, _oferta("Se valora experiencia previa"), CV_CAMARERA)
    assert m["ausentes_sin_origen"] == [] and m["ausentes_con_origen"] == []
    assert m["cobertura"] == 1.0


def test_f1_lo_que_si_falta_sigue_siendo_hueco():
    requisito = "Se valora experiencia previa como cocinero"
    m = medir_ats(CV_CAMARERA, _oferta(requisito), CV_CAMARERA)
    assert m["ausentes_sin_origen"] == [requisito]
    m = medir_ats(CV_CAMARERA, _oferta("Imprescindible carné de manipulador"), CV_CAMARERA)
    assert m["ausentes_sin_origen"] == ["Imprescindible carné de manipulador"]


# --- F2: una frase de la carta puede juntar datos de dos líneas del CV --------------------------------
MAESTRO = """# Nora Inventada

## Experiencia
Analista de datos · Logística Norte · 2021-actual

## Formación
Grado en Ingeniería Informática · Universidad de Deusto · 2014-2018

## Habilidades
Python, SQL, Power BI
"""
FRASE = ("Trabajo con SQL y Python, y mi base es el Grado en Ingeniería Informática "
         "de la Universidad de Deusto.")
FRAGMENTO = "Grado en Ingeniería Informática · Universidad de Deusto · 2014-2018"


def _carta(frase: str) -> list[str]:
    return verificar_trazabilidad(frase, [{"frase": frase, "fragmento": FRAGMENTO}], [MAESTRO],
                                  formulas_cortesia=FORMULAS_CORTESIA, por_frase=True)


def test_f2_la_carta_puede_juntar_datos_que_estan_en_el_cv():
    assert _carta(FRASE) == []


def test_f2_un_dato_que_no_esta_en_ninguna_fuente_sigue_avisando():
    errores = _carta(FRASE.replace("SQL y Python", "Rust y Kubernetes"))
    assert any("rust" in e for e in errores) and any("kubernetes" in e for e in errores)


def test_f2_el_cv_sigue_exigiendo_el_dato_en_su_propio_fragmento():
    linea = "Trabajo con SQL en Universidad de Deusto"
    errores = verificar_trazabilidad(linea, [{"frase": linea, "fragmento": FRAGMENTO}], [MAESTRO])
    assert errores  # en el CV, cada línea responde de sí misma; el cambio es solo para la carta


# --- F3: «idioma extranjero» o «en el extranjero» no son la nacionalidad de nadie ----------------------
def test_f3_idioma_o_lengua_extranjera_no_es_nacionalidad():
    for texto in ("Mi idioma extranjero es el inglés, con nivel B2.",
                  "Estudié inglés como lengua extranjera.",
                  "Dominio de idiomas extranjeros: inglés y francés.",
                  "Trabajé tres años en el extranjero."):
        assert rasgos_personales(texto) == [], texto


def test_f3_la_nacionalidad_sigue_detectandose():
    for texto in ("Al ser extranjera necesitará permiso.", "Soy extranjero y vivo en Sevilla.",
                  "Se buscan trabajadores extranjeros.", "Nacionalidad: española"):
        assert any(r.startswith("nacionalidad") for r in rasgos_personales(texto)), texto
