// Pantalla de una candidatura (RF-3.8 a RF-3.10): CV y carta para revisar, editar y aprobar; después, el
// seguimiento. Todo texto (incluido el que escribió el modelo) se pinta con textContent.
const ID = Number(location.pathname.split("/").pop());
const CANALES = [["correo", "Correo"], ["web", "Web de la empresa"], ["linkedin", "LinkedIn"], ["otro", "Otro"]];
const NOMBRE_ESTADO = { borrador: "Borrador", aprobada: "Aprobada", enviada: "Enviada", entrevista: "Entrevista", cerrada: "Cerrada" };   // historial: los estados internos
const DOCUMENTOS = { cv: "CV", carta: "Carta", oferta: "Oferta" };
let c = null;
let temporizador = null;
let avance = 0;   // % de la tarea que prepara el CV y la carta (RF-8.7)
let barraPrep = null;   // su barra, que se conserva entre repintados

function boton(texto, alClic, clase) {
  const b = nodo("button", texto, clase);
  b.type = "button";
  b.addEventListener("click", alClic);
  return b;
}

async function accion(ruta, cuerpo, ok) {
  const r = await api(ruta, { metodo: "POST", cuerpo: cuerpo || {} });
  if (!r.ok) {
    avisar(r.motivo, true);
    return false;
  }
  avisar(ok || "Hecho.");
  await cargar();
  return true;
}

// --- cabecera -----------------------------------------------------------------------------------
function cabecera() {
  const s = nodo("section");
  s.append(nodo("h2", c.oferta.titulo || "Oferta sin título"));
  s.append(nodo("p", c.oferta.empresa || "Empresa sin indicar", "suave"));
  const estado = estadoVisible(c.estado, c.preparacion);
  if (estado !== "Preparando") s.append(nodo("span", estado, "estado bien"));   // mientras prepara, ya lo dice la barra
  if (c.estado === "cerrada" && c.motivo_cierre) s.append(nodo("span", `Motivo: ${MOTIVOS_CIERRE[c.motivo_cierre] || c.motivo_cierre}`, "estado apagado"));
  const fila = nodo("div", null, "fila");
  fila.append(boton("Ver oferta original", () => verOriginal(c.oferta.id), "secundario"));   // RF-8.3
  s.append(fila);
  return s;
}

// --- «Revisa esto»: una sola lista con lo que la oferta pide y no consta, y los avisos -----------------------------------
// «Revisa esto» en tres grupos (RF-10.13): No consta en tu CV, Revisa y Dato dudoso. Un grupo vacío no sale, y sin
// nada que revisar no hay panel. Las candidaturas antiguas, sin `tipo`, se ven en «Revisa».
function grupoAvisos(titulo, hijos) {
  const g = nodo("div", null, "grupo-avisos");
  g.append(nodo("h4", titulo, "etiqueta-mono"));
  const ul = nodo("ul", null, "lista");
  ul.append(...hijos);
  g.append(ul);
  return g;
}

function avisoItem(a) {
  const li = nodo("li", null, "tarjeta alerta");
  li.append(nodo("strong", DOCUMENTOS[a.documento] || a.documento));
  if (a.frase) li.append(nodo("blockquote", a.frase));
  li.append(nodo("p", a.mensaje));
  return li;
}

function revisaEsto() {
  const s = nodo("section", null, "panel");
  const hayAlgo = c.huecos.length > 0 || c.avisos.length > 0;
  if (!hayAlgo && c.preparacion !== "pendiente_de_ti") return s;
  s.append(nodo("h3", "Revisa esto", "subtitulo"));
  if (!hayAlgo) {
    s.append(nodo("p", TEXTOS.revisaFalta, "tarjeta alerta"));
    return s;
  }
  const de = (tipo) => c.avisos.filter((a) => (a.tipo || "revisa") === tipo);
  if (c.huecos.length) {
    const li = nodo("li", null, "tarjeta");
    li.append(nodo("strong", textoNoConstaVarios(c.huecos.map((h) => h.requisito))));
    const propuesta = c.huecos.find((h) => h.propuesta)?.propuesta;
    if (propuesta) li.append(nodo("p", propuesta, "suave"));
    if (c.huecos.length > 1) {   // la lista entera, sin recortar, para quien quiera verla
      const d = nodo("details", null, "seccion-plegable");
      d.append(nodo("summary", `Ver los ${c.huecos.length} requisitos`));
      const todos = nodo("ul", null, "lista");
      todos.append(...c.huecos.map((h) => nodo("li", h.requisito)));
      d.append(todos);
      li.append(d);
    }
    s.append(grupoAvisos("No consta en tu CV", [li]));
  }
  if (de("revisa").length) s.append(grupoAvisos("Revisa", de("revisa").map(avisoItem)));
  if (de("dudoso").length) s.append(grupoAvisos("Dato dudoso", de("dudoso").map(avisoItem)));
  return s;
}

