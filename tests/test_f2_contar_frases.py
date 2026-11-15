import pytest

from horma.schemas.match import contar_frases


@pytest.mark.parametrize("texto,esperadas", [
    ("Una frase. Otra frase.", 2),
    ("Se piden 5-7 años en RR. HH., estudios y alemán. El perfil no tiene experiencia en RR. HH. y su inglés es B1.", 2),
    ("Trabaja en EE. UU. desde 2020. Habla inglés.", 2),
    ("Tiene idiomas, p. ej. inglés y alemán. Falta experiencia.", 2),
    ("Una. Dos. Tres. Cuatro.", 4),
    ("Una sola frase.", 1),
])
def test_contar_frases(texto, esperadas):
    assert contar_frases(texto) == esperadas
