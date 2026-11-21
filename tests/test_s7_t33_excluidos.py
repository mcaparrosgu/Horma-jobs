"""S7, T33: los términos excluidos van al final de «Qué buscas» (RF-10.6e)."""
from pathlib import Path

HTML = (Path(__file__).parent.parent / "horma" / "web" / "static" / "ofertas.html").read_text(encoding="utf-8")


def test_excluidos_va_despues_de_condiciones_y_antes_de_guardar_y_buscar():
    cond, exc, guardar = (HTML.index(x) for x in ("Condiciones</legend>", 'id="grupo-excluidos"', 'id="guardar-busca"'))
    assert cond < exc < guardar


def test_puestos_sugeridos_ocupa_todo_el_ancho():
    assert "grupos-dos" not in HTML
