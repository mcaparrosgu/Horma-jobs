"""Spec 011 · «Añadir oferta»: un solo botón «Añadir oferta» a la vista, con dos pestañas."""
import re
from pathlib import Path

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"


def _leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


def test_la_ventana_tiene_dos_pestanas_y_ningun_boton_leer_oferta():
    html = _leer("ofertas.html")
    ventana = html[html.index('<dialog id="ventana-anadir"'):html.index("</dialog>")]
    assert "Leer oferta" not in ventana
    assert 'role="tablist"' in ventana and ventana.count('role="tab"') == 2
    assert "Con una dirección" in ventana and "Pegando el texto" in ventana
    # uno por formulario, nunca los dos a la vez
    assert len(re.findall(r">Añadir oferta</button>", ventana)) == 2
    # el formulario del texto nace oculto: se ve la dirección
    assert re.search(r'<form id="formulario-texto"[^>]*\shidden\b', ventana)


def test_el_js_cambia_de_pestana_y_pone_el_foco_en_su_campo():
    js = _leer("ofertas.js")
    assert "function elegirPestanaAnadir" in js and "aria-selected" in js
    # un fallo al leer la dirección lleva a pegar el texto
    assert 'elegirPestanaAnadir("texto")' in js
