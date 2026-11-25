"""Spec 011 (T08f) · la lectura de una oferta por URL se retoma al volver a Ofertas.
Ejecuta en node el código real de `ofertas.js` (submit de «Por URL», `esperarLectura`, `retomarLectura`) y la
`barraAvance` real de `comun.js`, con un DOM, un `sessionStorage` y una `api` de mentira."""
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
global.window = { matchMedia: () => ({ matches: true }) };
function el() { return { hijos: [], attrs: {}, style: {}, isConnected: true,
  textContent: "", className: "", value: "",
  disabled: false, open: false, hidden: false, oyentes: {},
  classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
  append(...h) {   // como el DOM real, mover un nodo lo saca de su padre anterior
    for (const n of h) { if (n.padre) n.padre.hijos = n.padre.hijos.filter((x) => x !== n); n.padre = this; }
    this.hijos.push(...h);
  }, remove() { this.isConnected = false; },
  contains(n) { return this.hijos.includes(n); }, replaceChildren() { this.hijos = []; },
  setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute() {},
  addEventListener(n, f) { this.oyentes[n] = f; }, close() { this.open = false; } }; }
global.nodo = () => el();
const dom = {};
global.$ = (id) => (dom[id] = dom[id] || el());
const eventos = [];
global.avisarUrl = (t, e) => { eventos.push(["avisarUrl", t]); };
global.avisar = (t, e) => { eventos.push(["avisar", t]); };
global.abrirAnadir = () => { dom["ventana-anadir"].open = true; eventos.push(["abrirAnadir"]); };
global.elegirPestanaAnadir = (c) => eventos.push(["pestana", c]);
global.seguirAnadida = (id) => eventos.push(["seguir", id]);
global.cargarLista = async () => eventos.push(["lista"]);
global.TEXTOS = { anadirUrlFallida: "FALLIDA" };
const sondeos = [];
const respuestas = [];
global.api = async (ruta, op) => {
  sondeos.push(ruta);
  if (op && op.metodo === "POST") return { ok: true, datos: { id: 7 } };
  return respuestas.shift();
};
global.setTimeout = () => 0;

const ini = comun.indexOf("const AVANCE_TICK_MS");
const fin = comun.indexOf("// Sigue una tarea del servidor");
eval(comun.slice(ini, fin) + "; global.barraAvance = barraAvance;"
  + " global.DURACION_TIPICA_S = DURACION_TIPICA_S;");
global.lecturaBarra = null;
global.lote = new Map();
global.barraAnadidas = null;
global.SONDEO_MS = 3000;
global.CLAVE_LECTURA = (ofertas.match(/const CLAVE_LECTURA = "([^"]+)"/) || [])[1];
const a = ofertas.indexOf("function terminarLectura");
const b = ofertas.indexOf("(async () => {\n  if (!(await arrancar");
if (a < 0 || b < 0) throw new Error("no se encuentra el corte");
const tipo = "typeof retomarLectura === 'function' ? retomarLectura : null";
eval(ofertas.slice(a, b) + `; global.retomar = ${tipo};`);

