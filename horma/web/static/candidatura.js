// Pantalla de una candidatura (RF-3.8 a RF-3.10): CV y carta para revisar, editar y aprobar; después, el
// seguimiento. Todo texto (incluido el que escribió el modelo) se pinta con textContent.
const ID = Number(location.pathname.split("/").pop());
const CANALES = [["correo", "Correo"], ["web", "Web de la empresa"], ["linkedin", "LinkedIn"], ["otro", "Otro"]];
const MOTIVOS = [["rechazo", "Rechazo"], ["descartada", "La descarto yo"], ["retirada", "La retiro"]];
const ESTADOS = { borrador: "Borrador", aprobada: "Aprobada", enviada: "Enviada", entrevista: "Entrevista", cerrada: "Cerrada" };
const ETIQUETAS_RESPUESTA = { entrevista: "una entrevista", rechazo: "un rechazo", piden_informacion: "que piden más información", otro: "otra cosa" };
let c = null;
let temporizador = null;
let cvEditado = false;   // tras editar el CV se ofrece «Guardar como mi CV base»

function boton(texto, alClic, clase) {
  const b = nodo("button", texto, clase);
  b.type = "button";
  b.addEventListener("click", alClic);
  return b;
}

function selector(opciones, etiquetaCampo) {
  const s = nodo("select");
  for (const [valor, texto] of opciones) {
    const o = nodo("option", texto);
    o.value = valor;
    s.append(o);
  }
  return campo(etiquetaCampo, s);
}

async function accion(ruta, cuerpo, ok) {
  const r = await api(ruta, { metodo: "POST", cuerpo: cuerpo || {} });
  if (!r.ok) return avisar(r.motivo, true);
  avisar(ok || "Hecho.");
  await cargar();
}

// --- cabecera y qué CV base eligió Horma -------------------------------------------------------
function cabecera() {
  const s = nodo("section");
  s.append(nodo("h2", c.oferta.titulo || "Oferta sin título"));
  s.append(nodo("p", c.oferta.empresa || "Empresa sin indicar", "suave"));
  s.append(nodo("span", ESTADOS[c.estado] || c.estado, "estado bien"));
  if (c.estado === "cerrada" && c.motivo_cierre) s.append(nodo("span", `Motivo: ${c.motivo_cierre}`, "estado apagado"));
  if (c.cv_base) {
    const p = nodo("p", `CV base elegido: «${c.cv_base.nombre}».`);
    if (c.cv_base_motivo) p.append(" " + c.cv_base_motivo);
    s.append(p);
  }
  if (c.cobertura_ats !== null && c.cobertura_ats !== undefined) {
    s.append(nodo("p", `Palabras de la oferta que aparecen en el CV: ${Math.round(Number(c.cobertura_ats) * 100)} %`, "suave"));
  }
  return s;
}

// --- huecos y avisos ---------------------------------------------------------------------------
function huecosYAvisos() {
  const s = nodo("section");
  if (c.huecos.length) {
    s.append(nodo("h3", "Huecos: lo que pide la oferta y no está en tu CV", "subtitulo"));
    const ul = nodo("ul", null, "lista");
    for (const h of c.huecos) {
      const li = nodo("li", null, "tarjeta");
      li.append(nodo("strong", h.requisito));
      if (h.propuesta) li.append(nodo("p", `Propuesta: ${h.propuesta}`, "suave"));
      ul.append(li);
    }
    s.append(ul);
  }
  if (c.avisos.length) {
    s.append(nodo("h3", "Avisos: revísalos antes de aprobar", "subtitulo"));
    const ul = nodo("ul", null, "lista");
    for (const a of c.avisos) ul.append(nodo("li", a, "tarjeta alerta"));
    s.append(ul);
  } else if (c.preparacion === "pendiente_de_ti") {
    s.append(nodo("p", "Horma no pudo cerrar algo por su cuenta: revisa el CV y la carta con cuidado.", "alerta"));
  }
  return s;
}

