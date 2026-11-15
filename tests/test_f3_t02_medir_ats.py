"""Fase 3 · T02: medir_ats (RF-3.5): formato ATS y cobertura de palabras clave de la oferta."""
from horma.evals import errores_ats as errores_ats_evals
from horma.tools.medir_ats import errores_ats, medir_ats

CV = """# Ana Inventada

## Experiencia
**Camarera** · Bar Sol · 2020-2022
- Atención al cliente en sala y gestión de pedidos.
- Manejo de TPV y caja.

## Formación
FP Hostelería · IES Mar · 2018-2020
"""

OFERTA = {
    "titulo": "Camarera de sala",
    "requisitos": ["Atención al cliente", "Manejo de TPV", "Carné de manipulador de alimentos",
                   "Inglés conversacional"],
    "taxonomia": {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion",
                  "nivel": "junior", "stack": ["tpv", "opera pms"]},
}

MAESTRO = CV + "\nCarné de manipulador de alimentos en vigor desde 2019.\nFormación en Opera PMS.\n"


def test_errores_de_formato_como_antes():
    assert errores_ats(CV) == []
    assert errores_ats("# Ana\n## Experiencia\n| a | b |\n|---|---|\n")
    assert errores_ats("# Ana\n## Experiencia\n![foto](x.png)\n")
    assert errores_ats("# Ana\n## Mis aventuras\nCamarera\n")
    assert errores_ats("# Ana\nCamarera\n")
    assert errores_ats("# Ana\n## Experiencia\n<b>Camarera</b>\n")


def test_evals_sigue_exportando_errores_ats():
    assert errores_ats_evals is errores_ats


def test_cobertura_con_requisitos_y_stack():
    r = medir_ats(CV, OFERTA, [MAESTRO])
    assert r["errores_formato"] == []
    assert set(r["presentes"]) == {"Atención al cliente", "Manejo de TPV", "tpv"}
    assert r["cobertura"] == 3 / 6


def test_separa_ausentes_con_origen_y_sin_origen():
    r = medir_ats(CV, OFERTA, [MAESTRO])
    assert set(r["ausentes_con_origen"]) == {"Carné de manipulador de alimentos", "opera pms"}
    assert r["ausentes_sin_origen"] == ["Inglés conversacional"]


def test_fuentes_como_un_solo_texto_y_sin_palabras_clave():
    assert medir_ats(CV, OFERTA, MAESTRO)["ausentes_sin_origen"] == ["Inglés conversacional"]
    r = medir_ats(CV, {"titulo": "x", "requisitos": []}, [])
    assert r["cobertura"] == 1.0 and r["presentes"] == []


def test_acentos_y_mayusculas_no_importan_y_acepta_objetos():
    class T:
        stack = ["TPV"]

    class OfertaObj:
        requisitos = ["ATENCION AL CLIENTE"]
        taxonomia = T()

    r = medir_ats(CV, OfertaObj(), CV)
    assert r["cobertura"] == 1.0
