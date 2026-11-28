"""Spec 012 · T14r (RF-12.21, D-112): atribuir a un puesto tareas que su descripción no recoge es un dato
inventado; el revisor lo rechaza y el 58 de la pasada 1 de T14m queda como ejemplo en su control."""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROMPT = (RAIZ / "horma" / "agents" / "revisor_explicacion" / "prompt.md").read_text(encoding="utf-8")
CONTROL = json.loads((RAIZ / "evals" / "recomendacion" / "revisor.json").read_text(encoding="utf-8"))


def test_el_prompt_rechaza_tareas_atribuidas_a_un_puesto_que_no_las_describe():
    assert "atribuye a un puesto tareas que su descripción no recoge" in PROMPT


def test_el_58_esta_en_el_control_como_no_apoyado():
    [s] = [s for s in CONTROL if "Frutas Júcar" in s["explicacion"]]
    assert s["apoyada"] is False
    assert not s["explicacion"].startswith("Te la recomendamos")  # el revisor no ve la frase de franja
    [sin_descripcion] = [e for e in s["perfil"]["experiencias"] if e["empresa"] == "Frutas Júcar"]
    assert not sin_descripcion.get("descripcion")