// --- documentos (CV y carta) --------------------------------------------------------------------
function documento(titulo, clave, extra) {
  const s = nodo("section");
  s.append(nodo("h3", titulo, "subtitulo"));
  const hoja = cvBonito(c[clave]);
  s.append(hoja);
  if (c.estado === "borrador" && c.preparacion !== "en_curso") {
    const acciones = nodo("div", null, "fila");
    const editar = boton("Editar", () => {
      acciones.hidden = true;
      hoja.hidden = true;
      const f = nodo("form", null, "editor");
      const t = nodo("textarea");
      t.rows = 18;
      t.required = true;
      t.maxLength = 20000;
      t.value = c[clave];
      t.setAttribute("aria-label", `Texto de ${titulo}`);
      const cancelar = boton("Cancelar", () => { f.remove(); hoja.hidden = false; acciones.hidden = false; }, "secundario");
      const fila = nodo("div", null, "fila");
      fila.append(nodo("button", "Guardar"), cancelar);
      f.append(t, nodo("p", "Lo que escribas es tuyo: Horma lo vuelve a comprobar y lo que no esté en tu CV saldrá como aviso.", "suave"), fila);
      f.addEventListener("submit", async (e) => {
        e.preventDefault();
        const r = await api(`/api/candidaturas/${ID}`, { metodo: "PATCH", cuerpo: { [clave]: t.value } });
        if (!r.ok) return avisar(r.motivo, true);
        if (clave === "cv_contenido") cvEditado = true;
        avisar("Guardado.");
        await cargar();
      });
      s.append(f);
      t.focus();
    }, "secundario");
    acciones.append(editar);
    s.append(acciones);
  }
  if (extra) s.append(extra);
  return s;
}

// Tras editar el CV: guardarlo encima del CV base (RF-3.8). La versión anterior queda en el historial.
function guardarComoBase() {
  if (!(cvEditado && c.estado === "borrador" && c.cv_base)) return null;
  const f = nodo("form", null, "editor tarjeta");
  const i = nodo("input");
  i.type = "text";
  i.maxLength = 80;
  i.required = true;
  i.value = c.cv_base.nombre;
  f.append(campo("Nombre del CV base", i));
  f.append(nodo("p", "La versión anterior queda en el historial de ese CV base, en la pantalla «CV base».", "suave"));
  f.append(nodo("button", "Guardar como mi CV base"));
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const r = await api(`/api/candidaturas/${ID}/guardar-cv-base`, { metodo: "POST", cuerpo: { nombre: i.value } });
    if (!r.ok) return avisar(r.motivo, true);
    cvEditado = false;
    avisar("Guardado como tu CV base.");
    await cargar();
  });
  return f;
}

// --- botones según el estado --------------------------------------------------------------------
async function cargarEsteticos(select) {
  const r = await api("/api/cv");
  if (!r.ok) {
    avisar(r.motivo, true);
    return 0;
  }
  const esteticos = r.datos.filter((x) => x.clase === "estetico");
  select.replaceChildren(...esteticos.map((x) => {
    const o = nodo("option", x.nombre);
    o.value = x.id;
    return o;
  }));
  return esteticos.length;
}

function aprobar() {
  const s = nodo("section", null, "tarjeta");
  s.append(nodo("h3", "Aprobar", "subtitulo"));
  const hayAvisos = c.avisos.length > 0 || c.preparacion === "pendiente_de_ti";
  const revisados = nodo("input");
  revisados.type = "checkbox";
  const casilla = nodo("label", null, "casilla");
  casilla.append(revisados, nodo("span", "He revisado los avisos"));
  const adaptado = nodo("input");
  const estetico = nodo("input");
  for (const [inp, valor] of [[adaptado, "adaptado"], [estetico, "estetico"]]) {
    inp.type = "radio";
    inp.name = "documento";
    inp.value = valor;
  }
  adaptado.checked = true;
  const la = nodo("label", null, "casilla");
  const le = nodo("label", null, "casilla");
  la.append(adaptado, nodo("span", "CV adaptado por Horma (PDF sencillo, compatible con ATS)"));
  le.append(estetico, nodo("span", "Mi CV estético, tal cual lo subí"));
  const lista = nodo("select");
  lista.hidden = true;
  lista.setAttribute("aria-label", "CV estético");
  estetico.addEventListener("change", async () => {
    lista.hidden = false;
    if (!(await cargarEsteticos(lista))) avisar("No tienes ningún CV estético subido.", true);
  });
  adaptado.addEventListener("change", () => { lista.hidden = true; });
  const ok = nodo("button", "Aprobar candidatura");
  ok.type = "button";
  ok.disabled = hayAvisos;   // con avisos, el botón espera a la casilla
  revisados.addEventListener("change", () => { ok.disabled = hayAvisos && !revisados.checked; });
  ok.addEventListener("click", () => accion(`/api/candidaturas/${ID}/aprobar`, {
    documento: estetico.checked ? "estetico" : "adaptado",
    cv_estetico_id: estetico.checked && lista.value ? Number(lista.value) : null,
    avisos_revisados: revisados.checked,
  }, "Candidatura aprobada."));
  const fila = nodo("div", null, "fila");
  fila.append(ok);
  s.append(...(hayAvisos ? [casilla] : []), la, le, lista, fila);
  return s;
}

