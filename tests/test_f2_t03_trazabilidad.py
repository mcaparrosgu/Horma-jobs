"""Fase 2 · T03: verificar_trazabilidad (RF-2.9, RT-08).

Un CV base solo se guarda si cada frase tiene su fragmento real en el CV maestro y no aparece ninguna
fecha, cifra, cargo o nombre propio que el maestro no tenga."""
import pytest

from horma.tools.verificar_trazabilidad import verificar_trazabilidad

MAESTRO = """# Ana Inventada

## Experiencia
**Camarera** · Bar Sol · 2020-2022
Atención al cliente en sala y gestión de pedidos.
Reducción del tiempo de espera en un 15 %.

## Formación
FP Hostelería · IES Mar · 2018-2020
"""

TRAZA_OK = [
    {"frase": "Ana Inventada", "fragmento": "Ana Inventada"},
    {"frase": "**Camarera** · Bar Sol · 2020-2022", "fragmento": "**Camarera** · Bar Sol · 2020-2022"},
    {"frase": "Atendí a clientes en sala y gestioné pedidos.",
     "fragmento": "Atención al cliente en sala y gestión de pedidos."},
    {"frase": "Reduje el tiempo de espera un 15 %.",
     "fragmento": "Reducción del tiempo de espera en un 15 %."},
    {"frase": "FP Hostelería · IES Mar · 2018-2020", "fragmento": "FP Hostelería · IES Mar · 2018-2020"},
]

CV_OK = """# Ana Inventada

## Experiencia
**Camarera** · Bar Sol · 2020-2022
- Atendí a clientes en sala y gestioné pedidos.
- Reduje el tiempo de espera un 15 %.

## Formación
FP Hostelería · IES Mar · 2018-2020
"""


def test_un_cv_base_fiel_no_da_errores():
    assert verificar_trazabilidad(CV_OK, TRAZA_OK, MAESTRO) == []


def test_acepta_objetos_con_frase_y_fragmento():
    class T:
        def __init__(self, frase, fragmento):
            self.frase, self.fragmento = frase, fragmento

    traza = [T(t["frase"], t["fragmento"]) for t in TRAZA_OK]
    assert verificar_trazabilidad(CV_OK, traza, MAESTRO) == []


def test_frase_sin_traza_se_rechaza():
    cv = CV_OK + "\n- Gestioné un equipo de cocina.\n"
    errores = verificar_trazabilidad(cv, TRAZA_OK, MAESTRO)
    assert any("sin origen" in e and "equipo de cocina" in e for e in errores)


def test_fragmento_que_no_esta_en_el_maestro_se_rechaza():
    traza = TRAZA_OK + [{"frase": "Gestioné un equipo de cocina.",
                         "fragmento": "Gestión de un equipo de cocina"}]
    cv = CV_OK + "\n- Gestioné un equipo de cocina.\n"
    errores = verificar_trazabilidad(cv, traza, MAESTRO)
    assert any("no está en el CV maestro" in e for e in errores)


@pytest.mark.parametrize("cv_malo, esperado", [
    # fecha inventada
    (CV_OK.replace("2020-2022", "2019-2022"), "2019"),
    # cargo subido
    (CV_OK.replace("**Camarera** · Bar Sol", "**Jefa de sala** · Bar Sol"), "jefa"),
    # empresa cambiada
    (CV_OK.replace("Bar Sol", "Bar Luna"), "luna"),
    # titulación cambiada
    (CV_OK.replace("FP Hostelería", "Grado en Turismo"), "grado"),
    # cifra inventada
    (CV_OK.replace("un 15 %", "un 40 %"), "40"),
])
def test_rechaza_el_100_por_cien_de_datos_que_no_existen_en_el_maestro(cv_malo, esperado):
    traza = []
    for linea in cv_malo.splitlines():
        # la traza "engaña": cada línea apunta al fragmento original más parecido del maestro
        original = next((t["fragmento"] for t in TRAZA_OK if t["frase"].split("·")[0].strip("* ")[:6]
                         == linea.lstrip("- ").split("·")[0].strip("* ")[:6]), None)
        if original and linea.strip() and not linea.startswith("#"):
            traza.append({"frase": linea.lstrip("- ").strip(), "fragmento": original})
    # las frases de descripción conservan su traza real
    traza += [t for t in TRAZA_OK if t["frase"].startswith(("Atendí", "Reduje"))]
    errores = verificar_trazabilidad(cv_malo, traza, MAESTRO)
    assert errores, "debería haberse rechazado"
    assert any(esperado in e.casefold() for e in errores), errores


def test_una_fecha_que_no_esta_en_el_maestro_se_rechaza_aunque_la_traza_diga_otra_cosa():
    cv = CV_OK + "\n- Premio al mejor servicio 2023.\n"
    traza = TRAZA_OK + [{"frase": "Premio al mejor servicio 2023.",
                         "fragmento": "Atención al cliente en sala"}]
    errores = verificar_trazabilidad(cv, traza, MAESTRO)
    assert any("2023" in e for e in errores)


def test_los_titulos_de_seccion_no_necesitan_traza():
    cv = "# Ana Inventada\n\n## Experiencia\n\n## Formación\n"
    assert verificar_trazabilidad(cv, [{"frase": "Ana Inventada", "fragmento": "Ana Inventada"}],
                                  MAESTRO) == []


def test_ignora_marcas_de_markdown_y_mayusculas_al_comparar():
    cv = "# Ana Inventada\n\n* **CAMARERA** · bar sol · 2020-2022\n"
    traza = [{"frase": "Ana Inventada", "fragmento": "Ana Inventada"},
             {"frase": "camarera · bar sol · 2020-2022", "fragmento": "**Camarera** · Bar Sol · 2020-2022"}]
    assert verificar_trazabilidad(cv, traza, MAESTRO) == []
