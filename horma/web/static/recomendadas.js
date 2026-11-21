// Pantalla de ofertas recomendadas (RF-2.8, 6.5, 8.4 a 8.7). «Qué buscas» se guarda y vuelve a buscar y puntuar;
// la vista (nota, orden y estado) se aplica aquí, en el navegador, sin pedir nada al servidor ni al modelo.
const AYUDA = [
  ["Oferta", "El título de la oferta y la empresa que la publica. «Ver oferta original» abre el texto completo."],
  ["Puesto", "El tipo de trabajo según la clasificación de Horma, sea cual sea el sector."],
  ["Compatibilidad", "Nota de 0 a 100 de lo bien que encajan tu experiencia y formación con lo que pide la oferta. Orienta, no decide. Despliega la fila para ver por qué."],
  ["Salario", "Tal como lo dice la oferta, sin convertirlo. Si no lo publica, lo verás indicado."],
  ["Lugar", "El país donde está el puesto, o «Remoto»."],
  ["Publicado", "El día en que se publicó la oferta. Si no lo dice, «No consta fecha de publicación»."],
];
const CLAVE_VISTA = "horma.vista.recomendadas";
const VISTA_POR_DEFECTO = { min: 40, max: 100, orden: "recientes", estado: "nuevas" };
const ESTADOS_VISTA = [["nuevas", "Nuevas"], ["candidatura", "Con candidatura"], ["descartadas", "Descartadas"]];
const ETIQUETA_CANDIDATURA = { borrador: "Borrador", aprobada: "Aprobada", enviada: "Enviada",
  entrevista: "Entrevista", cerrada: "Cerrada" };
const TEXTO_TOPE = "Hoy ya hemos puntuado todo lo posible. Mañana seguimos con el resto.";
const TEXTO_SUELTAS = "Has puntuado 30 ofertas sueltas hoy. Mañana puedes seguir.";
let guardadas = null;
let opciones = null;
let todas = [];            // lo que devuelve la API; la vista lo filtra y ordena sin volver a pedirlo
let vista = { ...VISTA_POR_DEFECTO };
let sueltasHoy = 0;
let maxSueltas = 30;
let barra = null;          // barra de avance de la puntuación en marcha
let ultimoAvance = -1;
let dejarDeSeguir = null;
let abiertas = null;       // ids de las filas desplegadas; null hasta el primer pintado (entonces, solo la primera)

// Mapeo fijo familia → tono (.tono-0…5, RF-6.4): la misma familia sale siempre del mismo color.
function tonoDe(texto) {
  let h = 0;
  for (const c of String(texto || "")) h = (h * 31 + c.charCodeAt(0)) % 6;
  return `tono-${h}`;
}

// --- Ayuda «?»: globo propio con clic o foco, Escape y clic fuera (RF-6.7b) -----------------------
function cerrarAyudas(salvo = null) {
  for (const b of document.querySelectorAll("button.ayuda[aria-expanded='true']")) {
    if (b === salvo) continue;
    b.setAttribute("aria-expanded", "false");
    document.getElementById(b.getAttribute("aria-describedby")).hidden = true;
  }
}
document.addEventListener("click", (e) => cerrarAyudas(e.target.closest("button.ayuda")));
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const abierta = document.querySelector("button.ayuda[aria-expanded='true']");
  cerrarAyudas();
  if (abierta) abierta.focus();
});

function ayuda(nombre, texto, i) {
  const q = nodo("button", "?", "ayuda");
  q.type = "button";
  q.setAttribute("aria-label", `Qué significa «${nombre}»`);
  q.setAttribute("aria-expanded", "false");
  const globo = nodo("span", texto, "ayuda-globo");
  globo.id = `ayuda-${i}`;
  globo.hidden = true;
  q.setAttribute("aria-describedby", globo.id);
  q.addEventListener("click", () => {
    const abrir = globo.hidden;
    globo.hidden = !abrir;
    q.setAttribute("aria-expanded", String(abrir));
  });
  q.addEventListener("focusout", (e) => {
    if (!globo.contains(e.relatedTarget)) {
      globo.hidden = true;
      q.setAttribute("aria-expanded", "false");
    }
  });
  return [q, globo];
}

