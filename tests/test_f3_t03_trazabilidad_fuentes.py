"""Fase 3 · T03: verificar_trazabilidad con varias fuentes y fórmulas de cortesía (RF-3.3, RF-3.6, RT-08).

La llamada de la fase 2 (un solo texto) debe dar el mismo resultado; las fuentes nuevas son el CV base
(editado por la usuaria) y, solo para la carta, la oferta."""
from horma.tools.verificar_trazabilidad import FORMULAS_CORTESIA, verificar_trazabilidad

MAESTRO = """# Ana Inventada

## Experiencia
**Camarera** · Bar Sol · 2020-2022
Atención al cliente en sala y gestión de pedidos.

## Formación
FP Hostelería · IES Mar · 2018-2020
"""

# La usuaria editó su CV base y añadió una línea que el maestro no tiene.
CV_BASE_EDITADO = MAESTRO + "\nColaboración con el equipo de eventos del hotel en temporada alta.\n"

OFERTA = "Hotel Marina busca camarera con manejo de TPV para su restaurante de playa."

CV = """# Ana Inventada

## Experiencia
**Camarera** · Bar Sol · 2020-2022
- Atendí a clientes en sala y gestioné pedidos.
"""
TRAZA_CV = [
    {"frase": "Ana Inventada", "fragmento": "Ana Inventada"},
    {"frase": "**Camarera** · Bar Sol · 2020-2022", "fragmento": "**Camarera** · Bar Sol · 2020-2022"},
    {"frase": "Atendí a clientes en sala y gestioné pedidos.",
     "fragmento": "Atención al cliente en sala y gestión de pedidos."},
]


def test_la_llamada_de_la_fase_2_da_el_mismo_resultado():
    assert verificar_trazabilidad(CV, TRAZA_CV, MAESTRO) == []
    assert verificar_trazabilidad(CV, TRAZA_CV, [MAESTRO]) == []
    cv = CV + "- Gestioné un equipo de cocina.\n"
    solo = verificar_trazabilidad(cv, TRAZA_CV, MAESTRO)
    assert solo == verificar_trazabilidad(cv, TRAZA_CV, [MAESTRO])
    assert any("sin origen" in e for e in solo)


def test_un_fragmento_del_cv_base_editado_es_valido():
    linea = "Colaboré con el equipo de eventos del hotel en temporada alta."
    cv = CV + f"- {linea}\n"
    traza = TRAZA_CV + [{"frase": linea,
                         "fragmento": "Colaboración con el equipo de eventos del hotel en temporada alta."}]
    assert verificar_trazabilidad(cv, traza, [MAESTRO, CV_BASE_EDITADO]) == []
    errores = verificar_trazabilidad(cv, traza, [MAESTRO])  # sin el CV base editado, no hay origen
    assert any("no está" in e for e in errores)


def test_un_fragmento_de_la_oferta_vale_solo_si_la_oferta_es_fuente():
    carta = "Me interesa el restaurante de playa del Hotel Marina.\n"
    traza = [{"frase": "Me interesa el restaurante de playa del Hotel Marina.",
              "fragmento": "Hotel Marina busca camarera con manejo de TPV para su restaurante de playa."}]
    assert verificar_trazabilidad(carta, traza, [MAESTRO, CV_BASE_EDITADO, OFERTA]) == []
    # en el CV (sin la oferta entre las fuentes) el mismo fragmento se rechaza
    assert verificar_trazabilidad(carta, traza, [MAESTRO, CV_BASE_EDITADO])


