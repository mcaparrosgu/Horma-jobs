"""Simplificación S4 · T17: Perfil en una pantalla (RF-10.4, RF-10.5). La vista en el navegador, a 1280 y
390 px, se comprueba aparte."""
import re
from pathlib import Path

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
PROHIBIDAS = re.compile(r"\b(match|ATS|trazabilidad)\b", re.IGNORECASE)


def leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


def test_sin_perfil_solo_sube_tu_cv_y_con_perfil_salen_los_cinco_bloques_en_orden():
    html, js = leer("perfil.html"), leer("perfil.js")
    assert 'id="sube-cv"' in html and ">Sube tu CV<" in html
    pantalla = html.split('id="pantalla"')[1]
    orden = [pantalla.index(x) for x in ('id="mi-perfil"', 'id="maestro"', 'id="pendientes"',
                                         'id="cvs-subidos"', 'id="estilo"')]
    assert orden == sorted(orden)
    for titulo in ("Por resolver", "Tu perfil", "Tu CV completo", "Documentos subidos", "Cómo escribes"):
        assert titulo in html, titulo
    assert '$("pantalla").hidden = !perfil' in js and '$("sube-cv").hidden = !!perfil' in js
    assert not PROHIBIDAS.search(re.sub(r"<[^>]+>", " ", html))


def test_dos_columnas_a_1280_y_una_a_390():
    css = leer("estilo.css")
    assert ".pantalla-perfil{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr))" in css
    assert ".pantalla-perfil > .col-izq" in css and ".pantalla-perfil > .col-der" in css
    assert ".pantalla-perfil{ display: flex; flex-direction: column; }" in css.split("max-width: 900px")[1]


def test_columna_derecha_subir_archivo_primero_y_luego_cv_completo_documentos_y_como_escribes():
    html = leer("perfil.html")
    der = html.split('class="col-der"')[1]
    orden = [der.index(x) for x in ('id="subir-otro"', 'id="maestro"', 'id="pendientes"', 'id="cvs-subidos"', 'id="estilo"')]
    assert orden == sorted(orden) and ">Subir archivo<" in html
    assert 'id="subir-doc"' in der.split('id="maestro"')[0]


def test_por_resolver_junta_preguntas_huecos_y_avisos_con_dos_acciones():
    js = leer("perfil.js")
    assert "preguntas.map(pregunta)" in js and "items.map(avisoFila)" in js
    assert js.count('"Dar por visto"') == 2          # preguntas y avisos/huecos
    assert "Está bien así" not in js and "Está bien así" not in leer("perfil.html")
    html = leer("perfil.html")                       # RF-10.5c: «Avisos» desplegable dentro de «Por resolver»
    assert html.index('id="pendientes"') < html.index('id="avisos"') < html.index('id="lista-avisos"')
    for texto in ("Responder", "Añadir", "Corregir"):
        assert f'"{texto}"' in js, texto
    for ya_no in ("No lo sé / descartar", "Añadir en tu perfil", "t-avisos"):
        assert ya_no not in js and ya_no not in leer("perfil.html"), ya_no


def test_la_eleccion_de_longitud_esta_solo_en_el_aviso_de_cv_largo():
    js = leer("perfil.js")
    assert "maestro-longitud" not in js and "longitudElegida" not in js
    assert js.count('"Mantener la longitud"') == 1 and js.count("elegirLongitud(") == 2


def test_tu_cv_completo_tiene_ver_y_descargar_pdf_con_editar_por_seccion():
    html, js = leer("perfil.html"), leer("perfil.js")
    assert 'id="maestro-ver"' in html and ">Ver<" in html
    assert 'href="/api/perfil/cv.pdf"' in html and "Descargar PDF" in html
    assert "cvBonito(maestroActual)" in js and "irASeccion(clave)" in js and "innerHTML" not in js


def test_documentos_subidos_con_cv_y_carta_y_los_antiguos_como_documento():
    html, js = leer("perfil.html"), leer("perfil.js")
    assert '<option value="fuente" selected>CV</option>' in html
    assert '<option value="carta">Carta</option>' in html
    assert "estetico" not in html
    assert '$("clase-doc").value' in js and '{ carta: "Carta", fuente: "CV" }[c.clase] || "Documento"' in js
