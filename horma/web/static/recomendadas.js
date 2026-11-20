// Pantalla de ofertas recomendadas (RF-2.8, 2.15b, 2.15c, 6.5). Cambiar un filtro solo reordena y filtra
// lo ya puntuado: guarda las preferencias y vuelve a pedir la lista; nunca llama al modelo.
const AYUDA = [
  ["Oferta", "El título de la oferta y la empresa que la publica. El enlace lleva a la oferta original."],
  ["Puesto", "El tipo de trabajo según la clasificación de Horma, sea cual sea el sector."],
  ["Compatibilidad", "Nota de 0 a 100 de lo bien que encajan tu experiencia y formación con lo que pide la oferta. Orienta, no decide. Despliega la fila para ver por qué."],
  ["Salario", "Tal como lo dice la oferta, sin convertirlo. Si no lo publica, lo verás indicado."],
  ["Lugar", "El país donde está el puesto, o «Remoto»."],
  ["Publicado", "El día en que se publicó la oferta (o, si no lo dice, el día en que llegó a Horma)."],
];
const MAX_PUNTUANDO = 30;  // sondeos de 3 s tras pulsar «Recomendar»
let guardadas = null;
let opciones = null;
let sondeos = 0;
let sondeo = null;
let abiertas = null;       // ids de las filas desplegadas; null hasta el primer pintado (entonces, solo la primera)

function urlSegura(u) {
  return typeof u === "string" && /^https?:\/\//i.test(u);
}

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