function cabeceras() {
  const fila = $("cabeceras");
  AYUDA.forEach(([nombre, texto], i) => {
    const th = nodo("th");
    th.scope = "col";
    th.append(nodo("span", nombre), ...ayuda(nombre, texto, i));
    fila.append(th);
  });
  const ultima = nodo("th");
  ultima.append(nodo("span", "Detalle", "solo-lector"));
  fila.append(ultima);
}

function celda(rotulo, clase, ...hijos) {
  const td = nodo("td", null, clase);
  td.dataset.etiqueta = rotulo;
  td.append(...hijos);
  return td;
}

function formularioCorreccion(o, alTerminar) {
  const f = nodo("form", null, "editor");
  const nota = nodo("input");
  nota.type = "number";
  nota.min = 0;
  nota.max = 100;
  nota.className = "corto";
  nota.placeholder = String(o.nota);
  const motivo = nodo("textarea");
  motivo.rows = 3;
  motivo.maxLength = 1000;
  motivo.required = true;
  motivo.placeholder = "¿Qué no encaja? (por ejemplo: «la oferta pide carné de conducir y yo no lo tengo»)";
  const enviar = nodo("button", "Enviar corrección");
  const cancelar = nodo("button", "Cancelar", "secundario");
  cancelar.type = "button";
  cancelar.addEventListener("click", () => alTerminar(false));
  const fila = nodo("div", null, "fila");
  fila.append(enviar, cancelar);
  f.append(campo("Nota que te parece justa (opcional)", nota), campo("Motivo", motivo), fila);
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const cuerpo = { comentario: motivo.value.trim(), nota: nota.value === "" ? null : Number(nota.value) };
    const r = await api(`/api/matches/${o.id}/correccion`, { metodo: "POST", cuerpo });
    if (!r.ok) return avisar(r.estado === 422 ? "La nota va de 0 a 100 y el motivo no puede estar vacío." : r.motivo, true);
    avisar("Corrección guardada. Gracias: Mar la revisará.");
    o.correccion = r.datos;
    alTerminar(true);
  });
  return f;
}

// «Preparar candidatura» (RF-3.7b): crea la candidatura y lleva a ella; el CV base lo elige Horma.
function accionesCandidatura(o, contenedor) {
  const b = nodo("button", "Preparar candidatura", "primario-mov");
  b.type = "button";
  let repetir = false;
  b.addEventListener("click", async (e) => {
    e.stopPropagation();
    b.disabled = true;
    const r = await api("/api/candidaturas", { metodo: "POST", cuerpo: { oferta_id: o.id, repetir } });
    if (r.ok) {
      location.href = `/candidaturas/${r.datos.id}`;
      return;
    }
    b.disabled = false;
    avisar(r.motivo, true);
    if (r.estado === 409 && /Ya preparaste/.test(r.motivo || "") && !repetir) {
      repetir = true;
      b.textContent = "Preparar otra igualmente";
      const a = nodo("a", "Ver cerradas", "bloque");
      a.href = "/candidaturas";
      contenedor.append(a);
    }
    if (r.estado === 409 && /CV base/i.test(r.motivo || "") && !contenedor.querySelector("a[href='/cv-base']")) {
      const a = nodo("a", "Generar CV base", "bloque");
      a.href = "/cv-base";
      contenedor.append(a);
    }
  });
  return b;
}

// --- Vista en el navegador (RF-8.4c) -----------------------------------------------------------
function leerVista() {
  try {
    const v = JSON.parse(localStorage.getItem(CLAVE_VISTA) || "null");
    if (v && typeof v === "object") return { ...VISTA_POR_DEFECTO, ...v };
  } catch (e) {
    /* sin almacenamiento o valor roto: valores por defecto */
  }
  return { ...VISTA_POR_DEFECTO };
}

function guardarVista() {
  try {
    localStorage.setItem(CLAVE_VISTA, JSON.stringify(vista));
  } catch (e) {
    /* modo privado o datos bloqueados: la vista vale solo para esta visita */
  }
}

function estadoDe(o) {
  if (o.descartada) return "descartadas";
  return o.candidatura ? "candidatura" : "nuevas";
}

function enRango(o) {
  return o.sin_puntuar || (o.nota >= vista.min && o.nota <= vista.max);
}

function fechaOrden(o) {
  return new Date(o.fecha_publicacion || o.creada_en || 0).getTime() || 0;
}

