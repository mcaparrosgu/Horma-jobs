"""S7, T35: la carta suena escrita por una persona (RF-10.3g). Simulado: el prompt y su ejemplo."""
import json
import re
from pathlib import Path

from horma.tools.estructura_carta import errores_estructura_carta
from horma.tools.verificar_trazabilidad import FORMULAS_CORTESIA, verificar_trazabilidad

PROMPT = (Path(__file__).parent.parent / "horma" / "agents" / "redactor_carta" / "prompt.md").read_text(
    encoding="utf-8")


def _ejemplo() -> dict:
    return json.loads(re.search(r"```json\n(.*?)\n```", PROMPT, re.S).group(1))


def test_el_prompt_trae_la_estructura_de_rf_10_3g():
    for frase in ("lo que te interesa del puesto", "Frases cortas, una idea por frase", "en llano",
                  "lo que quiere aprender", "clichés de autoalabanza", "halagos a la empresa",
                  "menos de una\n  página"):
        assert frase in PROMPT, frase
    # RT-08 y el contenido no fiable siguen
    assert "traza" in PROMPT and "instrucciones_embebidas" in PROMPT


def test_el_ejemplo_cumple_la_traza_y_la_forma():
    e = _ejemplo()
    assert verificar_trazabilidad(e["carta"], e["traza"], e["fuentes"], formulas_cortesia=FORMULAS_CORTESIA,
                                  por_frase=True) == []
    assert errores_estructura_carta(e["carta"]) == []


def test_la_forma_rechaza_cliches_listas_y_frases_kilometricas():
    carta = ("Hola equipo,\n\n" + "Soy una persona apasionada. " + "\n\n- punto\n\n" + "palabra " * 40
             + ".\n\nUn saludo")
    errores = " ".join(errores_estructura_carta(carta))
    assert "apasionad" in errores and "listas" in errores and "Frase demasiado larga" in errores
    assert errores_estructura_carta("Hola equipo,\n\nUn párrafo.\n\nUn saludo")   # faltan párrafos