// --- documentos (CV y carta) --------------------------------------------------------------------
function documento(titulo, clave) {
  const s = nodo("section");
  s.append(nodo("h3", titulo, "subtitulo"));
  const hoja = clave === "carta_contenido" ? cartaBonita(c[clave]) : cvBonito(c[clave]);
  s.append(hoja);
  if (c.estado === "borrador") {
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
      f.append(t, nodo("p", TEXTOS.editaDocumento, "suave"), fila);
      f.addEventListener("submit", async (e) => {
        e.preventDefault();
        const r = await api(`/api/candidaturas/${ID}`, { metodo: "PATCH", cuerpo: { [clave]: t.value } });
        if (!r.ok) return avisar(r.motivo, true);
        avisar("Guardado.");
        await cargar();
      });
      s.append(f);
      t.focus();
    }, "secundario");
    acciones.append(editar);
    s.append(acciones);
  }
  return s;
}

// --- «Detalles»: plegado, con lo que Horma decidió por su cuenta ---------------------------------
function detalles() {
  const d = nodo("details", null, "leer");
  d.append(nodo("summary", "Detalles"));
  if (c.cobertura_ats !== null && c.cobertura_ats !== undefined) {
    d.append(nodo("p", `Palabras de la oferta que aparecen en el CV: ${Math.round(Number(c.cobertura_ats) * 100)} %`, "suave"));
  }
  return d;
}

// --- botones según el estado --------------------------------------------------------------------
function descargas() {
  const s = nodo("div", null, "fila");
  for (const [texto, ruta] of [["Descargar CV (PDF)", "cv.pdf"], ["Descargar carta (PDF)", "carta.pdf"]]) {
    const a = nodo("a", texto, "boton secundario");
    a.href = `/api/candidaturas/${ID}/${ruta}`;
    a.setAttribute("download", "");   // el nombre lo pone el servidor: tipo, puesto y empresa
    s.append(a);
  }
  return s;
}

// «Aprobar y descargar»: aprobar cuenta como haber revisado los avisos; después salen los dos PDF.
async function aprobarYDescargar() {
  if (!(await accion(`/api/candidaturas/${ID}/aprobar`, {}, "Candidatura aprobada."))) return;
  for (const ruta of ["cv.pdf", "carta.pdf"]) {
    const a = nodo("a");
    a.href = `/api/candidaturas/${ID}/${ruta}`;
    a.setAttribute("download", "");   // el nombre lo pone el servidor: tipo, puesto y empresa
    document.body.append(a);
    a.click();
    a.remove();
  }
}

function aprobar() {
  const s = nodo("section", null, "panel");
  s.append(nodo("p", "Puedes aprobar aunque queden avisos: al aprobar, se dan por revisados.", "suave"));
  const fila = nodo("div", null, "fila");
  fila.append(boton("Aprobar y descargar", aprobarYDescargar));
  s.append(fila);
  return s;
}

function formularioEnviada() {
  const f = nodo("form", null, "editor tarjeta");
  f.append(nodo("h3", "Cuando la hayas enviado", "subtitulo"));
  const sel = nodo("select");
  const vacio = nodo("option", "Sin indicar");
  vacio.value = "";
  sel.append(vacio);
  for (const [valor, texto] of CANALES) {
    const o = nodo("option", texto);
    o.value = valor;
    sel.append(o);
  }
  const otro = nodo("input");
  otro.type = "text";
  otro.maxLength = 60;
  const campoOtro = campo("¿Cuál?", otro);
  campoOtro.hidden = true;
  sel.addEventListener("change", () => { campoOtro.hidden = sel.value !== "otro"; });
  f.append(campo("Canal (opcional)", sel), campoOtro, nodo("button", "Marcar como enviada"));
  f.addEventListener("submit", (e) => {
    e.preventDefault();
    accion(`/api/candidaturas/${ID}/enviada`, {
      canal: sel.value || null, canal_otro: sel.value === "otro" ? otro.value.trim() || null : null,
    }, "Marcada como enviada.");
  });
  return f;
}

// Dos botones, solo los que son legales: «piden información» no cambia nada (P15).
// «Estado» (RF-10.17): qué ha pasado con la candidatura después de enviarla.
function respuestas() {
  const s = nodo("section");
  s.append(nodo("h3", "Estado", "subtitulo"));
  const fila = nodo("div", null, "fila");
  if (c.estado === "enviada") {
    fila.append(boton("Me han llamado", () => accion(`/api/candidaturas/${ID}/entrevista`, {}, "Pasada a entrevista.")));
  }
  fila.append(boton("Me han contratado", async () => {
    if (await accion(`/api/candidaturas/${ID}/cerrar`, { motivo: "contratada" }, "Candidatura cerrada: te han contratado.")) {
      $("contratada-texto").textContent = TEXTOS.contratada;
      $("ventana-contratada").showModal();
    }
  }));
  fila.append(boton("Me han rechazado", () => accion(`/api/candidaturas/${ID}/cerrar`, { motivo: "rechazo" }, "Candidatura cerrada."), "secundario"));
  s.append(fila);
  return s;
}
$("contratada-cerrar").addEventListener("click", () => $("ventana-contratada").close());

