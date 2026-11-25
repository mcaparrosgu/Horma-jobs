"""S8 · T65: la barra «Estamos leyendo tu CV» no parpadea y Perfil no enseña «Sube tu CV» antes de cargar
(RF-10.8c, RF-10.14n). Comprobación estática; la visual va en la prueba de cierre (T50)."""
import re
from pathlib import Path

ESTATICOS = Path("horma/web/static")


def _leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


def test_sube_tu_cv_nace_oculto_y_solo_se_pinta_tras_la_respuesta():
    html = _leer("perfil.html")
    assert re.search(r'<section id="sube-cv"[^>]*\shidden\b', html)
    js = _leer("perfil.js")
    # el estado vacío se decide después de `await api("/api/perfil")`
    assert js.index('await api("/api/perfil")') < js.index('$("sube-cv").hidden = !!perfil')


def test_la_barra_se_crea_una_vez_y_no_se_vacia_el_contenedor_mientras_dura():
    js = _leer("perfil.js")
    assert js.count('barraAvance(estado, rehaciendo ? TEXTOS.actualizandoPerfil : "Estamos leyendo tu CV")') == 1  # noqa: E501
    # no se vacía todo el contenedor de golpe: había un `await` entre vaciar y recolocar la barra
    assert 'const estado = $("estado-perfil");\n  estado.replaceChildren();' not in js
    assert "barraLectura.caja.parentNode !== estado" in js
