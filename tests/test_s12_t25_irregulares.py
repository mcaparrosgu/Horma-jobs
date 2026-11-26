"""Spec 012, T25 (RF-12.30i): la búsqueda casa también con las formas irregulares del léxico."""
import pytest

from horma.tools.normalizar_titulo import canonico, casa_con_puestos


@pytest.mark.parametrize("oferta, puesto", [
    ("Gobernante/a de pisos", "Gobernanta"), ("Gobernanta", "Gobernante/a"),
    ("Actriz de doblaje", "Actor"), ("Actor/actriz de doblaje", "Actriz"),
    ("Waiter/waitress", "Waitress"), ("Waitress", "Waiter/waitress"),
    ("Jueza sustituta", "Juez/a"), ("Matrón de hospital", "Matrona"),
])
def test_casa_con_la_forma_irregular(oferta, puesto):
    assert casa_con_puestos(oferta, [puesto])


@pytest.mark.parametrize("a, b", [("Actor", "Actriz"), ("Actor/actriz", "Actriz"), ("Matrón/a", "Matrona"),
                                  ("Gobernante/a", "Gobernanta"), ("Waiter/waitress", "Waiter")])
def test_misma_clave(a, b):
    assert canonico(a) == canonico(b)


def test_asistenta_no_es_asistente():
    assert canonico("Asistenta") != canonico("Asistente")
    assert not casa_con_puestos("Asistente de dirección", ["Asistenta"])
    assert not casa_con_puestos("Asistenta de hogar", ["Asistente"])
