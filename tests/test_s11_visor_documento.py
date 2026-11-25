"""Spec 011 · T08o · «Ver» un CV o una carta enseña el documento a toda la ventana (prueba de Mar, 25-nov).
Causa comprobada en Chrome: `.ventana-cuerpo` es una rejilla con `align-content: start`; su fila mide lo
que el iframe pide por defecto (150 px) y `height: 100%` no se resuelve contra una fila automática.
Estático: lo visual se comprueba en el navegador."""
import re
from pathlib import Path

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"


def _regla(css: str, selector: str) -> str:
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert m, f"falta la regla {selector}"
    return m.group(1)


def test_el_cuerpo_con_el_documento_estira_su_fila_a_toda_la_ventana():
    css = (ESTATICOS / "estilo.css").read_text(encoding="utf-8")
    regla = _regla(css, ".ventana-cuerpo:has(> .visor-marco)")
    assert "grid-template-rows: minmax(0, 1fr)" in regla   # una fila que ocupa todo el alto del cuerpo
    assert "align-content: stretch" in regla
    assert "height: 100%" in _regla(css, ".visor-marco")


def test_el_visor_es_una_ventana_alta_con_el_marco_dentro_del_cuerpo():
    html = (ESTATICOS / "perfil.html").read_text(encoding="utf-8")
    assert re.search(r'<dialog id="visor" class="ventana alta"', html)
    assert '<div id="visor-cuerpo" class="ventana-cuerpo">' in html
    js = (ESTATICOS / "perfil.js").read_text(encoding="utf-8")
    assert 'nodo("iframe", null, "visor-marco")' in js
    # hijo directo: lo que pide `:has(> .visor-marco)`
    assert '$("visor-cuerpo").replaceChildren(marco)' in js
