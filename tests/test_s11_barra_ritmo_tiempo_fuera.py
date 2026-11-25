"""Spec 011 · T08s · la barra de avance avanza según lo que suele tardar cada tarea y cuenta el tiempo que la
usuaria pasó en otra pestaña (RF-10.8c revisado, D-035). M17, tercera prueba de Mar: «subida muy lenta» (un CV
de 37 s llegaba a ~14 % y saltaba a 100 %) y, al volver de otra pestaña, parecía congelada (retomaba el valor
con el que se fue). Ejecuta `barraAvance` real en node con un reloj de mentira (un tick = 400 ms)."""
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
let ahora = 1_800_000_000_000;
Date.now = () => ahora;
let relojes = [];
global.setInterval = (f) => { relojes.push(f); return relojes.length; };
global.clearInterval = () => {};
function el() { const cls = new Set();
  return { hijos: [], attrs: {}, style: {}, isConnected: true, textContent: "",
  classList: { add: (c) => cls.add(c), remove: (c) => cls.delete(c), contains: (c) => cls.has(c),
    toggle(c, f) {
      if (f === undefined ? !cls.has(c) : f) cls.add(c); else cls.delete(c);
      return cls.has(c);
    } },
  append(...h) { this.hijos.push(...h); }, remove() { this.isConnected = false; },
  setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute() {} }; }
global.nodo = () => el();
eval(src.slice(ini, fin) + "; global.barraAvance = barraAvance;"
  + " global.DURACION_TIPICA_S = DURACION_TIPICA_S;");
const pct = (b) => Number(/(\d+) %/.exec(b.caja.hijos[0].textContent)[1]);
const errores = [];
function segundos(b, s, hist) {   // deja correr el reloj de la barra `s` segundos
  const f = relojes[relojes.length - 1];
  for (let i = 0; i < s * 1000 / 400; i++) {
    ahora += 400;
    if (f) f();
    const v = pct(b);
    if (hist.length && v < hist[hist.length - 1]) errores.push("baja " + v);
    if (v >= 100) errores.push("100 antes de terminar");
    hist.push(v);
    const ult = hist.slice(-10);
    if (ult.length === 10 && ult.every((x) => x === ult[0]) && !b.caja.classList.contains("esperando")) {
      errores.push("parada " + v);
    }
  }
}
const s = {};
const D = DURACION_TIPICA_S.perfil;
const modo = process.argv[4];
if (modo === "cv") {          // un CV: el servidor dice 0 % hasta el final (una sola llamada al modelo)
  const hist = [];
  const a = barraAvance(el(), "x", false, D); a.vincular("horma:avance:perfilar:5"); a.poner(0);
  segundos(a, D, hist);
  s.alTipico = pct(a);
  segundos(a, 2 * D, hist);       // tarda el triple de lo normal: sube poco a poco, sin llegar al 100
  s.alTriple = pct(a);
  a.poner(100);
  s.fin = pct(a);
} else if (modo === "fuera") {   // 10 s en Perfil, 20 s en Candidaturas, vuelta a Perfil
  const a = barraAvance(el(), "x", false, D); a.vincular("horma:avance:perfilar:6"); a.poner(0);
  segundos(a, 10, []);
  s.alIrse = pct(a);
  a.caja.remove();                // la página se va: su reloj ya no pinta
  ahora += 20000;
  const b = barraAvance(el(), "x", false, D); b.vincular("horma:avance:perfilar:6"); b.poner(0);
  s.alVolver = pct(b);
  const c = barraAvance(el(), "x", false, D); c.vincular("horma:avance:perfilar:7"); c.poner(0);
  segundos(c, 30, []);
  s.sinIrse = pct(c);             // la misma tarea, 30 s seguidos en la pantalla
} else if (modo === "paso") {    // un paso real la adelanta y sigue subiendo desde ahí
  const hist = [];
  const a = barraAvance(el(), "x", false, D); a.vincular("k"); a.poner(0);
  segundos(a, 3, hist);
  a.poner(70);
  s.trasPaso = pct(a);
  segundos(a, 10, hist);
  s.despues = pct(a);
} else if (modo === "antiguo") { // un valor guardado por la versión anterior (solo el número) se retoma
  almacen.set("horma:avance:lectura:7", "29.7");
  const b = barraAvance(el(), "x", false, DURACION_TIPICA_S.oferta);
  b.vincular("horma:avance:lectura:7"); b.poner(10);
  s.pct = pct(b);
} else {                          // movimiento reducido: sin reloj; no se inventa avance por el tiempo fuera
  const a = barraAvance(el(), "x", false, D); a.vincular("k"); a.poner(30);
  ahora += 60000;
  const b = barraAvance(el(), "x", false, D); b.vincular("k"); b.poner(30);
  s.relojes = relojes.length;
  s.pct = pct(b);
  s.espera = b.caja.classList.contains("esperando");
}
s.errores = errores;
console.log(JSON.stringify(s));
"""


def _correr(tmp_path, modo, reducir=False):
    arnes = tmp_path / "arnes.js"
    arnes.write_text(HARNESS, encoding="utf-8")
    orden = ["node", str(arnes), str(ESTATICOS / "comun.js"), "reducir" if reducir else "no", modo]
    return json.loads(subprocess.run(orden, capture_output=True, text=True, check=True).stdout)


@node
def test_un_cv_va_por_mas_de_la_mitad_a_su_duracion_tipica_y_nunca_parece_parado(tmp_path):
    s = _correr(tmp_path, "cv")
    assert s["errores"] == []
    assert 55 <= s["alTipico"] <= 65          # antes, ~14 %
    assert 85 <= s["alTriple"] <= 95          # sigue subiendo poco a poco y no llega al 100
    assert s["fin"] == 100


@node
def test_al_volver_de_otra_pestana_cuenta_el_tiempo_que_estuvo_fuera(tmp_path):
    s = _correr(tmp_path, "fuera")
    assert s["errores"] == []
    assert s["alVolver"] > s["alIrse"] + 10   # antes retomaba justo el valor con el que se fue
    assert abs(s["alVolver"] - s["sinIrse"]) <= 1


@node
def test_un_paso_real_la_adelanta_y_sigue_subiendo(tmp_path):
    s = _correr(tmp_path, "paso")
    assert s["errores"] == []
    assert s["trasPaso"] == 70
    assert s["despues"] > 70


@node
def test_un_valor_guardado_por_la_version_anterior_se_retoma(tmp_path):
    assert _correr(tmp_path, "antiguo")["pct"] >= 29


@node
def test_con_movimiento_reducido_no_hay_reloj_ni_avance_inventado(tmp_path):
    s = _correr(tmp_path, "reducido", reducir=True)
    assert s["relojes"] == 0
    assert s["pct"] == 30
    assert s["espera"] is False
