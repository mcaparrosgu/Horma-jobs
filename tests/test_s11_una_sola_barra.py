"""Spec 011 (T08l, RF-11.30, D-031) · añadir una oferta enseña una sola barra «Analizando la oferta», de la
lectura de la página al análisis, sin cambiar de frase ni bajar. Ejecuta en node el código de `ofertas.js`."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
node = pytest.mark.skipif(shutil.which("node") is None, reason="necesita node")

HARNESS = r"""
const fs = require("fs");
const leer = (f) => fs.readFileSync(f, "utf8").split("\r\n").join("\n");
const comun = leer(process.argv[2]);
const ofertas = leer(process.argv[3]);
const escenario = process.argv[4];

const almacen = new Map();
global.sessionStorage = { getItem: (k) => (almacen.has(k) ? almacen.get(k) : null),
  setItem: (k, v) => almacen.set(k, String(v)), removeItem: (k) => almacen.delete(k) };
global.window = { matchMedia: () => ({ matches: true }), addEventListener() {} };
global.location = { hash: "" };
function el(etiqueta, texto, clase) { return { etiqueta, hijos: [], attrs: {}, style: {}, isConnected: true,
  textContent: texto ?? "", className: clase || "", value: "", disabled: false, open: false, hidden: false,
  oyentes: {}, classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
  append(...h) {
    for (const n of h) { if (n.padre) n.padre.hijos = n.padre.hijos.filter((x) => x !== n); n.padre = this; }
    this.hijos.push(...h);
  }, remove() { this.isConnected = false; },
  contains(n) { return this.hijos.includes(n); },
  replaceChildren(...h) { this.hijos = []; if (h.length) this.append(...h); },
  setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute() {}, focus() {}, showModal() {},
  addEventListener(n, f) { this.oyentes[n] = f; }, close() { this.open = false; } }; }
global.nodo = (e, t, c) => el(e, t, c);
const dom = {};
global.$ = (id) => (dom[id] = dom[id] || el());
global.avisar = () => {}; global.avisarUrl = () => {};
global.cargarLista = async () => {};
global.traerPuestosNuevos = async () => {};
global.todas = [];
global.TEXTOS = { anadirUrlFallida: "F" };
global.setTimeout = () => 0;
global.clearTimeout = () => {};
let progresoAnalisis = 0;
global.api = async (ruta, op) => {
  if (op && op.metodo === "POST") return { ok: true, datos: { id: 7 } };
  if (ruta === "/ofertas/url/7") {
    global.cajaAntes = dom["lectura-url"].hijos[0];
    global.getBarra().poner(15);
    return { ok: true, datos: { estado: "leida", oferta_id: 42 } };
  }
  if (ruta === "/api/ofertas/propias") {
    return { ok: true, datos: [{ id: 42, estado: "pendiente", progreso: progresoAnalisis }] };
  }
  return { ok: true, datos: { tareas: [] } };
};

const ini = comun.indexOf("const AVANCE_TICK_MS");
const fin = comun.indexOf("// Sigue una tarea del servidor");
eval(comun.slice(ini, fin) + "; global.barraAvance = barraAvance;");
const a = ofertas.indexOf("const SONDEO_MS");
const d = ofertas.indexOf("(async () => {\n  if (!(await arrancar");
if (a < 0 || d < 0) throw new Error("no se encuentra el corte");
eval(ofertas.slice(a, d) + "; global.getBarra = () => lecturaBarra; global.ver = { seguir: seguirAnadida };");

const vivas = () => dom.avance.hijos.filter((h) => h.isConnected);
const salida = {};
(async () => {
  if (escenario === "leida") {
    dom.url = dom.url || el();
    dom.url.value = "https://x.es/o";
    await dom["formulario-url"].oyentes.submit({ preventDefault() {} });
    await new Promise((r) => setImmediate(r));
    const cajas = vivas();
    salida.n = cajas.length;
    salida.misma = cajas[0] === global.cajaAntes;
    salida.frase = cajas[0].hijos[0].textContent;
    salida.claveLectura = almacen.get("horma:avance:lectura:7") ?? null;
    salida.claveUrl = almacen.get("horma:lectura-url") ?? null;
    salida.claveAnadida = almacen.get("horma:avance:anadidas:42") ?? null;
    salida.botonDeshabilitado = dom["enviar-url"].disabled;
  } else {   // oferta añadida por texto: una sola, sin barra previa
    global.ver.seguir(42);
    await new Promise((r) => setImmediate(r));
    salida.frase = vivas()[0].hijos[0].textContent;
  }
  console.log(JSON.stringify(salida));
})().catch((e) => { console.error(e.stack); process.exit(1); });
"""


def _ejecutar(tmp_path, escenario):
    arnes = tmp_path / "arnes.js"
    arnes.write_text(HARNESS, encoding="utf-8")
    orden = ["node", str(arnes), str(ESTATICOS / "comun.js"), str(ESTATICOS / "ofertas.js"), escenario]
    r = subprocess.run(orden, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@node
def test_de_la_lectura_al_analisis_hay_una_sola_barra_la_misma_y_no_baja(tmp_path):
    s = _ejecutar(tmp_path, "leida")
    assert s["n"] == 1 and s["misma"] is True
    assert s["frase"].startswith("Analizando la oferta · ") and "añadida" not in s["frase"]
    assert int(s["frase"].split("·")[1].strip().rstrip(" %")) >= 15   # el análisis aún en 0: no baja
    assert s["claveLectura"] is None and s["claveUrl"] is None and not s["botonDeshabilitado"]
    assert s["claveAnadida"] is not None   # sigue con la clave de las añadidas (se retoma al volver)


@node
def test_una_oferta_anadida_por_texto_dice_analizando_la_oferta(tmp_path):
    s = _ejecutar(tmp_path, "texto")
    assert s["frase"].startswith("Analizando la oferta · ") and "añadida" not in s["frase"]
