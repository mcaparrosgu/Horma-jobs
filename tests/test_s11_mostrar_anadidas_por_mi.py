"""Spec 011 · T08p · «Mostrar» en Ofertas tiene «Añadidas por mí» (RF-11.31, D-033): las que la usuaria añadió
por URL o por texto, con candidatura o sin ella; las descartadas siguen solo en «Descartadas».
Ejecuta en node las funciones reales de `ofertas.js`."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"


def _fn(src: str, nombre: str) -> str:
    m = re.search(rf"function {nombre}\(.*?\n\}}", src, re.S)
    assert m, f"falta la función {nombre}"
    return m.group(0)


def _node(codigo: str):
    node = shutil.which("node")
    if not node:
        pytest.skip("node no disponible")
    return json.loads(subprocess.run([node, "-e", codigo], capture_output=True, text=True, check=True).stdout)


OFERTAS = """
const todas = [
  { id: 1, nota: 80 },                                        // catálogo, nueva
  { id: 2, nota: 70, propia: true },                          // mía, nueva
  { id: 3, nota: 60, propia: true, candidatura: { id: 9 } },  // mía, con candidatura
  { id: 4, nota: 50, propia: true, descartada: true },        // mía, descartada
  { id: 5, nota: 90, candidatura: { id: 8 } },                // catálogo, con candidatura
  { id: 6, nota: 30, descartada: true },                      // catálogo, descartada
];
"""


def test_anadidas_por_mi_son_las_suyas_menos_las_descartadas():
    src = (ESTATICOS / "ofertas.js").read_text(encoding="utf-8")
    codigo = OFERTAS + _fn(src, "estadoDe") + _fn(src, "enVista") + """
let vista = { estado: "nuevas" };
const ids = (cual) => todas.filter((o) => enVista(o, cual)).map((o) => o.id);
vista = { estado: "propias" };
const porDefecto = todas.filter((o) => enVista(o)).map((o) => o.id);
console.log(JSON.stringify({ propias: ids("propias"), porDefecto,
  nuevas: ids("nuevas"), candidatura: ids("candidatura"), descartadas: ids("descartadas") }));"""
    s = _node(codigo)
    assert s["propias"] == [2, 3]
    assert s["porDefecto"] == [2, 3]          # sin segundo argumento, la de la vista
    # los estados no cambian
    assert s["nuevas"] == [1, 2] and s["candidatura"] == [3, 5] and s["descartadas"] == [4, 6]


def test_la_opcion_sale_en_mostrar_con_su_numero_y_la_lista_usa_el_mismo_filtro():
    src = (ESTATICOS / "ofertas.js").read_text(encoding="utf-8")
    assert '["propias", "Añadidas por mí"]' in src
    estados = re.search(r"const ESTADOS_VISTA = (\[.*?\]);", src, re.S).group(1)
    assert estados.index('"descartadas"') < estados.index('"propias"')   # la última: no es un estado
    pintar = _fn(src, "pintarVista")
    assert "enVista(o, valor)" in pintar                                   # su número, con el mismo filtro
    lista = _fn(src, "pintarLista")
    assert "estadoDe(o) === vista.estado" not in lista and lista.count("enVista(o)") == 2
