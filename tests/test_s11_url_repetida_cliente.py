"""Spec 011 (T08k, RF-11.29) · la pantalla ante una URL ya añadida: sin barra, «Ya añadiste esta oferta el …»
con «Ver oferta» y «Leer de nuevo» (que manda `releer: true`). Ejecuta en node el código de `ofertas.js`."""
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
const escenario = process.argv[5];

const almacen = new Map();
global.sessionStorage = { getItem: (k) => (almacen.has(k) ? almacen.get(k) : null),
  setItem: (k, v) => almacen.set(k, String(v)), removeItem: (k) => almacen.delete(k) };
global.window = { matchMedia: () => ({ matches: true }) };
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
  setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute() {},
  addEventListener(n, f) { this.oyentes[n] = f; }, close() { this.open = false; } }; }
global.nodo = (e, t, c) => el(e, t, c);
const dom = {};
global.$ = (id) => (dom[id] = dom[id] || el());
const eventos = [];
global.avisarUrl = (t, e) => { eventos.push(["avisarUrl", t]); };
global.avisar = (t, e) => { eventos.push(["avisar", t]); };
global.verOriginal = (id) => eventos.push(["verOriginal", id]);
global.seguirAnadida = (id) => eventos.push(["seguir", id]);
global.cargarLista = async () => {};
global.elegirPestanaAnadir = (c) => eventos.push(["pestana", c]);
global.abrirAnadir = () => {};
eval(textos + "; global.TEXTOS = TEXTOS;");
const cuerpos = [];
const respuestas = [];
global.api = async (ruta, op) => {
  if (op && op.metodo === "POST") { cuerpos.push(op.cuerpo); return respuestas.shift(); }
  return { ok: true, datos: { estado: "pendiente" } };
};
global.setTimeout = () => 0;

const f0 = comun.indexOf("function fecha(valor)");
eval(comun.slice(f0, comun.indexOf("\n}\n", f0) + 3) + "; global.fecha = fecha;");
const ini = comun.indexOf("const AVANCE_TICK_MS");
const fin = comun.indexOf("// Sigue una tarea del servidor");
eval(comun.slice(ini, fin) + "; global.barraAvance = barraAvance;"
  + " global.DURACION_TIPICA_S = DURACION_TIPICA_S;");
global.lecturaBarra = null;
global.SONDEO_MS = 3000;
global.CLAVE_LECTURA = (ofertas.match(/const CLAVE_LECTURA = "([^"]+)"/) || [])[1];
const a = ofertas.indexOf("function terminarLectura");
const b = ofertas.indexOf("(async () => {\n  if (!(await arrancar");
if (a < 0 || b < 0) throw new Error("no se encuentra el corte");
eval(ofertas.slice(a, b));

const REPETIDA = { ok: true, datos: { repetida: true, oferta_id: 42, anadida_en: "2026-11-20T10:00:00Z",
  titulo: "Camarera" } };
const salida = {};
(async () => {
  dom.url = dom.url || el();
  dom.url.value = "https://x.es/o?utm_source=a";
  respuestas.push(REPETIDA);
  await dom["formulario-url"].oyentes.submit({ preventDefault() {} });
  const caja = dom["repetida-url"];
  salida.barra = global.lecturaBarra;
  salida.lecturaVacia = dom["lectura-url"].hijos.length === 0;
  salida.clave = almacen.get("horma:lectura-url") ?? null;
  salida.botonDeshabilitado = dom["enviar-url"].disabled;
  salida.hijos = caja.hijos.map((h) => ({ e: h.etiqueta, t: h.textContent, c: h.className,
    h: h.hijos.map((x) => ({ e: x.etiqueta, t: x.textContent, c: x.className })) }));
  const fila = caja.hijos.find((h) => h.className === "fila");
  if (escenario === "ver") {
    fila.hijos[0].oyentes.click();
  } else if (escenario === "releer") {
    respuestas.push({ ok: true, datos: { id: 9, estado: "pendiente" } });
    await fila.hijos[1].oyentes.click();
    salida.clave = almacen.get("horma:lectura-url") ?? null;
    salida.tras = caja.hijos.length;
  } else if (escenario === "limpiar") {
    dom.url.oyentes.input();
    salida.tras = caja.hijos.length;
  }
  salida.cuerpos = cuerpos; salida.eventos = eventos;
  console.log(JSON.stringify(salida));
})().catch((e) => { console.error(e.stack); process.exit(1); });
"""


def _ejecutar(tmp_path, escenario):
    arnes = tmp_path / "arnes.js"
    arnes.write_text(HARNESS, encoding="utf-8")
    orden = ["node", str(arnes), str(ESTATICOS / "comun.js"), str(ESTATICOS / "ofertas.js"),
             str(ESTATICOS / "textos.js"), escenario]
    r = subprocess.run(orden, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@node
def test_una_url_repetida_no_deja_barra_ni_clave_y_avisa_con_la_fecha_y_dos_botones(tmp_path):
    s = _ejecutar(tmp_path, "base")
    assert s["barra"] is None and s["lecturaVacia"] and s["clave"] is None and not s["botonDeshabilitado"]
    texto, fila = s["hijos"]
    assert texto["t"].startswith("Ya añadiste esta oferta el ") and texto["t"].endswith("2026.")
    assert fila["c"] == "fila"
    assert [(b["e"], b["t"]) for b in fila["h"]] == [("button", "Ver oferta"), ("button", "Leer de nuevo")]
    assert all("secundario" in b["c"] for b in fila["h"])
    assert s["cuerpos"] == [{"url": "https://x.es/o?utm_source=a"}]


@node
def test_ver_oferta_abre_el_original(tmp_path):
    s = _ejecutar(tmp_path, "ver")
    assert ["verOriginal", 42] in s["eventos"]


@node
def test_leer_de_nuevo_manda_releer_true_y_sigue_el_flujo_normal(tmp_path):
    s = _ejecutar(tmp_path, "releer")
    assert s["cuerpos"][1] == {"url": "https://x.es/o?utm_source=a", "releer": True}
    assert s["clave"] == "9" and s["tras"] == 0   # barra y clave de la nueva lectura; el aviso se quita


@node
def test_al_cambiar_la_url_el_aviso_se_limpia(tmp_path):
    s = _ejecutar(tmp_path, "limpiar")
    assert s["tras"] == 0
