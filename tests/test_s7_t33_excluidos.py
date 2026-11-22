"""S7, T33: los términos excluidos van al final de «Qué buscas» (RF-10.6e, RF-10.6f)."""
from pathlib import Path

ESTATICOS = Path(__file__).parent.parent / "horma" / "web" / "static"
HTML = (ESTATICOS / "ofertas.html").read_text(encoding="utf-8")


def test_excluidos_va_despues_de_condiciones_y_antes_de_guardar_y_buscar():
    marcas = ("Condiciones</legend>", 'id="grupo-excluidos"', 'id="guardar-busca"')
    cond, exc, guardar = (HTML.index(x) for x in marcas)
    assert cond < exc < guardar


def test_no_queda_la_rejilla_de_dos_columnas():
    assert "grupos-dos" not in HTML
