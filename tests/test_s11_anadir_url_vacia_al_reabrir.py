"""Spec 011 · T08r · al volver a abrir «Añadir oferta», «Por URL» sale vacío y sin «Ya añadiste…»
(RF-11.29; tercera prueba de Mar: conservaba la dirección anterior). Con una lectura en marcha se queda
la dirección que se lee. Ejecuta en node el código real de `ofertas.js`."""
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
const textos = leer(process.argv[4]);

const almacen = new Map();
global.sessionStorage = { getItem: (k) => (almacen.has(k) ? almacen.get(k) : null),
  setItem: (k, v) => almacen.set(k, String(v)), removeItem: (k) => almacen.delete(k) };
global.window = { matchMedia: () => ({ matches: true }), addEventListener() {} };
global.location = { hash: "", pathname: "/ofertas", search: "" };
global.history = { replaceState() {} };
function el(etiqueta, texto, clase) { return { etiqueta, hijos: [], attrs: {}, style: {}, isConnected: true,
  textContent: texto ?? "", className: clase || "", value: "",
  disabled: false, open: false, hidden: false, oyentes: {},
  classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
  append(...h) {
    for (const n of h) { if (n.padre) n.padre.hijos = n.padre.hijos.filter((x) => x !== n); n.padre = this; }
    this.hijos.push(...h);
  }, remove() { this.isConnected = false; },
  contains(n) { return this.hijos.includes(n); },
  replaceChildren(...h) { this.hijos = []; if (h.length) this.append(...h); },
  setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute() {}, focus() {},
  addEventListener(n, f) { (this.oyentes[n] = this.oyentes[n] || []).push(f); },
  showModal() { this.open = true; },
  close() { this.open = false; for (const f of this.oyentes.close || []) f(); } }; }
global.nodo = (e, t, c) => el(e, t, c);
const dom = {};
global.$ = (id) => (dom[id] = dom[id] || el());
global.avisar = () => {};
global.verOriginal = () => {};
global.seguirAnadida = () => {};
global.cargarLista = async () => {};
eval(textos + "; global.TEXTOS = TEXTOS;");
const respuestas = [];
global.api = async (ruta, op) => (op && op.metodo === "POST" ? respuestas.shift()
  : { ok: true, datos: { estado: "pendiente" } });
global.setTimeout = () => 0;

const f0 = comun.indexOf("function fecha(valor)");
eval(comun.slice(f0, comun.indexOf("\n}\n", f0) + 3) + "; global.fecha = fecha;");
const ini = comun.indexOf("const AVANCE_TICK_MS");
const fin = comun.indexOf("// Sigue una tarea del servidor");
eval(comun.slice(ini, fin) + "; global.barraAvance = barraAvance;"
  + " global.DURACION_TIPICA_S = DURACION_TIPICA_S;");
// desde la sección «+ Añadir oferta» hasta el arranque de la pantalla: el código real, sin cortes a mano
const a = ofertas.indexOf("// --- «+ Añadir oferta»");
const b = ofertas.indexOf("(async () => {\n  if (!(await arrancar");
if (a < 0 || b < 0) throw new Error("no se encuentra el corte");
eval(ofertas.slice(a, b).split("\nlet ").join("\nvar ") + "; global.abrirAnadir = abrirAnadir;");

const estado = () => ({ url: dom.url.value, repetida: dom["repetida-url"].hijos.length,
  aviso: dom["aviso-url"].textContent, abierta: dom["ventana-anadir"].open });
const REPETIDA = { ok: true, datos: { repetida: true, oferta_id: 42, anadida_en: "2026-11-20T10:00:00Z" } };
const salida = {};
(async () => {
  abrirAnadir();
  dom.url.value = "https://lifeworq.com/es/job/1?utm_source=a";
  respuestas.push(REPETIDA);
  for (const f of dom["formulario-url"].oyentes.submit) await f({ preventDefault() {} });
  salida.repetida = estado();                       // «Ya añadiste…» con la dirección escrita
  dom["anadir-cerrar"].oyentes.click[0]();          // «Cerrar»
  dom["abrir-anadir"].oyentes.click[0]();           // «+ Añadir oferta» otra vez
  salida.reabierta = estado();

  // con una lectura en marcha, al reabrir se queda la dirección que se está leyendo
  dom.url.value = "https://empresa.es/oferta/9";
  respuestas.push({ ok: true, datos: { id: 7 } });
  for (const f of dom["formulario-url"].oyentes.submit) await f({ preventDefault() {} });
  dom["anadir-cerrar"].oyentes.click[0]();
  dom["abrir-anadir"].oyentes.click[0]();
  salida.leyendo = estado();
  console.log(JSON.stringify(salida));
})();
"""


@node
def test_al_reabrir_anadir_oferta_por_url_sale_vacio_y_sin_ya_anadiste(tmp_path):
    arnes = tmp_path / "arnes.js"
    arnes.write_text(HARNESS, encoding="utf-8")
    orden = ["node", str(arnes), str(ESTATICOS / "comun.js"), str(ESTATICOS / "ofertas.js"),
             str(ESTATICOS / "textos.js")]
    s = json.loads(subprocess.run(orden, capture_output=True, text=True, encoding="utf-8",
                                  check=True).stdout)
    assert s["repetida"]["repetida"] > 0 and s["repetida"]["url"]        # el aviso salió (T08k)
    assert s["reabierta"] == {"url": "", "repetida": 0, "aviso": "", "abierta": True}
    assert s["leyendo"]["url"] == "https://empresa.es/oferta/9"
    assert s["leyendo"]["aviso"] == "Leyendo la página…"