function formularioCerrar() {
  const f = nodo("form", null, "editor tarjeta");
  f.append(nodo("h3", "Cerrar candidatura", "subtitulo"));
  const sel = nodo("select");
  for (const [valor, texto] of MOTIVOS_PREGUNTA) {
    const o = nodo("option", texto);
    o.value = valor;
    sel.append(o);
  }
  f.append(campo("Motivo", sel), nodo("button", "Cerrar", "secundario"));
  f.addEventListener("submit", (e) => {
    e.preventDefault();
    accion(`/api/candidaturas/${ID}/cerrar`, { motivo: sel.value }, "Candidatura cerrada.");
  });
  return f;
}

// --- historial ----------------------------------------------------------------------------------
function historial() {
  const s = nodo("details", null, "leer");
  s.append(nodo("summary", "Historial"));
  const ul = nodo("ul");
  for (const e of c.eventos) {
    const texto = `${NOMBRE_ESTADO[e.de] || "Inicio"} → ${NOMBRE_ESTADO[e.a] || e.a}${e.motivo ? ` (${e.motivo})` : ""}${e.canal ? ` · ${e.canal}` : ""}`;
    ul.append(nodo("li", `${fecha(e.creado_en)} · ${texto}`));
  }
  if (!c.eventos.length) ul.append(nodo("li", "Sin movimientos todavía."));
  s.append(ul);
  return s;
}

// --- borrador de una versión anterior del perfil (RF-5.1f) ---------------------------------------
function avisoDesfasada() {
  const d = nodo("div", null, "panel");
  d.append(nodo("p", "Preparada con una versión anterior de tu perfil", "alerta"));
  d.append(nodo("p", "Puedes aprobarla igualmente. Si prefieres que use tu perfil actual, vuelve a prepararla.", "suave"));
  const fila = nodo("div", null, "fila");
  const volver = boton("Volver a preparar", () => {
    volver.hidden = true;
    const conf = nodo("div", null, "fila");
    conf.append(
      nodo("span", "Se perderá lo que hayas editado en este borrador."),
      boton("Sí, volver a preparar", () => accion(`/api/candidaturas/${ID}/reintentar`, {}, "Preparando de nuevo…"), "secundario"),
      boton("Cancelar", () => { conf.remove(); volver.hidden = false; }, "secundario"),
    );
    d.append(conf);
  }, "secundario");
  fila.append(volver);
  d.append(fila);
  return d;
}

// --- pintar -------------------------------------------------------------------------------------
function pintar() {
  const partes = [cabecera()];
  if (c.preparacion !== "en_curso" && barraPrep) {   // terminó: la próxima preparación empieza de cero
    barraPrep.quitar();
    barraPrep = null;
    avance = 0;
  }
  if (c.preparacion === "en_curso") {
    const caja = nodo("div");
    // la misma barra en cada repintado: así sigue rellenándose en vez de empezar de cero (RF-10.8c)
    if (!barraPrep) barraPrep = barraAvance(caja, "Preparando tu CV y tu carta");
    else caja.append(barraPrep.caja);
    barraPrep.poner(avance);
    partes.push(caja,nodo("p", "Horma está preparando el CV y la carta… puede tardar un minuto.", "suave"));
  } else if (c.preparacion === "error") {
    partes.push(nodo("p", c.motivo_error || "No se pudo preparar esta candidatura.", "alerta"));
    partes.push(boton("Reintentar", () => accion(`/api/candidaturas/${ID}/reintentar`, {}, "Preparando de nuevo…")));
  } else {
    if (c.desfasada) partes.push(avisoDesfasada());
    partes.push(revisaEsto(), documento("CV adaptado", "cv_contenido"),
      documento("Carta de presentación", "carta_contenido"), detalles());
    if (c.estado === "borrador") partes.push(aprobar());
    else if (c.estado !== "cerrada") partes.push(descargas());
    if (c.estado === "aprobada") partes.push(formularioEnviada());
    if ((c.estado === "enviada" || c.estado === "entrevista") && c.enviada_en) {
      const canal = c.canal === "otro" ? c.canal_otro || "otro canal" : c.canal;
      partes.push(nodo("p", `Enviada el ${fecha(c.enviada_en)}${canal ? ` por ${canal}` : ""}.`, "suave"));
    }
    if (c.estado === "enviada" || c.estado === "entrevista") partes.push(respuestas());
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
  if (c.preparacion === "en_curso") {   // la barra retoma su punto aunque se haya vuelto a la pantalla (RF-8.7b)
    const t = await api("/api/tareas/activas?tipo=candidatura");
    const mia = t.ok ? t.datos.tareas.find((x) => x.entidad_id === ID) : null;
    avance = mia ? Math.max(avance, mia.progreso) : avance;
  }
  pintar();
  if (c.preparacion === "en_curso") temporizador = setTimeout(cargar, 3000);
}

(async () => {
  if (!(await arrancar("/candidaturas"))) return;
  await cargar();
})();
