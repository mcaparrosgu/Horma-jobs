"""Spec 011 · «Añadir oferta»: aviso claro si la URL no se lee y seguimiento retomado al volver a Ofertas."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
node = pytest.mark.skipif(shutil.which("node") is None, reason="necesita node")


def _leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


def test_pestanas_por_url_y_por_texto():
    html = _leer("ofertas.html")
    assert ">Por URL</button>" in html and ">Por texto</button>" in html
    assert "Con una dirección" not in html and "Pegando el texto" not in html


def test_si_la_url_no_se_lee_el_aviso_sale_en_la_pestana_del_texto():
    textos, js = _leer("textos.js"), _leer("ofertas.js")
    assert "Estamos teniendo problemas para leer esa dirección. Mejor copia y pega aquí el texto" in textos
    inicio, fin = js.index("async function esperarLectura"), js.index('$("formulario-url").addEventListener')
    corte = js[inicio:fin]
    assert "TEXTOS.anadirUrlFallida" in corte and '$("aviso-texto")' in corte
    # el aviso se pinta con la pestaña ya a la vista
    assert corte.index('elegirPestanaAnadir("texto")') < corte.index("TEXTOS.anadirUrlFallida")


HARNESS = r"""
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8").split("\r\n").join("\n");
const ini = src.indexOf("function anadidasPorRetomar");
const fin = src.indexOf("\n}\n", ini) + 3;
eval(src.slice(ini, fin) + "; global.f = anadidasPorRetomar;");
const propias = [{ id: 1, estado: "pendiente" }, { id: 2, estado: "procesada" },
                 { id: 3, estado: "procesada" }, { id: 4, estado: "error" }, { id: 5, estado: "procesada" }];
const todas = [{ id: 3, sin_puntuar: false }, { id: 5, sin_puntuar: true }];
console.log(JSON.stringify({ puntuando: f(propias, todas, true), quieto: f(propias, todas, false) }));
"""


@node
def test_retoma_la_analizada_que_aun_no_esta_en_la_lista_mientras_se_puntua(tmp_path):
    arnes = tmp_path / "arnes.js"
    arnes.write_text(HARNESS, encoding="utf-8")
    r = subprocess.run(["node", str(arnes), str(ESTATICOS / "ofertas.js")],
                       capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)
    # pendiente, procesada sin fila aún y fila sin nota; no la 3 (ya en la lista) ni la 4 (error)
    assert s["puntuando"] == [1, 2, 5]
    # sin puntuación en marcha, la 2 es una oferta oculta por sus ajustes: se deja
    assert s["quieto"] == [1, 5]
