"""S8 · T60: «No consta en tu CV» (RF-10.13) solo dice lo que de verdad falta. Salió de la pasada del 22-nov (J1, I5):
el CV de Irene tenía CoverManager, sumillería, inglés B2 y más de cinco años en sala, y el aviso los negaba."""
import pytest

from horma.tools.medir_ats import medir_ats

CV_IRENE = """# Irene Navarro Soler

## Experiencia
Jefa de sala · Restaurante La Albufera Mar · 2021-2023
- Coordinó un equipo de 8 camareros y 2 ayudantes en un restaurante de 90 cubiertos.
- Formó a 12 personas nuevas en servicio, carta de vinos y uso del TPV.
- Gestionó reservas y eventos de hasta 120 invitados con CoverManager.
Camarera · Cafetería El Mercat · 2015-2018

## Formación
Curso de sumillería básica (40 horas) · Asociación Valenciana de Sumilleres · 2017

## Idiomas
Inglés: B2 (Cambridge First Certificate)

## Habilidades
TPV Ágora · CoverManager · Excel básico · Gestión de equipos
"""


def _oferta(*requisitos: str) -> dict:
    return {"requisitos": list(requisitos),
            "taxonomia": {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion",
                          "nivel": "senior", "stack": []}}


def _huecos(*requisitos: str, fuentes: str = CV_IRENE) -> list[str]:
    return medir_ats(CV_IRENE, _oferta(*requisitos), fuentes)["ausentes_sin_origen"]


@pytest.mark.parametrize("requisito", [
    "Mínimo 5 años de experiencia en sala, 2 de ellos como responsable de equipo",
    "Inglés B1 o superior",
    "Conocimientos de vino; se valorará formación en sumillería",
    "Manejo de TPV y de programas de reservas (CoverManager o similar)",
    "CoverManager",
    "Inglés B2",
])
def test_lo_que_el_cv_si_tiene_no_es_un_hueco(requisito):
    assert _huecos(requisito) == []


@pytest.mark.parametrize("requisito", [
    "Excel avanzado",                         # el CV dice «Excel básico»
    "Inglés C1",                              # el CV llega a B2
    "Carné de manipulador de alimentos",
    "Se valora experiencia previa como cocinero",
    "Francés",
    "Manejo de A3ERP",
])
def test_lo_que_falta_de_verdad_sigue_siendo_un_hueco(requisito):
    assert _huecos(requisito) == [requisito]


def test_una_frase_larga_la_juzga_el_redactor_no_el_recuento_de_palabras():
    larga = "Técnico Superior en Administración y Finanzas o similar"
    assert _huecos(larga) == []   # ≥ 4 palabras con contenido: sin hueco de código; lo anota el redactor


def test_el_nivel_de_idioma_pide_igual_o_mayor():
    assert _huecos("Inglés B1") == [] and _huecos("Inglés B2") == [] and _huecos("Inglés C2") == ["Inglés C2"]


def test_plural_de_palabras_cortas():
    assert _huecos("Conocimientos de vino") == [] and _huecos("Atención de mesas", fuentes="Atención de mesa") == []
