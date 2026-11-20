// Pantalla de costes. Todo lo que viene de la API se pinta con textContent: nunca como HTML.
const $ = (id) => document.getElementById(id);

function nodo(etiqueta, texto, clase) {
  const el = document.createElement(etiqueta);
  if (texto !== undefined && texto !== null) el.textContent = texto;
  if (clase) el.className = clase;
  return el;
}

const usd = (n) => `${Number(n).toFixed(4)} USD`;
const porcentaje = (n) => `${(Number(n) * 100).toFixed(1)} %`;
const entero = (n) => Number(n).toLocaleString("es-ES");

function tabla(id, columnas, filas) {
  const t = $(id);
  t.replaceChildren();
  const cabecera = nodo("tr");
  columnas.forEach((c) => cabecera.append(nodo("th", c.titulo)));
  const encabezado = nodo("thead");
  encabezado.append(cabecera);
  t.append(encabezado);
  const cuerpo = nodo("tbody");
  filas.forEach((f) => {
    const tr = nodo("tr");
    columnas.forEach((c) => tr.append(nodo("td", c.formato ? c.formato(f[c.clave]) : f[c.clave])));
    cuerpo.append(tr);
  });
  if (!filas.length) {
    const tr = nodo("tr");
    const td = nodo("td", "Sin llamadas en este periodo.");
    td.colSpan = columnas.length;
    tr.append(td);
    cuerpo.append(tr);
  }
  t.append(cuerpo);
}

const CIFRAS = [
  { titulo: "Llamadas", clave: "llamadas", formato: entero },
  { titulo: "Coste", clave: "coste", formato: usd },
  { titulo: "Tokens ent.", clave: "tokens_entrada", formato: entero },
  { titulo: "Tokens sal.", clave: "tokens_salida", formato: entero },
  { titulo: "Latencia media", clave: "latencia_media_ms", formato: (n) => `${entero(n)} ms` },
  { titulo: "Errores", clave: "tasa_errores", formato: porcentaje },
];

const NOMBRE_ALERTA = { gasto_dia: "Gasto del día", tasa_errores: "Tasa de errores" };

function pintar(r) {
  tabla("dias", [{ titulo: "Día", clave: "dia" }, ...CIFRAS], r.dias);
  tabla("agentes", [{ titulo: "Agente", clave: "agente" }, ...CIFRAS], r.agentes);
  tabla("modelos", [{ titulo: "Modelo", clave: "modelo" }, ...CIFRAS], r.modelos);

  const alertas = $("alertas");
  alertas.replaceChildren();
  r.alertas.forEach((a) => {
    const esGasto = a.tipo === "gasto_dia";
    const valor = esGasto ? usd(a.valor) : porcentaje(a.valor);
    const umbral = esGasto ? usd(a.umbral) : porcentaje(a.umbral);
    const fecha = new Date(a.creada_en).toLocaleString("es-ES");
    const li = nodo("li", `${NOMBRE_ALERTA[a.tipo] || a.tipo}: ${valor} (umbral ${umbral}) · ${fecha}` +
      (a.correo_enviado ? " · correo enviado" : " · sin correo"), "tarjeta alerta");
    alertas.append(li);
  });
  $("sin-alertas").hidden = r.alertas.length > 0;

  const tareas = $("tareas");
  tareas.replaceChildren();
  r.tareas_en_error.forEach((t) => tareas.append(nodo("li", `${t.tipo}: ${t.n}`, "chip")));
  $("sin-tareas").hidden = r.tareas_en_error.length > 0;
}

async function cargar() {
  const sesion = await fetch("/api/yo");
  if (sesion.status === 401) { location.href = "/"; return; }
  const csrf = (await sesion.json()).csrf;
  $("salir").addEventListener("click", async () => {
    await fetch("/auth/logout", { method: "POST", headers: { "X-CSRF-Token": csrf } });
    location.href = "/";
  });
  const r = await fetch("/api/costes");
  if (!r.ok) {
    $("aviso").className = "error";
    $("aviso").textContent = r.status === 403 ? "Solo para administradoras." : `Error ${r.status}`;
    return;
  }
  pintar(await r.json());
}

cargar();