def test_saludo_y_despedida_de_la_lista_no_piden_traza():
    assert "Un saludo" in FORMULAS_CORTESIA
    carta = ("Estimado equipo de selección,\n\nMe interesa el puesto de camarera en Hotel Marina.\n\n"
             "Un saludo,\nAna Inventada\n")
    traza = [{"frase": "Me interesa el puesto de camarera en Hotel Marina.",
              "fragmento": "Hotel Marina busca camarera con manejo de TPV"},
             {"frase": "Ana Inventada", "fragmento": "Ana Inventada"}]
    fuentes = [MAESTRO, OFERTA]
    assert verificar_trazabilidad(carta, traza, fuentes, formulas_cortesia=FORMULAS_CORTESIA) == []
    # sin la lista, el saludo y la despedida piden traza
    assert verificar_trazabilidad(carta, traza, fuentes)


def test_una_formula_que_no_esta_en_la_lista_pide_traza():
    carta = "Un abrazo fuerte,\n"
    errores = verificar_trazabilidad(carta, [], [MAESTRO], formulas_cortesia=FORMULAS_CORTESIA)
    assert any("sin origen" in e for e in errores)


def test_fechas_cargos_empresas_y_titulaciones_cambiados_se_rechazan_con_varias_fuentes():
    fuentes = [MAESTRO, CV_BASE_EDITADO]
    casos = [
        (CV.replace("2020-2022", "2019-2022"), "2019"),
        (CV.replace("**Camarera** · Bar Sol", "**Jefa de sala** · Bar Sol"), "jefa"),
        (CV.replace("Bar Sol", "Bar Luna"), "luna"),
    ]
    for cv_malo, esperado in casos:
        traza = TRAZA_CV + [{"frase": linea.lstrip("- ").strip(), "fragmento": TRAZA_CV[1]["fragmento"]}
                            for linea in cv_malo.splitlines() if "·" in linea]
        errores = verificar_trazabilidad(cv_malo, traza, fuentes)
        assert any(esperado in e.casefold() for e in errores), (esperado, errores)
    titulacion = "## Formación\nGrado en Turismo · IES Mar · 2018-2020\n"
    traza = [{"frase": "Grado en Turismo · IES Mar · 2018-2020",
              "fragmento": "FP Hostelería · IES Mar · 2018-2020"}]
    assert any("grado" in e.casefold() for e in verificar_trazabilidad(titulacion, traza, fuentes))


def test_una_fecha_solo_de_la_oferta_vale_para_la_carta_si_la_oferta_es_fuente():
    carta = "Me presento a la oferta publicada en 2026.\n"
    traza = [{"frase": "Me presento a la oferta publicada en 2026.", "fragmento": "publicada en 2026"}]
    oferta = "Oferta publicada en 2026 por Hotel Marina."
    assert verificar_trazabilidad(carta, traza, [MAESTRO, oferta]) == []
    assert any("2026" in e for e in verificar_trazabilidad(carta, traza, [MAESTRO]))


def test_por_frase_la_traza_va_por_frase_y_no_por_parrafo():
    carta = "Hola equipo,\nTrabajé en Bar Sol desde 2020. Me gusta atender mesas con calma.\nUn saludo"
    fuente = "Camarera en Bar Sol, 2020-2023\nAtender mesas con calma"
    traza = [{"frase": "Trabajé en Bar Sol desde 2020.", "fragmento": "Camarera en Bar Sol, 2020-2023"},
             {"frase": "Me gusta atender mesas con calma.", "fragmento": "Atender mesas con calma"}]
    formulas = ("Hola equipo,", "Un saludo")
    assert verificar_trazabilidad(carta, traza, fuente, formulas, por_frase=True) == []
    assert verificar_trazabilidad(carta, traza, fuente, formulas)  # por línea falla


def test_por_frase_una_frase_corta_de_carta_no_se_trata_como_cabecera():
    carta = "Mi nivel es B1.\nUn saludo"
    traza = [{"frase": "Mi nivel es B1.", "fragmento": "Inglés B1"}]
    assert verificar_trazabilidad(carta, traza, "Inglés B1", ("Un saludo",), por_frase=True) == []
    assert verificar_trazabilidad(carta, traza, "Inglés B1", ("Un saludo",))  # en el CV sí lo es