function ordenar(lista) {
  const porFecha = (a, b) => fechaOrden(b) - fechaOrden(a) || b.id - a.id;
  if (vista.orden === "compatibles") {   // lo puntuado primero, de más a menos nota; el resto, al final
    return [...lista].sort((a, b) => (b.sin_puntuar ? -1 : b.nota) - (a.sin_puntuar ? -1 : a.nota) || porFecha(a, b));
  }
  return [...lista].sort(porFecha);
}

function pintarVista() {
  $("nota-min").value = vista.min;
  $("nota-max").value = vista.max;
  $("orden").value = vista.orden;
  const visibles = todas.filter(enRango);
  const n = (e) => visibles.filter((o) => estadoDe(o) === e).length;
  $("estado").replaceChildren(...ESTADOS_VISTA.map(([valor, texto]) => {
    const op = nodo("option", `${texto} (${n(valor)})`);
    op.value = valor;
    return op;
  }));
  $("estado").value = vista.estado;
}

function leerCamposVista() {
  const num = (id, defecto) => {
    const v = $(id).value.trim();
    const x = v === "" ? defecto : Number(v);
    return Number.isFinite(x) ? Math.max(0, Math.min(100, Math.round(x))) : defecto;
  };
  vista = { min: num("nota-min", 0), max: num("nota-max", 100), orden: $("orden").value, estado: $("estado").value };
  if (vista.min > vista.max) [vista.min, vista.max] = [vista.max, vista.min];
  guardarVista();
  pintarLista();
}

// --- Detalle de cada oferta ----------------------------------------------------------------------
// Contenido de la fila desplegada (RF-6.5d): a la izquierda el porqué; a la derecha, las acciones.
function detalle(o) {
  const cont = nodo("div", null, "detalle");
  const izq = nodo("div", null, "porque-cuerpo");
  const dch = nodo("div", null, "acciones");
  cont.append(izq);
  const pintar = () => {
    izq.replaceChildren(nodo("span", "Por qué te la recomendamos", "etiqueta-mono"));
    if (o.sin_puntuar) {
      izq.append(nodo("p", "Esta oferta todavía no tiene nota. Horma la puntuará sola; si la quieres ya, pulsa «Puntuar ahora»."));
      return;
    }
    if (o.retirada) {
      izq.append(nodo("p", "Se ha retirado la explicación porque no cumplía las reglas de Horma. La nota sigue siendo válida.", "suave"));
    } else {
      izq.append(nodo("p", o.explicacion));
      if (o.cita_perfil) izq.append(nodo("p", `De tu perfil: «${o.cita_perfil}»`, "suave"));
      if (o.cita_oferta) izq.append(nodo("p", `De la oferta: «${o.cita_oferta}»`, "suave"));
    }
    if (o.desfasado) izq.append(nodo("p", "Esta nota se calculó con una versión anterior de tu perfil.", "suave"));
    if (o.correccion) {
      const c = o.correccion;
      const nota = c.nota !== null && c.nota !== undefined ? ` (nota que propones: ${c.nota})` : "";
      izq.append(nodo("p", `Tu corrección${nota}: ${c.comentario}`, "origen"));
    }
  };
  pintar();
  cont.append(dch);

  const original = nodo("button", "Ver oferta original", "secundario");
  original.type = "button";
  original.addEventListener("click", (e) => { e.stopPropagation(); verOriginal(o.id); });

  if (o.sin_puntuar) {
    dch.append(botonPuntuarAhora(o), original);
  } else {
    const corregir = nodo("button", "Corregir explicación", "secundario");
    corregir.type = "button";
    corregir.addEventListener("click", (e) => {
      e.stopPropagation();
      corregir.hidden = true;
      const f = formularioCorreccion(o, (guardada) => {
        if (guardada) pintar();
        f.remove();
        corregir.hidden = false;
      });
      izq.append(f);
    });
    dch.append(corregir);
    if (!o.descartada) dch.append(accionCandidatura(o, dch));
    dch.append(original);
  }
  const descarte = botonDescartar(o);
  if (descarte) dch.append(descarte);
  if (!o.sin_puntuar && !o.descartada) dch.append(nodo("p", "Horma elige tu CV base más adecuado.", "suave"));
  return cont;
}