function descargas() {
  const s = nodo("div", null, "fila");
  for (const [texto, ruta] of [["Descargar CV (PDF)", "cv.pdf"], ["Descargar carta (PDF)", "carta.pdf"]]) {
    const a = nodo("a", texto, "boton");
    a.href = `/api/candidaturas/${ID}/${ruta}`;
    s.append(a);
  }
  return s;
}

function formularioEnviada() {
  const f = nodo("form", null, "editor tarjeta");
  f.append(nodo("h3", "Marcar como enviada", "subtitulo"));
  const dia = nodo("input");
  dia.type = "date";
  dia.required = true;
  dia.value = new Date().toISOString().slice(0, 10);
  const canal = selector(CANALES, "Canal");
  const otro = nodo("input");
  otro.type = "text";
  otro.maxLength = 60;
  const campoOtro = campo("¿Cuál?", otro);
  campoOtro.hidden = true;
  canal.querySelector("select").addEventListener("change", (e) => { campoOtro.hidden = e.target.value !== "otro"; });
  f.append(campo("Fecha de envío", dia), canal, campoOtro, nodo("button", "Marcar como enviada"));
  f.addEventListener("submit", (e) => {
    e.preventDefault();
    accion(`/api/candidaturas/${ID}/enviada`, {
      fecha: dia.value, canal: canal.querySelector("select").value, canal_otro: otro.value.trim() || null,
    }, "Marcada como enviada.");
  });
  return f;
}

function formularioCerrar() {
  const f = nodo("form", null, "editor tarjeta");
  f.append(nodo("h3", "Cerrar candidatura", "subtitulo"));
  const motivo = selector(MOTIVOS, "Motivo");
  f.append(motivo, nodo("button", "Cerrar", "secundario"));
  f.addEventListener("submit", (e) => {
    e.preventDefault();
    accion(`/api/candidaturas/${ID}/cerrar`, { motivo: motivo.querySelector("select").value }, "Candidatura cerrada.");
  });
  return f;
}

// --- respuesta de la empresa ---------------------------------------------------------------------
function propuesta(p) {
  const s = nodo("div", null, "tarjeta");
  s.append(nodo("p", `Parece que la respuesta trata de ${ETIQUETAS_RESPUESTA[p.etiqueta] || "otra cosa"}.`));
  if (p.tipo === "ninguna") s.append(nodo("p", "Horma no propone ningún cambio de estado. Decide tú.", "suave"));
  else if (p.tipo === "nota") s.append(nodo("p", "Propuesta: dejar constancia en el historial.", "suave"));
  else s.append(nodo("p", `Propuesta: pasar a «${ESTADOS[p.destino] || p.destino}».`, "suave"));
  const fila = nodo("div", null, "fila");
  if (p.tipo !== "ninguna") fila.append(boton("Confirmar", () => accion(`/api/candidaturas/${ID}/respuesta/confirmar`, {}, "Aplicado.")));
  fila.append(boton("Descartar", () => accion(`/api/candidaturas/${ID}/respuesta/descartar`, {}, "Descartado."), "secundario"));
  s.append(fila);
  return s;
}

