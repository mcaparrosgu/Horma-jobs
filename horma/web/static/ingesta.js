// Dashboard de ingesta. Todo el texto que viene de la API se pinta con textContent: nunca como HTML.
const $ = (id) => document.getElementById(id);
let csrf = null;
let editando = null; // id de la fuente que se edita, o null si es nueva
let temporizador = null;
const pendientes = new Set(); // calificaciones que aún no han terminado

function nodo(etiqueta, texto, clase) {
  const el = document.createElement(etiqueta);
  if (texto !== undefined && texto !== null) el.textContent = texto;
  if (clase) el.className = clase;
  return el;
}

function boton(texto, accion, clase) {
  const b = nodo("button", texto, clase);
  b.type = "button";
  b.addEventListener("click", accion);
  return b;
}

function avisar(texto, error) {
  const a = $("aviso");
  a.className = error ? "error" : "";
  a.textContent = texto;
}

async function api(metodo, ruta, cuerpo) {
  const opciones = { method: metodo, headers: { "X-CSRF-Token": csrf } };
  if (cuerpo !== undefined) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(cuerpo);
  }
  const r = await fetch(ruta, opciones);
  let datos = null;
  if (r.status !== 204) datos = await r.json().catch(() => null);
  if (!r.ok) {
    const detalle = datos && datos.detail;
    throw new Error(typeof detalle === "string" ? detalle : `Error ${r.status}`);
  }
  return datos;
}

const fecha = (v) => (v ? new Date(v).toLocaleString("es-ES") : "—");

function textoEjecucion(c) {
  if (!c) return "Sin ejecuciones todavía.";
  const base = `Última ejecución: ${c.estado} · ${fecha(c.terminada_en || c.creada_en)}`;
  if (c.estado === "hecha" || c.estado === "error") {
    return `${base} · recibidas ${c.recibidas} · nuevas ${c.nuevas} · repetidas ${c.repetidas} · errores ${c.errores}`;
  }
  return base;
}

function tarjetaFuente(f) {
  const li = nodo("li", null, "tarjeta");
  li.append(nodo("span", f.activa ? "activa" : "inactiva", f.activa ? "estado" : "estado apagado"));
  li.append(nodo("h3", f.nombre));
  li.append(nodo("p", f.web, "suave"));
  const c = f.calificacion;
  if (c) {
    li.append(nodo("p", `Calificación: ${c.apta ? "APTA" : "NO APTA"} (${fecha(c.calificada_en)})`, c.apta ? null : "alerta"));
    for (const m of c.motivos || []) li.append(nodo("p", `· ${m}`, "suave"));
  } else {
    li.append(nodo("p", "Sin calificar: no se puede activar.", "suave"));
  }
  const ejecucion = f.ultima_ejecucion;
  li.append(nodo("p", textoEjecucion(ejecucion), ejecucion && ejecucion.estado === "error" ? "alerta" : null));
  if (ejecucion && ejecucion.motivo_error) li.append(nodo("p", ejecucion.motivo_error, "alerta"));

  const acciones = nodo("div", null, "fila");
  const limite = nodo("input");
  limite.type = "number";
  limite.min = "1";
  limite.max = "500";
  limite.value = "20";
  limite.className = "corto";
  limite.setAttribute("aria-label", `Límite de ofertas para ${f.nombre}`);
  const lanzar = boton("Lanzar ingesta", async () => {
    try {
      await api("POST", "/api/ingesta/ejecuciones", { fuente_id: f.id, limite: Number(limite.value) || 20 });
      avisar(`Ejecución pedida para ${f.nombre}. La ejecuta el ingestor.`);
      await cargar();
    } catch (e) {
      avisar(e.message, true);
    }
  });
  lanzar.disabled = !f.activa;
  acciones.append(limite, lanzar);
  acciones.append(boton("Editar", () => abrirEditor(f), "secundario"));
  acciones.append(boton("Calificar", () => calificar(f.web), "secundario"));
  li.append(acciones);
  return li;
}

function abrirEditor(f) {
  const form = $("form-fuente");
  editando = f ? f.id : null;
  form.nombre.value = f ? f.nombre : "";
  form.metodo.value = f ? f.metodo : "GET";
  form.web.value = f ? f.web : "";
  form.url.value = f ? f.url : "";
  form.variable_clave.value = f && f.variable_clave ? f.variable_clave : "";
  form.activa.checked = f ? f.activa : false;
  form.parametros.value = JSON.stringify(f ? f.parametros : {}, null, 2);
  form.cabeceras.value = JSON.stringify(f ? f.cabeceras : {}, null, 2);
  form.mapeo.value = JSON.stringify(f ? f.mapeo : { lista: "", id: "", titulo: "", descripcion: "" }, null, 2);
  $("editor").hidden = false;
  form.nombre.focus();
}

$("nueva-fuente").addEventListener("click", () => abrirEditor(null));
$("cancelar").addEventListener("click", () => {
  $("editor").hidden = true;
});