// «Puntuar ahora» (RF-8.5e): puntúa solo esta oferta; con 30 sueltas hoy, desactivado con su texto (RF-8.5f).
function botonPuntuarAhora(o) {
  const caja = nodo("div", null, "acciones-ahora");
  const b = nodo("button", "Puntuar ahora");
  b.type = "button";
  const nota = nodo("p", "", "suave");
  nota.setAttribute("role", "status");
  const agotadas = () => { b.disabled = true; nota.textContent = TEXTO_SUELTAS; };
  if (sueltasHoy >= maxSueltas) agotadas();
  b.addEventListener("click", async (e) => {
    e.stopPropagation();
    b.disabled = true;
    nota.textContent = "Puntuando…";
    const r = await api(`/api/matches/${o.id}/puntuar`, { metodo: "POST" });
    if (r.estado === 429) return agotadas();
    if (!r.ok) {
      b.disabled = false;
      nota.textContent = "";
      return avisar(r.motivo, true);
    }
    sueltasHoy += 1;
    seguirTarea(r.datos.tarea_id, (p) => { nota.textContent = `Puntuando… ${p} %`; }, async (t) => {
      if (t.estado === "error") {
        b.disabled = false;
        nota.textContent = "No se ha podido puntuar esta oferta. Inténtalo otra vez.";
        return;
      }
      await cargarLista();
    });
  });
  caja.append(b, nota);
  return caja;
}

// Estado de la candidatura (RF-8.6): con una abierta, «Ver candidatura» sustituye a «Preparar candidatura».
function accionCandidatura(o, contenedor) {
  const c = o.candidatura;
  if (c && c.estado !== "cerrada") {
    const a = nodo("a", "Ver candidatura", "boton");
    a.href = `/candidaturas/${c.id}`;
    return a;
  }
  return accionesCandidatura(o, contenedor);
}

// «Descartar» (RF-8.6b) y «Recuperar» (RF-8.6d). Una oferta con candidatura abierta no se descarta.
function botonDescartar(o) {
  if (o.descartada) {
    const b = nodo("button", "Recuperar", "boton-texto");
    b.type = "button";
    b.addEventListener("click", (e) => { e.stopPropagation(); recuperar(o); });
    return b;
  }
  if (o.candidatura && o.candidatura.estado !== "cerrada") return null;
  const b = nodo("button", "Descartar", "boton-texto");
  b.type = "button";
  b.addEventListener("click", async (e) => {
    e.stopPropagation();
    b.disabled = true;
    const r = await api(`/api/descartes/${o.id}`, { metodo: "PUT" });
    if (!r.ok) {
      b.disabled = false;
      return avisar(r.motivo, true);
    }
    o.descartada = true;
    avisarDescarte(o);
    pintarLista();
  });
  return b;
}

async function recuperar(o) {
  const r = await api(`/api/descartes/${o.id}`, { metodo: "DELETE" });
  if (!r.ok) return avisar(r.motivo, true);
  o.descartada = false;
  $("aviso-descarte").replaceChildren();
  pintarLista();
}

// «Oferta descartada. Deshacer»: sin confirmar antes (RF-8.6b).
function avisarDescarte(o) {
  const deshacer = nodo("button", "Deshacer", "boton-texto");
  deshacer.type = "button";
  deshacer.addEventListener("click", () => recuperar(o));
  $("aviso-descarte").replaceChildren(nodo("span", "Oferta descartada. "), deshacer);
}

