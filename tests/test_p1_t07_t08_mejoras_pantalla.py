"""Paso 1 · T07-T08 (spec 011, parte 1, bloque M): botones de archivo, barras sin borde y barra de rango
(RF-11.26, RF-11.26c, RF-11.27). Estático y con node; lo visual va en la prueba de cierre (T09)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"


def leer(n):
    return (ESTATICOS / n).read_text(encoding="utf-8")


def _node(codigo: str):
    node = shutil.which("node")
    if not node:
        pytest.skip("node no disponible")
    salida = subprocess.run([node, "-e", codigo], capture_output=True, text=True, check=True).stdout
    return json.loads(salida)


def test_el_boton_de_archivo_principal_es_primario_y_el_otro_secundario():
    html = leer("perfil.html")
    principal = re.search(r'<span class="([^"]*)"[^>]*>Elegir archivos</span>', html).group(1)
    otro = re.search(r'<span class="([^"]*)"[^>]*>Subir archivos</span>', html).group(1)
    assert "secundario" not in principal and "secundario" in otro
    # «Subir mi CV» en Ofertas es también la acción principal de su pantalla: primario
    assert 'id="sin-perfil-boton" class="boton"' in leer("ofertas.html")


def test_ninguna_barra_lleva_borde_y_la_pista_se_ve_sola():
    css = leer("estilo.css")
    for regla in (".barra-compat{", ".barra-avance .pista{"):
        linea = next(x for x in css.splitlines() if x.startswith(regla))
        assert "outline" not in linea and "border" not in linea
    assert "--bar-track: #8f8f88" in leer("tokens.css")


def test_el_cuerpo_de_la_ventana_deja_sitio_al_resaltado_de_foco():
    css = leer("estilo.css")
    linea = next(x for x in css.splitlines() if x.startswith(".ventana-cuerpo{"))
    assert "padding: 5px" in linea and "margin: -5px" in linea  # 3 px de foco + 2 de separación


def test_ofertas_usa_una_sola_barra_de_rango_con_dos_tiradores_y_sus_numeros():
    html = leer("ofertas.html")
    assert 'id="nota-min" type="range"' in html and 'id="nota-max" type="range"' in html
    assert 'type="number"' not in html.split('id="vista"')[1].split("</form>")[0]
    assert html.count('class="rango-numero"') == 2
    assert 'aria-label="Compatibilidad mínima"' in html and 'aria-label="Compatibilidad máxima"' in html
    assert html.index("rango.js") < html.index("ofertas.js")


def test_la_zona_tactil_del_tirador_es_de_44_px():
    css = leer("estilo.css")
    assert css.count("width: var(--tap); height: var(--tap);") >= 2  # webkit y gecko


def test_el_minimo_no_pasa_del_maximo():
    codigo = leer("rango.js") + """
console.log(JSON.stringify([
  acotarRango(70, 40, "min"), acotarRango(70, 40, "max"), acotarRango(20, 80, "min"),
  acotarRango("", "x", "min"), acotarRango(-5, 250, "max")]));"""
    assert _node(codigo) == [{"min": 40, "max": 40}, {"min": 70, "max": 70}, {"min": 20, "max": 80},
                             {"min": 0, "max": 100}, {"min": 0, "max": 100}]


def test_el_filtro_con_la_barra_da_las_mismas_ofertas_que_las_dos_casillas():
    enrango = re.search(r"function enRango\(o\) \{.*?\n\}", leer("ofertas.js"), re.S).group(0)
    codigo = leer("rango.js") + enrango + """
const ofertas = [0, 10, 39, 40, 55, 70, 100].map((nota) => ({ nota }))
  .concat([{ propia: true, nota: 5 }, { sin_puntuar: true, nota: 0 }]);
let vista;
const con = (min, max) => { vista = { min, max }; return ofertas.filter(enRango).map((o) => o.nota); };
const casillas = con(40, 70);                          // lo que daban las dos casillas
vista = acotarRango("40", "70", "min");                // lo que da la barra con los mismos valores
console.log(JSON.stringify([casillas, ofertas.filter(enRango).map((o) => o.nota)]));"""
    casillas, barra = _node(codigo)
    assert casillas == barra == [40, 55, 70, 5, 0]
