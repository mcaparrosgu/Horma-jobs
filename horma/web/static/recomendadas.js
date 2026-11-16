// Pantalla de ofertas recomendadas (RF-2.8, 2.15b, 2.15c). Cambiar un filtro solo reordena y filtra
// lo ya puntuado: guarda las preferencias y vuelve a pedir la lista; nunca llama al modelo.
const AYUDA = [
  ["Oferta", "El título de la oferta y la empresa que la publica. El enlace lleva a la oferta original."],
  ["Puesto", "El tipo de trabajo según la clasificación de Horma, sea cual sea el sector."],
  ["Compatibilidad", "Nota de 0 a 100 de lo bien que encajan tu experiencia y formación con lo que pide la oferta. Orienta, no decide. «Por qué» explica la nota."],
  ["Condiciones", "Cómo encajan las condiciones de trabajo (alto, medio o bajo) con lo que buscas, y el nivel que pide la oferta."],
  ["Salario", "Tal como lo dice la oferta, sin convertirlo. Si no lo publica, lo verás indicado."],
  ["Lugar", "El país donde está el puesto, o «Remoto»."],
  ["Publicado", "El día en que se publicó la oferta (o, si no lo dice, el día en que llegó a Horma)."],
  ["Candidatura", "Horma elige tu CV base más adecuado y prepara el CV adaptado y la carta. Tú los revisas y los apruebas."],
];
const MAX_PUNTUANDO = 30;  // sondeos de 3 s tras pulsar «Recomendar»
let guardadas = null;
let opciones = null;
let esperaFiltro = null;
let sondeos = 0;
let sondeo = null;

function urlSegura(u) {
  return typeof u === "string" && /^https?:\/\//i.test(u);
}

function colorDe(texto) {
  let h = 0;
  for (const c of String(texto || "")) h = (h * 31 + c.charCodeAt(0)) % 6;
  return `color-${h}`;
}

function cabeceras() {
  const fila = $("cabeceras");
  for (const [nombre, ayuda] of AYUDA) {
    const th = nodo("th");
    th.scope = "col";
    th.append(nodo("span", nombre));
    const q = nodo("button", "?", "ayuda secundario");
    q.type = "button";
    q.setAttribute("aria-label", `Qué significa «${nombre}»`);
    q.setAttribute("aria-expanded", "false");
    const texto = nodo("span", ayuda, "ayuda-texto");
    texto.hidden = true;
    q.addEventListener("click", () => {
      texto.hidden = !texto.hidden;
      q.setAttribute("aria-expanded", String(!texto.hidden));
    });
    th.append(q, texto);
    fila.append(th);
  }
}

function celda(rotulo, ...hijos) {
  const td = nodo("td");
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
  cancelar.addEventListener("click", alTerminar);
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

function porque(o) {
  const d = nodo("details", null, "porque");
  d.append(nodo("summary", "Por qué"));
  const cuerpo = nodo("div", null, "porque-cuerpo");
  const pintar = () => {
    cuerpo.replaceChildren();
    if (o.retirada) {
      cuerpo.append(nodo("p", "Se ha retirado la explicación porque no cumplía las reglas de Horma. La nota sigue siendo válida.", "suave"));
    } else {
      cuerpo.append(nodo("p", o.explicacion));
      if (o.cita_perfil) cuerpo.append(nodo("p", `De tu perfil: «${o.cita_perfil}»`, "suave"));
      if (o.cita_oferta) cuerpo.append(nodo("p", `De la oferta: «${o.cita_oferta}»`, "suave"));
    }
    if (o.desfasado) cuerpo.append(nodo("p", "Esta nota se calculó con una versión anterior de tu perfil.", "suave"));
    if (o.correccion) {
      const c = o.correccion;
      const nota = c.nota !== null && c.nota !== undefined ? ` (nota que propones: ${c.nota})` : "";
      cuerpo.append(nodo("p", `Tu corrección${nota}: ${c.comentario}`, "origen"));
    }
    const boton = nodo("button", o.correccion ? "Modificar de nuevo" : "Modificar", "secundario");
    boton.type = "button";
    boton.addEventListener("click", () => {
      boton.hidden = true;
      const f = formularioCorreccion(o, (guardada) => (guardada ? pintar() : (f.remove(), (boton.hidden = false))));
      cuerpo.append(f);
    });
    cuerpo.append(boton);
  };
  pintar();
  d.append(cuerpo);
  return d;
}

// «Preparar candidatura» (RF-3.7b): crea la candidatura y lleva a ella; el CV base lo elige Horma.
function celdaCandidatura(o) {
  const td = celda("Candidatura");
  const b = nodo("button", "Preparar candidatura", "secundario");
  b.type = "button";
  let repetir = false;
  b.addEventListener("click", async () => {
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
      td.append(a);
    }
    if (r.estado === 409 && /CV base/i.test(r.motivo || "") && !td.querySelector("a")) {
      const a = nodo("a", "Generar CV base", "bloque");
      a.href = "/cv-base";
      td.append(a);
    }
  });
  td.append(b);
  return td;
}