function respuesta() {
  const s = nodo("section");
  s.append(nodo("h3", "Respuesta de la empresa", "subtitulo"));
  if (c.clasificando) {
    s.append(nodo("p", "Leyendo la respuesta…", "suave"));
    return s;
  }
  if (c.respuesta_propuesta) {
    s.append(propuesta(c.respuesta_propuesta));
    return s;
  }
  const f = nodo("form", null, "editor");
  const t = nodo("textarea");
  t.rows = 6;
  t.required = true;
  t.maxLength = 20000;
  t.setAttribute("aria-label", "Texto de la respuesta");
  f.append(t, nodo("p", "Pega aquí el correo. Horma propone un cambio de estado; el texto no se guarda.", "suave"),
    nodo("button", "Analizar respuesta", "secundario"));
  f.addEventListener("submit", (e) => {
    e.preventDefault();
    accion(`/api/candidaturas/${ID}/respuesta`, { texto: t.value }, "Leyendo la respuesta…");
  });
  s.append(f);
  return s;
}

// --- historial ----------------------------------------------------------------------------------
function historial() {
  const s = nodo("details", null, "leer");
  s.append(nodo("summary", "Historial"));
  const ul = nodo("ul");
  for (const e of c.eventos) {
    let texto;
    if (e.tipo === "cv_base_guardado") texto = "Guardaste el CV adaptado como tu CV base.";
    else if (e.tipo === "nota") texto = `Respuesta de la empresa registrada (${ETIQUETAS_RESPUESTA[e.etiqueta_respuesta] || "otra cosa"}).`;
    else texto = `${ESTADOS[e.de] || "Inicio"} → ${ESTADOS[e.a] || e.a}${e.motivo ? ` (${e.motivo})` : ""}${e.canal ? ` · ${e.canal}` : ""}`;
    ul.append(nodo("li", `${fecha(e.creado_en)} · ${texto}`));
  }
  if (!c.eventos.length) ul.append(nodo("li", "Sin movimientos todavía."));
  s.append(ul);
  return s;
}

// --- pintar -------------------------------------------------------------------------------------
function pintar() {
  const partes = [cabecera()];
  if (c.preparacion === "en_curso") {
    partes.push(nodo("p", "Horma está preparando el CV y la carta… puede tardar un minuto.", "suave"));
  } else if (c.preparacion === "error") {
    partes.push(nodo("p", c.motivo_error || "No se pudo preparar esta candidatura.", "alerta"));
  } else {
    partes.push(huecosYAvisos(), documento("CV adaptado", "cv_contenido", guardarComoBase()),
      documento("Carta de presentación", "carta_contenido"));
    if (c.estado === "borrador") partes.push(aprobar());
    else if (c.estado !== "cerrada" && c.documento) partes.push(descargas());
    if (c.estado === "aprobada") partes.push(formularioEnviada());
    if ((c.estado === "enviada" || c.estado === "entrevista") && c.enviada_en) {
      const canal = c.canal === "otro" ? c.canal_otro || "otro canal" : c.canal;
      partes.push(nodo("p", `Enviada el ${fecha(c.enviada_en)} por ${canal}.`, "suave"));
    }
    if (c.estado === "enviada" || c.estado === "entrevista") partes.push(respuesta());
    if (c.estado === "enviada") {
      const fila = nodo("div", null, "fila");
      fila.append(boton("Me han llamado a una entrevista", () => accion(`/api/candidaturas/${ID}/entrevista`, {}, "Pasada a entrevista."), "secundario"));
      partes.push(fila);
    }
    if (c.estado !== "cerrada") partes.push(formularioCerrar());
  }
  partes.push(historial());
  $("candidatura").replaceChildren(...partes);
}

async function cargar() {
  clearTimeout(temporizador);
  const r = await api(`/api/candidaturas/${ID}`);
  if (!r.ok) return avisar(r.motivo, true);
  c = r.datos;
  pintar();
  if (c.preparacion === "en_curso" || c.clasificando) temporizador = setTimeout(cargar, 3000);
}

(async () => {
  if (!(await arrancar("/candidaturas"))) return;
  await cargar();
})();
