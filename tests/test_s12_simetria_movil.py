"""Simetría a 390 px (RF-6.4b): paneles a todo el ancho, botones en columnas iguales y sin cajas vacías."""

from pathlib import Path

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"


def test_reglas_de_simetria_en_movil():
    css = (ESTATICOS / "estilo.css").read_text(encoding="utf-8")
    assert ".pantalla-perfil{ align-items: stretch; }" in css
    assert "dialog.ventana > header{ flex-wrap: nowrap;" in css
    assert ".fila:not([hidden]):not(header):not(:has(> :not(button, .boton))){ display: grid;" in css


def test_sin_nada_que_revisar_no_queda_un_panel_vacio():
    js = (ESTATICOS / "candidatura.js").read_text(encoding="utf-8")
    assert 'c.preparacion !== "pendiente_de_ti") { s.hidden = true; return s; }' in js


def test_acciones_de_fuente_y_papelera_en_rejilla():
    js = (ESTATICOS / "ingesta.js").read_text(encoding="utf-8")
    assert 'nodo("div", null, "fila acciones-fuente")' in js
    css = (ESTATICOS / "estilo.css").read_text(encoding="utf-8")
    assert ".fila.acciones-fuente{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr));" in css
    assert ".fila > button.icono:last-child:nth-child(odd){ grid-column: 1 / -1; }" in css