$("form-fuente").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  let cuerpo;
  try {
    cuerpo = {
      nombre: form.nombre.value.trim(),
      web: form.web.value.trim(),
      url: form.url.value.trim(),
      metodo: form.metodo.value,
      variable_clave: form.variable_clave.value.trim() || null,
      activa: form.activa.checked,
      parametros: JSON.parse(form.parametros.value || "{}"),
      cabeceras: JSON.parse(form.cabeceras.value || "{}"),
      mapeo: JSON.parse(form.mapeo.value || "{}"),
    };
  } catch {
    avisar("Parámetros, cabeceras y mapeo tienen que ser JSON válido.", true);
    return;
  }
  try {
    if (editando) await api("PUT", `/api/fuentes/${editando}`, cuerpo);
    else await api("POST", "/api/fuentes", cuerpo);
    $("editor").hidden = true;
    avisar("Fuente guardada.");
    await cargar();
  } catch (err) {
    avisar(err.message, true);
  }
});

async function calificar(url) {
  try {
    const r = await api("POST", "/api/fuentes/calificaciones", { url });
    pendientes.add(r.id);
    avisar(`Calificación de ${url} pedida; la hace el worker.`);
    await cargarCalificaciones();
    await cargar(); // arma el temporizador que refresca hasta que termine
  } catch (e) {
    avisar(e.message, true);
  }
}

$("form-calificar").addEventListener("submit", async (e) => {
  e.preventDefault();
  await calificar(e.target.url.value.trim());
  e.target.reset();
});

async function cargarCalificaciones() {
  const lista = $("calificaciones");
  const items = [];
  for (const id of [...pendientes]) {
    try {
      const c = await api("GET", `/api/fuentes/calificaciones/${id}`);
      if (c.estado !== "pendiente") pendientes.delete(id);
      const li = nodo("li", null, "tarjeta");
      const titulo = c.estado === "pendiente" ? "calificando…" : c.estado === "error" ? "error" : c.apta ? "APTA" : "NO APTA";
      li.append(nodo("span", titulo, c.apta ? "estado" : "estado error"));
      li.append(nodo("h3", c.url));
      for (const m of c.motivos || []) li.append(nodo("p", `· ${m}`, "suave"));
      if (c.motivo_error) li.append(nodo("p", c.motivo_error, "alerta"));
      if (c.instrucciones_embebidas && c.instrucciones_embebidas.length) {
        li.append(nodo("p", `Instrucciones detectadas y no ejecutadas: ${c.instrucciones_embebidas.length}`, "alerta"));
      }
      items.push(li);
    } catch {
      pendientes.delete(id);
    }
  }
  if (items.length) lista.replaceChildren(...items);
}

async function cargarClaves() {
  const claves = await api("GET", "/api/claves");
  $("claves").replaceChildren(
    ...claves.map((k) => {
      const li = nodo("li", null, "tarjeta");
      li.append(nodo("span", k.revocada_en ? "revocada" : k.alcance, k.revocada_en ? "estado apagado" : "estado"));
      li.append(nodo("h3", k.nombre));
      li.append(nodo("p", `${k.prefijo}… · creada ${fecha(k.creada_en)}`, "suave"));
      if (!k.revocada_en) {
        li.append(
          boton("Revocar", async () => {
            try {
              await api("DELETE", `/api/claves/${k.id}`);
              avisar("Clave revocada.");
              await cargarClaves();
            } catch (e) {
              avisar(e.message, true);
            }
          }, "secundario"),
        );
      }
      return li;
    }),
  );
}

$("form-clave").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const r = await api("POST", "/api/claves", { nombre: e.target.nombre.value.trim(), alcance: e.target.alcance.value });
    const aviso = $("clave-nueva");
    aviso.textContent = `Copia la clave ahora; no se volverá a enseñar: ${r.clave}`;
    aviso.hidden = false;
    e.target.reset();
    await cargarClaves();
  } catch (err) {
    avisar(err.message, true);
  }
});

async function cargar() {
  const r = await api("GET", "/api/ingesta/resumen");
  const estados = Object.entries(r.ofertas_por_estado);
  $("estados").replaceChildren(
    ...(estados.length ? estados.map(([e, n]) => nodo("li", `${e}: ${n}`, "chip")) : [nodo("li", "Sin ofertas todavía.", "chip")]),
  );
  $("fuentes").replaceChildren(...r.fuentes.map(tarjetaFuente));
  const errores = [
    ...r.errores.map((o) => [`Oferta ${o.id}${o.fuente ? ` (${o.fuente})` : ""}: ${o.titulo || "sin título"}`, o.motivo_error]),
    ...r.ejecuciones_con_error.map((c) => [`Ejecución ${c.id} de ${c.fuente}`, c.motivo_error]),
  ];
  $("errores").replaceChildren(
    ...errores.map(([titulo, motivo]) => {
      const li = nodo("li", null, "tarjeta");
      li.append(nodo("h3", titulo), nodo("p", motivo, "alerta"));
      return li;
    }),
  );
  $("sin-errores").hidden = errores.length > 0;
  clearTimeout(temporizador);
  const enMarcha = r.fuentes.some((f) => f.ultima_ejecucion && ["pendiente", "en_curso"].includes(f.ultima_ejecucion.estado));
  if (enMarcha || pendientes.size) {
    temporizador = setTimeout(async () => {
      await cargarCalificaciones();
      await cargar();
    }, 4000);
  }
}

async function iniciar() {
  const r = await fetch("/api/yo");
  if (!r.ok) {
    location.href = "/";
    return;
  }
  csrf = (await r.json()).csrf;
  try {
    await cargar();
    await cargarClaves();
  } catch (e) {
    avisar(e.message, true);
  }
}

iniciar();
