"""T23 (RF-4.8b): los 12 prompts de los agentes activos cumplen las líneas rojas que se pueden
comprobar en el texto del prompt. La tabla completa está en docs/revision-lineas-rojas.md."""
import re
from pathlib import Path

import pytest

from horma.agents.registry import AGENTES

PROMPTS = {n: (Path(__import__(a.__module__, fromlist=["x"]).__file__).parent / "prompt.md")
           .read_text(encoding="utf-8") for n, a in AGENTES.items()}


def test_estan_los_13_agentes_activos():
    assert len(PROMPTS) == 13


@pytest.mark.parametrize("nombre", sorted(PROMPTS))
def test_el_prompt_trata_el_contenido_como_no_fiable_y_no_lo_obedece(nombre):
    p = PROMPTS[nombre]
    assert "no fiable" in p.lower()
    assert re.search(r"\bno\s+las\s+(ejecutes|sigas)\b", p, re.IGNORECASE)


# El juez solo señala problemas en CV y cartas; no extrae, puntúa ni guarda datos. Los rasgos
# personales de esos textos los retira el código (`flows/candidatura.py`, RT-09).
SIN_LINEA_ART9 = {"juez-candidatura"}


@pytest.mark.parametrize("nombre", sorted(set(PROMPTS) - SIN_LINEA_ART9))
def test_el_prompt_prohibe_edad_nacionalidad_y_categorias_especiales(nombre):
    p = PROMPTS[nombre].lower()
    assert "edad" in p and "nacionalidad" in p
    assert re.search(r"categor[ií]as? especial", p)