function filaOferta(o) {
  const tr = nodo("tr", null, "fila-oferta");
  const titulo = urlSegura(o.url) ? nodo("a", o.titulo || "Sin título") : nodo("span", o.titulo || "Sin título");
  if (urlSegura(o.url)) {
    titulo.href = o.url;
    titulo.target = "_blank";
    titulo.rel = "noopener noreferrer";
  }
  titulo.classList.add("titulo-oferta");
  tr.append(celda("Oferta", titulo, nodo("span", o.empresa || "Empresa sin indicar", "suave bloque")));
  tr.append(celda("Puesto", nodo("span", etiqueta(o.familia), `etiqueta-puesto ${colorDe(o.familia)}`)));

  const comp = celda("Compatibilidad");
  if (o.sin_puntuar) {
    comp.append(nodo("span", "sin puntuar", "estado apagado"));
  } else {
    const barra = nodo("progress");
    barra.max = 100;
    barra.value = o.nota;
    barra.setAttribute("aria-label", `Compatibilidad ${o.nota} de 100`);
    const fila = nodo("div", null, "nota");
    fila.append(barra, nodo("strong", String(o.nota)));
    comp.append(fila, porque(o));
  }
  tr.append(comp);

  const nivelCond = o.sin_puntuar ? null : o.condiciones;
  tr.append(celda("Condiciones",
    nivelCond ? nodo("span", etiqueta(nivelCond), `estado cond-${nivelCond}`) : nodo("span", "—", "suave"),
    nodo("span", etiqueta(o.nivel), "suave bloque")));
  tr.append(celda("Salario", nodo("span", o.salario || "No publicado", o.salario ? "" : "suave")));
  const lugar = [o.remoto ? "Remoto" : null, o.pais].filter(Boolean).join(" · ") || o.ubicacion || "—";
  tr.append(celda("Lugar", nodo("span", lugar)));
  tr.append(celda("Publicado", nodo("span", fecha(o.fecha_publicacion || o.creada_en))));
  tr.append(celdaCandidatura(o));
  return tr;
}

// --- Filtros ------------------------------------------------------------------------------------
function pintarFiltros() {
  $("grupos").replaceChildren(...GRUPOS.map(([clave, titulo]) =>
    grupoCasillas(clave, titulo, opciones.grupos[clave] || [], guardadas[clave] || [],
                  { plegable: true, alCambiar: cambioDeFiltro })));
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

function cambioDeFiltro() {
  clearTimeout(esperaFiltro);
  esperaFiltro = setTimeout(aplicarFiltros, 400);
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
  $("filas").replaceChildren(...recomendaciones.map(filaOferta));
  $("vacio").hidden = total > 0;
  $("tabla").hidden = total === 0;
  const n = total === 1 ? "1 oferta" : `${total} ofertas`;
  $("contador").textContent = pendientes ? `${n} · ${pendientes} sin puntuar` : n;
  $("recomendar").disabled = pendientes === 0;
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
  avisar("Puntuando lo que falta… se actualizará sola.");
  const r = await api("/api/recomendar", { metodo: "POST" });
  if (!r.ok) {
    $("recomendar").disabled = false;
    return avisar(r.motivo, true);
  }
  sondeos = 0;
  sondeo = setTimeout(sondear, 3000);
});

$("filtros").addEventListener("submit", (e) => e.preventDefault());
for (const id of ["solo-remoto", "solo-salario", "sueldo-minimo", "orden", "rango-min", "rango-max"]) {
  $(id).addEventListener("change", cambioDeFiltro);
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
})();
