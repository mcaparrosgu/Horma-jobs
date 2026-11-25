"""Spec 011 · T08g · la barra de avance nunca parece parada (RF-10.8c). Revisado en T08s (D-035): ya no
hay tope de «paso real + 20»; la barra se acerca al 95 % y, si el % no cambia en 3 s, el relleno late.
Ejecuta `barraAvance` real en node con un DOM de mentira y un reloj manual (un tick = 400 ms)."""
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
const reducir = process.argv[3] === "reducir";
const ini = src.indexOf("const AVANCE_TICK_MS");
const fin = src.indexOf("// Sigue una tarea del servidor");
const almacen = new Map();
global.sessionStorage = { getItem: (k) => (almacen.has(k) ? almacen.get(k) : null),
  setItem: (k, v) => almacen.set(k, String(v)), removeItem: (k) => almacen.delete(k) };
global.window = { matchMedia: () => ({ matches: reducir }) };
let relojes = [];
global.setInterval = (f) => { relojes.push(f); return relojes.length; };
global.clearInterval = () => {};
function el() { const cls = new Set();
  const e = { hijos: [], attrs: {}, style: {}, isConnected: true, textContent: "",
  classList: { add: (c) => cls.add(c), remove: (c) => cls.delete(c), contains: (c) => cls.has(c),
    toggle(c, f) {
      if (f === undefined ? !cls.has(c) : f) cls.add(c); else cls.delete(c);
      return cls.has(c);
    } },
  append(...h) { this.hijos.push(...h); }, remove() { this.isConnected = false; },
  setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute() {} }; return e; }
global.nodo = () => el();
eval(src.slice(ini, fin) + "; global.barraAvance = barraAvance;");
const pct = (b) => Number(/(\d+) %/.exec(b.caja.hijos[0].textContent)[1]);
const salida = { errores: [] };
function ticks(b, n, real, hist) {
  const f = relojes[relojes.length - 1];
  for (let i = 0; i < n; i++) {
    if (f) f();
    const v = pct(b);
    if (hist.length && v < hist[hist.length - 1]) salida.errores.push("baja " + v);
    if (v >= 100) salida.errores.push("100 antes de terminar");
    hist.push(v);
    const ult = hist.slice(-10);
    const cambio = ult.length < 10 || ult.some((x) => x !== ult[0]);
    if (!cambio && !b.caja.classList.contains("esperando")) {
      salida.errores.push("parada " + v + " tick " + hist.length);
    }
  }
}
const modo = process.argv[4];
if (modo === "perfil") {
  const hist = [];
  const a = barraAvance(el(), "x", false, 37); a.vincular("horma:avance:perfilar:5"); a.poner(0);
  ticks(a, 50, 0, hist);
  // se repinta la pantalla: otra barra con la misma clave sigue desde su punto; el paso real tarda 200 s
  const b = barraAvance(el(), "x", false, 37); b.vincular("horma:avance:perfilar:5"); b.poner(0);
  ticks(b, 500, 0, hist);
  salida.espera = b.caja.classList.contains("esperando");   // casi en el 95 %: el % apenas cambia y late
  salida.alFinal = pct(b);
  b.poner(96);
  salida.sinEspera = !b.caja.classList.contains("esperando");   // un paso real cambia el % y deja de latir
  ticks(b, 20, 96, []);
  salida.vuelveALatir = b.caja.classList.contains("esperando");
} else {
  const b = barraAvance(el(), "x"); b.vincular("k"); b.poner(0);
  salida.relojes = relojes.length;
  salida.espera = b.caja.classList.contains("esperando");
}
console.log(JSON.stringify(salida));
"""


def _correr(tmp_path, modo, reducir=False):
    arnes = tmp_path / "arnes.js"
    arnes.write_text(HARNESS, encoding="utf-8")
    orden = ["node", str(arnes), str(ESTATICOS / "comun.js"), "reducir" if reducir else "no", modo]
    r = subprocess.run(orden, capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


@node
def test_el_perfil_nunca_parece_parado_aunque_el_paso_real_tarde(tmp_path):
    s = _correr(tmp_path, "perfil")
    assert s["errores"] == []
    assert s["espera"] is True        # cerca del 95 %, sin cambiar el %, el relleno late
    assert 90 <= s["alFinal"] <= 95
    assert s["sinEspera"] is True     # un paso real que cambia el % quita el latido
    assert s["vuelveALatir"] is True


@node
def test_con_movimiento_reducido_no_hay_reloj_ni_latido(tmp_path):
    s = _correr(tmp_path, "reducido", reducir=True)
    assert s["relojes"] == 0
    assert s["espera"] is False
