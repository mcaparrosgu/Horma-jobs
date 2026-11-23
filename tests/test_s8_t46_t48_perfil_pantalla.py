"""S8, T46-T48: Perfil sin versión, Formación con cursos, nombre, hueco, fechas, «Corregir» por experiencia,
Cómo escribes en listas y ayudas «?» (RF-10.14f a 10.14m). Estático: lee los HTML y JS."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"


def leer(n):
    return (ESTATICOS / n).read_text(encoding="utf-8")


def test_ninguna_pagina_pinta_la_version():
    for n in ("perfil.html", "perfil.js", "ofertas.html", "candidaturas.html", "candidatura.html"):
        assert not re.search(r"versi[oó]n \$\{|id=\"version\"|ya es la versión", leer(n)), n
    assert "Hecho: perfil actualizado." in leer("perfil.js")


def test_formacion_lleva_cursos_y_certificados_debajo_y_el_nombre_se_rotula():
    js = leer("perfil.js")
    assert '"Cursos y certificados"' in js and "formacion.append(bloque)" in js
    assert "Tu nombre (sale arriba en tus CV y cartas)" in js
    assert "¿Fue un empleo u otra cosa?" in leer("textos.js") and "preguntarTipoDeHueco" in js


def test_las_fechas_se_ven_y_se_escriben_como_mm_aaaa():
    js = leer("perfil.js") + leer("comun.js")
    assert "fechaVista" in js and "fechaGuardada" in js and "(MM-AAAA" in js
    node = shutil.which("node")
    if not node:
        pytest.skip("node no disponible")
    codigo = (leer("comun.js").split("// Fechas de un periodo")[1].split("function fecha(")[0]
              .split("\n", 1)[1])
    prueba = codigo + ("console.log(JSON.stringify([fechaVista('2021-03'), fechaVista('2021'), "
                       "fechaGuardada('03-2021'), fechaGuardada('2021'), fechaGuardada('actual')]));")
    salida = subprocess.run([node, "-e", prueba], capture_output=True, text=True, check=True).stdout
    assert salida.strip() == '["03-2021","2021","2021-03","2021","actual"]'


def test_sin_cifras_tiene_un_corregir_por_experiencia_y_ejemplos():
    js = leer("perfil.js")
    assert "corregirExperiencia(x.indice)" in js and "dataset.modificar" in js
    assert "mesas o cubiertos por servicio" in leer("textos.js")


def test_como_escribes_son_listas_y_la_ayuda_es_un_componente_comun():
    js, textos = leer("perfil.js"), leer("textos.js")
    assert 'nodo("ul"' in js and "Hecha por Horma" in js and "Editada por ti" in js
    assert "Aún no lo sabemos: sube una carta tuya." in textos
    assert "function ayuda(" in leer("comun.js") and "function ayuda(" not in leer("ofertas.js")
    for pagina in ("perfil", "ofertas", "candidaturas", "candidatura"):
        assert "data-explicacion=" in leer(f"{pagina}.html"), pagina
    assert "Horma escribe tus CV y cartas imitando cómo escribes." in textos