// Contenido de la fila desplegada (RF-6.5d): a la izquierda el porqué; a la derecha, las dos acciones.
function detalle(o) {
  const cont = nodo("div", null, "detalle");
  const izq = nodo("div", null, "porque-cuerpo");
  const dch = nodo("div", null, "acciones");
  cont.append(izq);
  const pintar = () => {
    izq.replaceChildren(nodo("span", "Por qué te la recomendamos", "etiqueta-mono"));
    if (o.sin_puntuar) {
      izq.append(nodo("p", "Esta oferta todavía no tiene nota. Pulsa «Recomendar» para calcularla."));
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
  if (o.sin_puntuar) return cont;

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
  dch.append(corregir, accionesCandidatura(o, dch), nodo("p", "Horma elige tu CV base más adecuado.", "suave"));
  cont.append(dch);
  return cont;
}

function filaOferta(o) {
  const id = `detalle-${o.id}`;
  const tr = nodo("tr", null, "fila-oferta");
  const titulo = urlSegura(o.url) ? nodo("a", o.titulo || "Sin título") : nodo("span", o.titulo || "Sin título");
  if (urlSegura(o.url)) {
    titulo.href = o.url;
    titulo.target = "_blank";
    titulo.rel = "noopener noreferrer";
  }
  titulo.classList.add("titulo-oferta");
  const celdaOferta = celda("Oferta", "c-oferta", titulo, nodo("span", o.empresa || "Empresa sin indicar", "suave bloque"));
  if (o.atribucion) celdaOferta.append(nodo("span", o.atribucion, "suave bloque"));  // cita de la fuente (RF-5.5d)
  if (o.propia) {  // las que añade la usuaria salen siempre, con su marca y lo que vio el auditor (RF-5.3e)
    celdaOferta.append(nodo("span", `Añadida por ti · analizada el ${fecha(o.analizada_en)}`, "estado bien bloque"));
    if (o.aviso_auditor) celdaOferta.append(nodo("span", o.aviso_auditor, "estado error bloque"));
  }
  tr.append(celdaOferta);
  tr.append(celda("Puesto", "c-puesto", nodo("span", etiqueta(o.familia), `etiqueta-puesto ${tonoDe(o.familia)}`),
                  nodo("span", etiqueta(o.nivel), "suave")));

  const comp = celda("Compatibilidad", "c-compat");
  if (o.sin_puntuar) {
    comp.append(nodo("em", "Sin puntuar", "suave"));
  } else {
    const barra = nodo("div", null, "barra-compat");
    barra.setAttribute("role", "meter");
    barra.setAttribute("aria-valuenow", String(o.nota));
    barra.setAttribute("aria-valuemin", "0");
    barra.setAttribute("aria-valuemax", "100");
    barra.setAttribute("aria-label", "Compatibilidad");
    const relleno = nodo("span");
    relleno.style.width = `${Math.max(0, Math.min(100, o.nota))}%`;   // por CSSOM: la CSP no permite style= en el HTML
    barra.append(relleno);
    const fila = nodo("div", null, "nota");
    fila.append(barra, nodo("span", String(o.nota), "numero"));
    comp.append(fila);
  }
  tr.append(comp);

  tr.append(celda("Salario", "c-salario", nodo("span", o.salario || "No publicado", o.salario ? "" : "suave")));
  const lugar = [o.remoto ? "Remoto" : null, o.pais].filter(Boolean).join(" · ") || o.ubicacion || "—";
  tr.append(celda("Lugar", "c-lugar", nodo("span", lugar)));
  tr.append(celda("Publicado", "c-publicado suave", nodo("span", fecha(o.fecha_publicacion || o.creada_en))));

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

// --- Filtros ------------------------------------------------------------------------------------
function pintarFiltros() {
  // En móvil solo se ve el primer grupo; el resto cuelga de «Más filtros» (clase .mas).
  $("grupos").replaceChildren(...GRUPOS.map(([clave, titulo], i) => {
    const g = grupoCasillas(clave, titulo, opciones.grupos[clave] || [], guardadas[clave] || [], { plegable: true });
    if (i > 0) g.classList.add("mas");
    return g;
  }));
  $("solo-remoto").checked = guardadas.solo_remoto;
  $("solo-salario").checked = guardadas.solo_salario;
  $("sueldo-minimo").value = guardadas.sueldo_minimo === null ? "" : guardadas.sueldo_minimo;
  $("orden").value = guardadas.orden;
  $("rango-min").value = guardadas.rango_min;
  $("rango-max").value = guardadas.rango_max;
}

function leerFiltros() {
  const p = { ...guardadas };
  for (const [clave] of GRUPOS) p[clave] = marcadas(document.querySelector(`[data-grupo="${clave}"]`));
  p.solo_remoto = $("solo-remoto").checked;
  p.solo_salario = $("solo-salario").checked;
  const sueldo = $("sueldo-minimo").value.trim();
  p.sueldo_minimo = sueldo === "" ? null : Number(sueldo);
  p.orden = $("orden").value;
  p.rango_min = Number($("rango-min").value === "" ? 0 : $("rango-min").value);
  p.rango_max = Number($("rango-max").value === "" ? 100 : $("rango-max").value);
  return p;
}

async function aplicarFiltros() {
  const nuevas = leerFiltros();
  const r = await api("/api/preferencias", { metodo: "PUT", cuerpo: nuevas });
  if (!r.ok) {
    return avisar(r.estado === 422 ? "Revisa los filtros: el mínimo no puede superar al máximo y el sueldo debe ser positivo." : r.motivo, true);
  }
  guardadas = r.datos;
  avisar("");
  await cargarLista();
}

// --- Lista --------------------------------------------------------------------------------------
async function cargarLista() {
  const r = await api("/api/recomendaciones");
  if (!r.ok) return avisar(r.motivo, true);
  const { total, sin_puntuar: pendientes, recomendaciones } = r.datos;
  if (abiertas === null) abiertas = new Set(recomendaciones.slice(0, 1).map((o) => o.id));   // la primera, abierta
  $("filas").replaceChildren(...recomendaciones.flatMap(filaOferta));
  $("vacio").hidden = total > 0;
  $("tabla").hidden = total === 0;
  const n = total === 1 ? "1 oferta" : `${total} ofertas`;
  $("contador").textContent = pendientes ? `${n} · ${pendientes} sin puntuar` : n;
  $("recomendar").disabled = pendientes === 0;
  if (pendientes === 0) $("recomendar").classList.remove("ocupado");
  return pendientes;
}

async function sondear() {
  clearTimeout(sondeo);
  const pendientes = await cargarLista();
  sondeos += 1;
  if (pendientes && sondeos < MAX_PUNTUANDO) {
    sondeo = setTimeout(sondear, 3000);
  } else {
    avisar(pendientes ? "Aún quedan ofertas sin puntuar: puede que sigan en marcha. Vuelve en un rato." : "Listo: todo puntuado.");
  }
}

$("recomendar").addEventListener("click", async () => {
  $("recomendar").disabled = true;
  $("recomendar").classList.add("ocupado");
  avisar("Puntuando lo que falta… se actualizará sola.");
  const r = await api("/api/recomendar", { metodo: "POST" });
  if (!r.ok) {
    $("recomendar").disabled = false;
    return avisar(r.motivo, true);
  }
  sondeos = 0;
  sondeo = setTimeout(sondear, 3000);
});

// «Más filtros» / «Menos filtros» (solo se ve en móvil).
$("mas-filtros").addEventListener("click", () => {
  const plegado = $("filtros").classList.toggle("plegados");
  $("mas-filtros").setAttribute("aria-expanded", String(!plegado));
  $("mas-filtros").textContent = plegado ? "Más filtros" : "Menos filtros";
});

// Los filtros solo se aplican al pulsar «Buscar» (o Intro en un campo).
$("filtros").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("buscar").disabled = true;
  await aplicarFiltros();
  $("buscar").disabled = false;
});

// Entradilla: si el perfil tiene titular, va detrás de dos puntos (RF-6.5).
async function pintarTitular() {
  const r = await api("/api/perfil");
  const titular = r.ok && r.datos.perfil && r.datos.perfil.titular && r.datos.perfil.titular.valor;
  if (titular) $("entradilla").textContent = `Ofertas ya revisadas, sin fraudes ni ofertas fantasma, para tu perfil: ${titular}`;
}

(async () => {
  if (!(await arrancar("/recomendadas"))) return;
  cabeceras();
  const [p, o] = await Promise.all([api("/api/preferencias"), api("/api/preferencias/opciones")]);
  if (!p.ok || !o.ok) return avisar(p.motivo || o.motivo, true);
  guardadas = p.datos;
  opciones = o.datos;
  pintarFiltros();
  await cargarLista();
  pintarTitular();
})();