function filaOferta(o) {
  const id = `detalle-${o.id}`;
  const tr = nodo("tr", null, "fila-oferta");
  const titulo = nodo("span", o.titulo || "Sin título", "titulo-oferta");   // el enlace de origen va en «Ver oferta original»
  const celdaOferta = celda("Oferta", "c-oferta", titulo, nodo("span", o.empresa || "Empresa sin indicar", "suave bloque"));
  if (o.atribucion) celdaOferta.append(nodo("span", o.atribucion, "suave bloque"));  // cita de la fuente (RF-5.5d)
  if (o.propia) {  // las que añade la usuaria salen siempre, con su marca y lo que vio el auditor (RF-5.3e)
    celdaOferta.append(nodo("span", `Añadida por ti · analizada el ${fecha(o.analizada_en)}`, "estado bien bloque"));
    if (o.fuente_desconocida) celdaOferta.append(nodo("span", textoFuenteDesconocida(o), "estado apagado bloque"));
    if (o.aviso_auditor) celdaOferta.append(nodo("span", o.aviso_auditor, "estado error bloque"));
  }
  if (o.candidatura) {  // el estado, siempre con texto (RF-6.7e)
    celdaOferta.append(nodo("span", `Candidatura: ${ETIQUETA_CANDIDATURA[o.candidatura.estado] || o.candidatura.estado}`,
      "estado bloque"));
  }
  tr.append(celdaOferta);
  tr.append(celda("Puesto", "c-puesto", nodo("span", etiqueta(o.familia), `etiqueta-puesto ${tonoDe(o.familia)}`),
                  nodo("span", etiqueta(o.nivel), "suave")));

  const comp = celda("Compatibilidad", "c-compat");
  if (o.sin_puntuar) {
    comp.append(nodo("em", "Sin puntuar", "suave"));
  } else {
    const barraNota = nodo("div", null, "barra-compat");
    barraNota.setAttribute("role", "meter");
    barraNota.setAttribute("aria-valuenow", String(o.nota));
    barraNota.setAttribute("aria-valuemin", "0");
    barraNota.setAttribute("aria-valuemax", "100");
    barraNota.setAttribute("aria-label", "Compatibilidad");
    const relleno = nodo("span");
    relleno.style.width = `${Math.max(0, Math.min(100, o.nota))}%`;   // por CSSOM: la CSP no permite style= en el HTML
    barraNota.append(relleno);
    const fila = nodo("div", null, "nota");
    fila.append(barraNota, nodo("span", String(o.nota), "numero"));
    comp.append(fila);
  }
  tr.append(comp);

  tr.append(celda("Salario", "c-salario", nodo("span", o.salario || "No publicado", o.salario ? "" : "suave")));
  // «Presencial · Rota»: la modalidad y, a su lado, el municipio que dice la oferta (o, si no, el país).
  const sitio = o.ubicacion || (String(o.pais || "").toLowerCase() === "remoto" ? null : nombrePais(o.pais));
  const lugar = [nombreModalidad(o.modalidad) || null, sitio].filter(Boolean).join(" · ") || "—";
  tr.append(celda("Lugar", "c-lugar", nodo("span", lugar)));
  tr.append(celda("Publicado", "c-publicado suave", nodo("span", o.propia && !o.fecha_publicacion ? "No consta fecha de publicación" : fecha(o.fecha_publicacion || o.creada_en))));

  const chevron = nodo("button", null, "chevron");
  chevron.type = "button";
  chevron.setAttribute("aria-controls", id);
  chevron.setAttribute("aria-label", `Ver por qué: ${o.titulo || "oferta sin título"}`);
  tr.append(celda("", "c-chevron", chevron));

  const td = nodo("td");
  td.colSpan = 7;
  td.append(detalle(o));
  const det = nodo("tr", null, "fila-detalle");
  det.id = id;
  det.append(td);

  const alternar = (abrir) => {
    det.hidden = !abrir;
    chevron.setAttribute("aria-expanded", String(abrir));
    if (abrir) abiertas.add(o.id);
    else abiertas.delete(o.id);
  };
  chevron.addEventListener("click", (e) => {
    e.stopPropagation();
    alternar(det.hidden);
  });
  // Clic en la fila; los de dentro (enlaces, botones, campos) no la pliegan.
  tr.addEventListener("click", (e) => {
    if (e.target.closest("a, button, input, select, textarea, label")) return;
    alternar(det.hidden);
  });
  alternar(abiertas.has(o.id));
  return [tr, det];
}

// --- Lista --------------------------------------------------------------------------------------
function pintarLista() {
  pintarVista();
  const lista = ordenar(todas.filter((o) => enRango(o) && estadoDe(o) === vista.estado));
  if (abiertas === null) abiertas = new Set(lista.slice(0, 1).map((o) => o.id));   // la primera, abierta
  $("filas").replaceChildren(...lista.flatMap(filaOferta));
  $("vacio").hidden = lista.length > 0;
  $("tabla").hidden = lista.length === 0;
  const pendientes = todas.filter((o) => o.sin_puntuar && !o.descartada).length;
  const n = lista.length === 1 ? "1 oferta" : `${lista.length} ofertas`;
  $("contador").textContent = pendientes ? `${n} · ${pendientes} sin puntuar en total` : n;
}

async function cargarLista() {
  const r = await api("/api/recomendaciones");
  if (!r.ok) return avisar(r.motivo, true);
  todas = r.datos.recomendaciones;
  sueltasHoy = r.datos.sueltas_hoy;
  maxSueltas = r.datos.max_sueltas;
  pintarLista();
}

