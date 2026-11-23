"""S8 · T66: saludos de la carta con la puntuación correcta; las antiguas se aceptan."""
from pathlib import Path

from horma.tools.verificar_trazabilidad import FORMULAS_CORTESIA, verificar_trazabilidad

NUEVAS = ("Hola, equipo:", "Estimado equipo de selección:", "Estimados señores:", "Buenos días:")
VIEJAS = ("Hola equipo,", "Estimado equipo de selección,", "Estimados señores,", "Buenos días,")


def test_la_lista_cerrada_trae_las_formas_nuevas_y_conserva_las_antiguas():
    assert all(f in FORMULAS_CORTESIA for f in NUEVAS + VIEJAS)


def test_el_prompt_y_su_ejemplo_solo_traen_formas_nuevas():
    prompt = " ".join(Path("horma/agents/redactor_carta/prompt.md").read_text(encoding="utf-8").split())
    assert all(f"«{f}»" in prompt for f in NUEVAS)
    assert "Hola, equipo:" in prompt
    assert not any(v in prompt for v in VIEJAS)


def test_los_casos_del_eval_cv_usan_la_forma_nueva():
    for caso in Path("evals/cv/casos").rglob("entrada.json"):
        assert "Hola equipo," not in caso.read_text(encoding="utf-8"), caso


def test_una_carta_con_saludo_nuevo_o_antiguo_pasa_la_comprobacion():
    for saludo in ("Hola, equipo:", "Hola equipo,"):
        carta = f"{saludo}\nTrabajé en Bar Sol desde 2020.\nUn saludo"
        assert verificar_trazabilidad(
            carta, [{"frase": "Trabajé en Bar Sol desde 2020.", "fragmento": "Bar Sol desde 2020"}],
            ["Camarera · Bar Sol · 2020-2024. Bar Sol desde 2020"],
            formulas_cortesia=FORMULAS_CORTESIA, por_frase=True) == []
