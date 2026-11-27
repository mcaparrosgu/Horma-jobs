"""Arreglos a 390 px: botones de la portada a todo el ancho y sin «Calificar todas» cuando no hay perfil."""

from pathlib import Path

ESTATICOS = Path(__file__).parent.parent / "horma" / "web" / "static"


def test_botones_de_la_portada_en_movil():
    css = (ESTATICOS / "estilo.css").read_text(encoding="utf-8")
    assert ".cabecera:not(:has(nav)) .derecha{ display: grid;" in css


def test_sin_perfil_no_se_ofrece_calificar_todas():
    js = (ESTATICOS / "ofertas.js").read_text(encoding="utf-8")
    assert '|| !$("sin-perfil").hidden;' in js
    assert '"contador", "calificar-todas"]' in js