// --- Puntuación sin botón y avance (RF-8.5, RF-8.7) ------------------------------------------------
function frasePorError(t) {
  const tope = /tope de coste/i.test(t.motivo || "");
  return (tope ? "Se ha alcanzado el tope de gasto de esta puntuación." : "La puntuación se ha detenido por un error.")
    + " Lo ya puntuado se conserva.";
}

// Sigue una tarea de puntuar: barra con su %, y la lista se recarga cada vez que sube (las notas llegan por tandas).
function seguirPuntuacion(tareaId) {
  if (dejarDeSeguir) dejarDeSeguir();
  if (!barra) barra = barraAvance($("avance"), "Puntuando ofertas");
  ultimoAvance = -1;
  dejarDeSeguir = seguirTarea(tareaId, async (p) => {
    if (barra) barra.poner(p);
    if (p > ultimoAvance) {
      ultimoAvance = p;
      await cargarLista();
    }
  }, async (t) => {
    if (barra) barra.quitar();
    barra = null;
    dejarDeSeguir = null;
    await cargarLista();
    if (t.estado === "error") avisar(frasePorError(t), true);
  });
}

// Al abrir, o al guardar «Qué buscas»: Horma decide si hay que puntuar y lo hace sola.
async function lanzarPuntuacion(motivo) {
  const r = await api("/api/recomendar", { metodo: "POST", cuerpo: { motivo } });
  if (!r.ok) return avisar(r.motivo, true);
  $("aviso-tope").textContent = r.datos.motivo === "tope" ? TEXTO_TOPE : "";
  if (r.datos.tarea_id) seguirPuntuacion(r.datos.tarea_id);
}

async function retomarOLanzar() {
  const r = await api("/api/tareas/activas?tipo=recomendar");
  if (r.ok && r.datos.tareas.length) return seguirPuntuacion(r.datos.tareas[0].id);   // RF-8.7b
  await lanzarPuntuacion("abrir");
}

// --- «Qué buscas» (RF-8.4) ---------------------------------------------------------------------
let puestos = [];     // {valor, dato, n, marcado}: los sugeridos y los que escribe ella (RF-9.3b)
let excluidos = [];

function casillaPuesto(p) {
  const l = nodo("label", null, "casilla casilla-puesto");
  const i = nodo("input");
  i.type = "checkbox";
  i.value = p.valor;
  i.checked = p.marcado;
  i.addEventListener("change", () => { p.marcado = i.checked; });
  const texto = nodo("span", `${p.valor} (${p.n})`);
  if (p.dato) texto.append(nodo("span", `Por tu perfil: ${p.dato}`, "dato-puesto"));
  l.append(i, texto);
  return l;
}

function pintarPuestos() {
  const caja = $("casillas-puestos");
  caja.replaceChildren();
  if (puestos.length > 2) {
    const masivo = nodo("div", null, "masivo");
    for (const [texto, valor] of [["Seleccionar todo", true], ["Quitar selección", false]]) {
      const b = nodo("button", texto, "secundario enlace");
      b.type = "button";
      b.addEventListener("click", () => { for (const p of puestos) p.marcado = valor; pintarPuestos(); });
      masivo.append(b);
    }
    caja.append(masivo);
  }
  if (!puestos.length) caja.append(nodo("p", "Aún no hay puestos: súbelos tú abajo o sube un CV para que Horma los proponga.", "suave"));
  caja.append(...puestos.map(casillaPuesto));
}

function pintarExcluidos() {
  const ul = $("lista-excluidos");
  ul.replaceChildren();
  if (!excluidos.length) ul.append(nodo("li", "Ninguno: no se excluye nada.", "suave"));
  excluidos.forEach((t, i) => {
    const li = nodo("li");
    const quitar = nodo("button", "Quitar", "secundario");
    quitar.type = "button";
    quitar.setAttribute("aria-label", `Quitar el término «${t}»`);
    quitar.addEventListener("click", () => { excluidos.splice(i, 1); pintarExcluidos(); });
    li.append(nodo("span", t), quitar);
    ul.append(li);
  });
}

function anadirTermino(entrada, lista, alAnadir) {
  const t = entrada.value.trim().replace(/\s+/g, " ");
  if (!t) return;
  if (!lista.some((x) => (x.valor || x).toLowerCase() === t.toLowerCase())) alAnadir(t);
  entrada.value = "";
  entrada.focus();
}

