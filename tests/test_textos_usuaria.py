"""Palabras de la usuaria (spec 010, RF-10.1c y RF-10.2): vocabulario único y menú de tres pestañas.
tres pestañas. El test es estático: lee los HTML y JS de las pantallas de la usuaria."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
# Pantallas de la usuaria. `cv-base.*` queda fuera: sigue accesible por URL, sin enlaces, hasta S2 (RF-10.3e).
PANTALLAS = ["index", "perfil", "ofertas", "candidaturas", "candidatura"]
ADMIN = ["ingesta", "costes", "catalogo"]

PROHIBIDAS = [
    (r"\bnotas?\b", "«nota»: se dice «compatibilidad» (RF-10.2b)"),
    (r"puntuaci[oó]n", "«puntuación»: se dice «compatibilidad» (RF-10.2b)"),
    (r"(?<![./\w])match(es)?\b(?!\()", "«match» (RF-10.2b)"),
    (r"\bCV base\b", "«CV base» (RF-10.2d)"),
    (r"\bCV maestro\b", "«CV maestro»: se dice «Tu CV completo» (RF-10.2d)"),
    (r"\bApify\b", "proveedor «Apify» (RF-10.2d)"),
    (r"\bauditor\b", "pieza interna «el auditor» (RF-10.2d)"),
    (r"tope de (coste|gasto)", "pieza interna «tope de coste» (RF-10.2d)"),
    (r"\bMar\b", "persona del equipo (RF-10.2d)"),
    (r"\bRecomendadas\b", "el nombre antiguo de Ofertas (RF-10.6)"),
    (r"\bATS\b", "«ATS» (RF-6.8)"),
]
HUECO = (r"\bhuecos?\b", "«hueco» solo nombra un periodo sin actividad (RF-10.2c)")


def _cadenas_js(codigo: str) -> list[str]:
    """Literales de cadena de un JS, sin comentarios, sin `${…}` y sin los que son identificadores o rutas."""
    codigo = re.sub(r"/\*.*?\*/", "", codigo, flags=re.S)
    codigo = re.sub(r"(?<![:\"'`\\])//[^\n]*", "", codigo)
    salida = []
    for m in re.finditer(r"\"((?:[^\"\\\n]|\\.)*)\"|'((?:[^'\\\n]|\\.)*)'|`((?:[^`\\]|\\.)*)`", codigo):
        texto = next(g for g in m.groups() if g is not None)
        texto = re.sub(r"\$\{[^}]*\}", " ", texto)
        if texto.startswith("/api/") or re.fullmatch(r"[A-Za-z0-9_\-/.#:?=&\[\]\"'>+~*, ()^$|\\{}]*", texto) and " " not in texto.strip():  # noqa: E501
            continue  # un identificador, una ruta o un selector: no es un texto que lea la usuaria
        salida.append(texto)
    return salida


def _textos_html(codigo: str) -> list[str]:
    codigo = re.sub(r"<script\b.*?</script>", "", codigo, flags=re.S)
    codigo = re.sub(r"<!--.*?-->", "", codigo, flags=re.S)
    atributos = re.findall(r"\b(?:aria-label|placeholder|title|alt)=\"([^\"]*)\"", codigo)
    return [re.sub(r"<[^>]+>", " ", codigo), *atributos]


def _textos(nombre: str) -> list[str]:
    salida = []
    html = ESTATICOS / f"{nombre}.html"
    if html.exists():
        salida += _textos_html(html.read_text(encoding="utf-8"))
    for js in (ESTATICOS / f"{nombre}.js",):
        if js.exists():
            salida += _cadenas_js(js.read_text(encoding="utf-8"))
    return salida


def test_hay_un_solo_archivo_de_textos_cargado_antes_que_comun():
    assert (ESTATICOS / "textos.js").exists()
    for nombre in PANTALLAS[1:] + ADMIN:
        html = (ESTATICOS / f"{nombre}.html").read_text(encoding="utf-8")
        assert "/static/textos.js" in html, f"{nombre}.html no carga textos.js"
        assert html.index("/static/textos.js") < html.index("/static/comun.js"), nombre


@pytest.mark.parametrize("nombre", PANTALLAS + ["comun"])
def test_ningun_texto_de_la_usuaria_usa_palabras_prohibidas(nombre):
    fallos = []
    for texto in _textos(nombre):
        for patron, motivo in PROHIBIDAS + ([] if nombre == "perfil" else [HUECO]):
            if re.search(patron, texto, flags=re.I if patron != r"\bMar\b" and patron != r"\bATS\b" else 0):
                fallos.append(f"{nombre}: {motivo} → {texto.strip()[:80]!r}")
    assert not fallos, "\n".join(fallos)


def test_textos_js_no_usa_palabras_prohibidas():
    fallos = [t for t in _cadenas_js((ESTATICOS / "textos.js").read_text(encoding="utf-8"))
              for patron, _ in PROHIBIDAS if re.search(patron, t, flags=re.I if patron not in (r"\bMar\b", r"\bATS\b") else 0)]  # noqa: E501
    assert not fallos, fallos


def test_el_menu_tiene_tres_pestanas_mas_admin():
    comun = (ESTATICOS / "comun.js").read_text(encoding="utf-8")
    bloque = re.search(r"const PESTANAS = \[(.*?)\];", comun, flags=re.S).group(1)
    assert re.findall(r'\["([^"]+)", "(/[^"]*)"\]', bloque) == [
        ("Ofertas", "/ofertas"), ("Candidaturas", "/candidaturas"), ("Perfil", "/perfil")]
    assert '"Admin"' in comun


def test_admin_no_copia_las_utilidades_de_comun():
    for nombre in ("ingesta", "costes"):
        js = (ESTATICOS / f"{nombre}.js").read_text(encoding="utf-8")
        for copia in (r"^const \$ =", r"^let csrf", r"^function nodo\(", r"^function avisar\(", r"^async function api\(",  # noqa: E501
                      r"^function fecha\(", r"/api/yo"):
            assert not re.search(copia, js, flags=re.M), f"{nombre}.js copia {copia}"
        html = (ESTATICOS / f"{nombre}.html").read_text(encoding="utf-8")
        assert "/static/comun.js" in html, nombre


def test_las_pantallas_antiguas_ya_no_existen_como_archivo():
    for viejo in ("recomendadas.html", "recomendadas.js", "anadir-oferta.html", "anadir-oferta.js", "entrar.html"):  # noqa: E501
        assert not (ESTATICOS / viejo).exists(), viejo


@pytest.mark.skipif(shutil.which("node") is None, reason="node no está instalado")
def test_estado_visible_da_los_seis_estados():
    guion = (
        "const fs=require('fs');"
        f"eval(fs.readFileSync({str(ESTATICOS / 'textos.js')!r},'utf8')+';globalThis.E=estadoVisible;');"
        "const r=[E('borrador','en_curso'),E('borrador','lista'),E('borrador','pendiente_de_ti'),"
        "E('aprobada','lista'),E('enviada','lista'),E('entrevista','lista'),E('cerrada','lista'),E('borrador','error')];"
        "console.log(JSON.stringify(r));"
    )
    salida = subprocess.run(["node", "-e", guion], capture_output=True, text=True, check=True).stdout
    assert salida.strip() == ('["Preparando","Por revisar","Por revisar","Lista para enviar","Enviada",'
                              '"Entrevista","Cerrada","No se pudo preparar"]')