const barra = () => {
  const h = dom.avance ? dom.avance.hijos : [];
  return h.length ? h[h.length - 1] : null;
};
const salida = {};
(async () => {
  if (escenario === "enviar") {
    dom.url = el(); dom.url.value = "https://x.es/o";
    respuestas.push({ ok: true, datos: { estado: "pendiente" } });
    await dom["formulario-url"].oyentes.submit({ preventDefault() {} });
    salida.clave = almacen.get("horma:lectura-url") ?? null;
  } else if (escenario === "cerrar") {
    dom.url = el(); dom.url.value = "https://x.es/o";
    respuestas.push({ ok: true, datos: { estado: "pendiente" } });
    await dom["formulario-url"].oyentes.submit({ preventDefault() {} });
    const caja = dom["lectura-url"].hijos[0];
    salida.dentroAntes = dom["lectura-url"].hijos.includes(caja);
    dom["ventana-anadir"].oyentes.close();   // la ventana es modal: se cierra para ir a otra pantalla
    salida.dentro = dom["lectura-url"].hijos.includes(caja);
    salida.enPagina = dom.avance.hijos.includes(caja);
    salida.frase = caja.hijos[0].textContent;
    salida.clave = almacen.get("horma:avance:lectura:7") ?? null;
  } else {
    almacen.set("horma:lectura-url", "7");
    almacen.set("horma:avance:lectura:7", "27");
    dom["ventana-anadir"] = el();
    if (escenario === "leida") respuestas.push({ ok: true, datos: { estado: "leida", oferta_id: 42 } });
    else if (escenario === "error") respuestas.push({ ok: true, datos: { estado: "error" } });
    else respuestas.push({ ok: true, datos: { estado: "pendiente" } });
    if (!global.retomar) throw new Error("retomarLectura no existe");
    await global.retomar();
    salida.frase = barra() && barra().hijos[0].textContent;
    salida.botonDeshabilitado = dom["enviar-url"].disabled;
    salida.barraViva = !!(barra() && barra().isConnected);
    salida.clave = almacen.get("horma:lectura-url") ?? null;
    salida.avance = almacen.get("horma:avance:lectura:7") ?? null;
    salida.avisoTexto = dom["aviso-texto"] ? dom["aviso-texto"].textContent : null;
  }
  salida.sondeos = sondeos; salida.eventos = eventos;
  console.log(JSON.stringify(salida));
})().catch((e) => { console.error(e.stack); process.exit(1); });
"""


def _ejecutar(tmp_path, escenario):
    arnes = tmp_path / "arnes.js"
    arnes.write_text(HARNESS, encoding="utf-8")
    orden = ["node", str(arnes), str(ESTATICOS / "comun.js"), str(ESTATICOS / "ofertas.js"), escenario]
    r = subprocess.run(orden, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@node
def test_al_enviar_la_url_se_guarda_el_id_de_la_lectura(tmp_path):
    s = _ejecutar(tmp_path, "enviar")
    assert s["clave"] == "7"


@node
def test_en_pagina_nueva_se_retoma_la_barra_con_su_valor_guardado(tmp_path):
    s = _ejecutar(tmp_path, "pendiente")
    assert s["frase"].endswith("· 27 %")   # nunca baja (RF-10.8c)
    assert s["barraViva"] and s["botonDeshabilitado"]
    assert s["sondeos"] == ["/ofertas/url/7"]
    assert s["clave"] == "7"               # sigue pendiente: se conserva


@node
def test_la_lectura_retomada_que_termina_limpia_las_claves_y_sigue_la_oferta(tmp_path):
    s = _ejecutar(tmp_path, "leida")
    # la misma barra sigue con el análisis (T08l): sin las claves de la lectura, y sigue en pantalla
    assert s["clave"] is None and s["avance"] is None and s["barraViva"]
    assert ["seguir", 42] in s["eventos"] and not s["botonDeshabilitado"]


@node
def test_la_lectura_retomada_que_falla_avisa_en_la_pestana_de_texto(tmp_path):
    s = _ejecutar(tmp_path, "error")
    assert s["clave"] is None and s["avance"] is None and not s["barraViva"]
    assert s["avisoTexto"] == "FALLIDA"
    ev = s["eventos"]
    assert ["abrirAnadir"] in ev and ev.index(["abrirAnadir"]) < ev.index(["pestana", "texto"])


@node
def test_al_cerrar_la_ventana_con_una_lectura_en_marcha_la_barra_pasa_a_la_pagina(tmp_path):
    """M16: la ventana es modal; cerrada, la barra no se veía dentro de ella."""
    s = _ejecutar(tmp_path, "cerrar")
    assert s["dentroAntes"] is True
    assert s["enPagina"] is True and s["dentro"] is False
    assert "Analizando la oferta" in s["frase"] and "%" in s["frase"]
    assert s["clave"] is not None          # conserva su clave de avance