$("anadir-puesto").addEventListener("click", () => anadirTermino($("nuevo-puesto"), puestos, (t) => {
  puestos.push({ valor: t, dato: null, n: 0, marcado: true });
  pintarPuestos();
}));
$("anadir-excluido").addEventListener("click", () => anadirTermino($("nuevo-excluido"), excluidos, (t) => {
  excluidos.push(t);
  pintarExcluidos();
}));
for (const [id, boton] of [["nuevo-puesto", "anadir-puesto"], ["nuevo-excluido", "anadir-excluido"]]) {
  $(id).addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); $(boton).click(); } });
}

function pintarQueBuscas() {
  puestos = (opciones.puestos || []).map((p) => ({ ...p }));
  for (const t of guardadas.puestos || []) {   // los que ella escribió y ya no son sugeridos
    if (!puestos.some((p) => p.valor === t)) puestos.push({ valor: t, dato: null, n: 0, marcado: true });
  }
  excluidos = [...(guardadas.excluidos || [])];
  pintarPuestos();
  pintarExcluidos();
  $("grupos").replaceChildren(...GRUPOS.map(([clave, titulo]) =>
    grupoCasillas(clave, titulo, opciones.grupos[clave] || [], guardadas[clave] || [],
                  { origen: (guardadas.origen || {})[clave] })));
  $("solo-remoto").checked = guardadas.solo_remoto;
  $("solo-salario").checked = guardadas.solo_salario;
  $("sueldo-minimo").value = guardadas.sueldo_minimo === null ? "" : guardadas.sueldo_minimo;
  const vacio = GRUPOS.every(([clave]) => !(guardadas[clave] || []).length) && !puestos.length;
  $("que-buscas").open = vacio || location.hash === "#que-buscas";   // abierto si aún no hay nada guardado
}

$("formulario-busca").addEventListener("submit", async (e) => {
  e.preventDefault();
  const nuevas = { ...guardadas };
  for (const [clave] of GRUPOS) nuevas[clave] = marcadas(document.querySelector(`[data-grupo="${clave}"]`));
  nuevas.puestos = puestos.filter((p) => p.marcado).map((p) => p.valor);
  nuevas.excluidos = [...excluidos];
  nuevas.solo_remoto = $("solo-remoto").checked;
  nuevas.solo_salario = $("solo-salario").checked;
  const sueldo = $("sueldo-minimo").value.trim();
  nuevas.sueldo_minimo = sueldo === "" ? null : Number(sueldo);
  $("guardar-busca").disabled = true;
  const r = await api("/api/preferencias", { metodo: "PUT", cuerpo: nuevas });
  $("guardar-busca").disabled = false;
  if (!r.ok) return avisar(r.estado === 422 ? "Revisa el sueldo mínimo (un número positivo) y que puestos y términos no pasen de 80 letras." : r.motivo, true);
  guardadas = r.datos;
  avisar("Guardado.");
  const espera = barraAvance($("avance"), "Buscando y puntuando ofertas", true);   // para que no parezca bloqueada
  try {
    await cargarLista();
    await lanzarPuntuacion("buscar");   // sin esperar a la hora (RF-8.5)
  } finally {
    espera.quitar();
  }
});

// La vista cambia en el navegador: ninguna petición (RF-8.4c).
for (const id of ["nota-min", "nota-max", "orden", "estado"]) $(id).addEventListener("change", leerCamposVista);
$("vista").addEventListener("submit", (e) => e.preventDefault());

// Entradilla: si el perfil tiene titular, va detrás de dos puntos (RF-6.5).
async function pintarTitular() {
  const r = await api("/api/perfil");
  const titular = r.ok && r.datos.perfil && r.datos.perfil.titular && r.datos.perfil.titular.valor;
  if (titular) $("entradilla").textContent = `Ofertas ya revisadas, sin fraudes ni ofertas fantasma, para tu perfil: ${titular}`;
}

(async () => {
  if (!(await arrancar("/recomendadas"))) return;
  cabeceras();
  vista = leerVista();
  const [p, o] = await Promise.all([api("/api/preferencias"), api("/api/preferencias/opciones")]);
  if (!p.ok || !o.ok) return avisar(p.motivo || o.motivo, true);
  guardadas = p.datos;
  opciones = o.datos;
  pintarQueBuscas();
  await cargarLista();
  pintarTitular();
  await retomarOLanzar();
})();
