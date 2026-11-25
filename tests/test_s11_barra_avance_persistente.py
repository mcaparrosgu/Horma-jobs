"""Spec 011 · barra de avance: no retrocede al cambiar de pestaña (RF-10.8c).
Ejecuta `barraAvance` real en node con un DOM de mentira."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
node = pytest.mark.skipif(shutil.which("node") is None, reason="necesita node")

HARNESS = r"""
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const ini = src.indexOf("const AVANCE_TICK_MS");
const fin = src.indexOf("// Sigue una tarea del servidor");
const almacen = new Map();
global.sessionStorage = { getItem: (k) => (almacen.has(k) ? almacen.get(k) : null),
  setItem: (k, v) => almacen.set(k, String(v)), removeItem: (k) => almacen.delete(k) };
global.window = { matchMedia: () => ({ matches: true }) };   // sin reloj: el avance solo se simula a mano
function el() { const e = { hijos: [], attrs: {}, style: {}, isConnected: true, textContent: "",
  classList: { add() {} },
  append(...h) { this.hijos.push(...h); }, remove() { this.isConnected = false; },
  setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute() {} }; return e; }
global.nodo = () => el();
eval(src.slice(ini, fin) + "; global.barraAvance = barraAvance;");
const cont = el();
const salida = {};
const a = barraAvance(cont, "x");
a.vincular("perfilar:5");
a.poner(7); a.poner(3);
salida.a = a.caja.hijos[0].textContent;
const b = barraAvance(cont, "x");          // otra pestaña: empieza en 2 %
b.vincular("perfilar:5");                   // retoma el último valor mostrado
salida.b = b.caja.hijos[0].textContent;
b.poner(2);
salida.b2 = b.caja.hijos[0].textContent;    // nunca baja
b.quitar();
const c = barraAvance(cont, "x");
c.vincular("perfilar:5");
salida.c = c.caja.hijos[0].textContent;     // tarea terminada: la clave se borra
const d = barraAvance(cont, "x");
d.vincular("perfilar:6");
salida.d = d.caja.hijos[0].textContent;     // otra tarea: empieza de cero
console.log(JSON.stringify(salida));
"""


@node
def test_la_barra_retoma_el_ultimo_valor_al_volver_a_la_pantalla(tmp_path):
    arnes = tmp_path / "arnes.js"
    arnes.write_text(HARNESS, encoding="utf-8")
    r = subprocess.run(["node", str(arnes), str(ESTATICOS / "comun.js")],
                       capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)
    assert s["a"].endswith("· 7 %")
    assert s["b"].endswith("· 7 %")      # antes volvía al 2 %
    assert s["b2"].endswith("· 7 %")
    assert s["c"].endswith("· 2 %")
    assert s["d"].endswith("· 2 %")


def test_las_pantallas_vinculan_su_barra_a_su_tarea():
    perfil = (ESTATICOS / "perfil.js").read_text(encoding="utf-8")
    ofertas = (ESTATICOS / "ofertas.js").read_text(encoding="utf-8")
    assert "barraLectura.vincular(" in perfil
    assert "barra.vincular(" in ofertas or ".vincular(" in ofertas
