// Pantalla de CV base: se generan a petición, se leen y se renombran (RF-2.1b, RF-2.9).
let temporizador = null;

// Historial del CV base (RF-3.8d): versiones con sus líneas añadidas y quitadas; se puede volver a una.
function lineaVersion(l) {
  const marca = l.marca === "añadida" ? "añadida" : l.marca === "quitada" ? "quitada" : "igual";
  const p = nodo("p", null, `linea-version linea-${marca === "añadida" ? "anadida" : marca}`);
  if (marca !== "igual") p.append(nodo("span", marca === "añadida" ? "añadida: " : "quitada: ", "solo-lector"));
  p.append(l.linea === "" ? " " : l.linea);
  return p;
}

function historial(c) {
  const d = nodo("details", null, "leer");
  d.append(nodo("summary", "Historial"));
  const cuerpo = nodo("div");
  d.append(cuerpo);
  let cargado = false;
  d.addEventListener("toggle", async () => {
    if (!d.open || cargado) return;
    cargado = true;
    const r = await api(`/api/cv-base/${c.id}/versiones`);
    if (!r.ok) { cargado = false; return avisar(r.motivo, true); }
    if (!r.datos.versiones.length) {
      cuerpo.append(nodo("p", "Todavía no hay versiones anteriores: aparecen cuando editas este CV base, lo regeneras o vuelves a una versión.", "suave"));
      return;
    }
    const origenes = { edicion: "edición", restauracion: "al volver a una versión", regeneracion: "al regenerarlo" };
    for (const v of r.datos.versiones) {
      const det = nodo("details", null, "version");
      det.append(nodo("summary", `${fecha(v.creado_en)} · ${origenes[v.origen] || v.origen} · «${v.nombre}»`));
      const lineas = nodo("div", null, "lineas-version");
      lineas.append(...v.lineas.map(lineaVersion));
      const volver = nodo("button", "Volver a esta versión", "secundario");
      volver.type = "button";
      volver.addEventListener("click", async () => {
        const rr = await api(`/api/cv-base/${c.id}/versiones/${v.id}/restaurar`, { metodo: "POST", cuerpo: {} });
        if (!rr.ok) return avisar(rr.motivo, true);
        avisar("Has vuelto a esa versión; la anterior queda en el historial.");
        await cargar();
      });
      det.append(lineas, volver);
      cuerpo.append(det);
    }
  });
  return d;
}

// Qué ver de cada experiencia en este CV base (RF-5.1g): se aplica al regenerarlo.
const OPCIONES_VISIBILIDAD = [
  ["", "Automática (la de otro sector, condensada)"],
  ["completa", "Completa"],
  ["condensada", "Condensada en una línea"],
  ["oculta", "Oculta"],
];

function visibilidad(c, experiencias) {
  const d = nodo("details", null, "leer");
  d.append(nodo("summary", "Qué experiencias salen"));
  d.append(nodo("p", "Elige cómo sale cada experiencia en este CV. Se aplica cuando pulses «Regenerar»: no cambia el CV que ves ahora.", "suave"));
  const marcas = { ...(c.visibilidad || {}) };
  const lista = nodo("ul");
  experiencias.forEach((e) => {
    const li = nodo("li", null, "fila");
    const etiqueta = nodo("label", `${e.nombre}${e.periodo ? " (" + e.periodo + ")" : ""} `);
    const sel = nodo("select");
    sel.setAttribute("aria-label", `Cómo sale ${e.nombre} en este CV base`);
    OPCIONES_VISIBILIDAD.forEach(([valor, texto]) => {
      const o = nodo("option", texto);
      o.value = valor;
      sel.append(o);
    });
    sel.value = marcas[e.clave] || "";
    sel.addEventListener("change", async () => {
      const nuevas = { ...marcas };
      if (sel.value) nuevas[e.clave] = sel.value; else delete nuevas[e.clave];
      const r = await api(`/api/cv-base/${c.id}/visibilidad`, { metodo: "PUT", cuerpo: { visibilidad: nuevas } });
      if (!r.ok) { sel.value = marcas[e.clave] || ""; return avisar(r.motivo, true); }
      Object.keys(marcas).forEach((k) => delete marcas[k]);
      Object.assign(marcas, nuevas);
      avisar("Guardado. Pulsa «Regenerar» para que se aplique.");
    });
    etiqueta.append(sel);
    li.append(etiqueta);
    lista.append(li);
  });
  d.append(lista);
  return d;
}

function tarjeta(c, regenerando, experiencias) {
  const li = nodo("li", null, "tarjeta");
  const fila = nodo("div", null, "fila");
  fila.append(nodo("span", etiqueta(c.familia), "etiqueta-puesto"));
  if (c.desfasado) fila.append(nodo("span", "desfasado: has cambiado datos que este CV usa", "estado apagado"));
  li.append(fila);
  if (c.desfasado && c.cambios && c.cambios.length) {
    const cambios = nodo("details", null, "leer");
    cambios.append(nodo("summary", "Qué ha cambiado"));
    cambios.append(nodo("p", "Estas líneas de este CV ya no están como estaban en tu perfil:", "suave"));
    const ul = nodo("ul");
    c.cambios.forEach((l) => ul.append(nodo("li", l)));
    cambios.append(ul);
    li.append(cambios);
  }
  if (regenerando) li.append(nodo("p", "Regenerando este CV… puede tardar un minuto.", "suave"));
  if (c.motivo_error) li.append(nodo("p", `No se pudo regenerar (este CV se queda como estaba): ${c.motivo_error}`, "alerta"));
  li.append(nodo("h3", c.nombre));
  li.append(nodo("p", `Perfil versión ${c.perfil_version} · ${fecha(c.creado_en)}`, "suave"));
  const detalle = nodo("details", null, "leer");
  detalle.append(nodo("summary", "Ver el CV"));
  detalle.append(cvBonito(c.contenido));
  li.append(detalle);
  if (experiencias.length) li.append(visibilidad(c, experiencias));
  li.append(historial(c));
  const acciones = nodo("div", null, "fila");
  const modificar = nodo("button", "Modificar", "secundario");
  modificar.type = "button";
  modificar.addEventListener("click", () => {
    acciones.hidden = true;
    const f = nodo("form", null, "editor");
    const i = nodo("input");
    i.type = "text";
    i.maxLength = 80;
    i.required = true;
    i.value = c.nombre;
    i.setAttribute("aria-label", "Nombre del CV base");
    const t = nodo("textarea");
    t.rows = 18;
    t.required = true;
    t.maxLength = 20000;
    t.value = c.contenido;
    t.setAttribute("aria-label", "Texto del CV base");
    const ayuda = nodo("p", "Puedes cambiar el nombre y el texto. Los títulos empiezan por ## y las listas por -. Lo que escribas es tuyo: Horma no lo vuelve a comprobar contra tu CV.", "suave");
    const cancelar = nodo("button", "Cancelar", "secundario");
    cancelar.type = "button";
    cancelar.addEventListener("click", () => { f.remove(); acciones.hidden = false; });
    const fila = nodo("div", null, "fila");
    fila.append(nodo("button", "Guardar"), cancelar);
    f.append(i, t, ayuda, fila);
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const r = await api(`/api/cv-base/${c.id}`, { metodo: "PATCH", cuerpo: { nombre: i.value, contenido: t.value } });
      if (!r.ok) return avisar(r.motivo, true);
      avisar("CV base guardado.");
      await cargar();
    });
    li.append(f);
    t.focus();
  });
  const eliminar = nodo("button", "Eliminar", "secundario");
  eliminar.type = "button";
  eliminar.addEventListener("click", () => {
    acciones.hidden = true;
    const conf = nodo("div", null, "fila editor");
    const si = nodo("button", "Eliminar", "secundario");
    si.type = "button";
    const no = nodo("button", "Cancelar", "secundario");
    no.type = "button";
    no.addEventListener("click", () => { conf.remove(); acciones.hidden = false; });
    si.addEventListener("click", async () => {
      const r = await api(`/api/cv-base/${c.id}`, { metodo: "DELETE" });
      if (!r.ok) return avisar(r.motivo, true);
      avisar("CV base eliminado.");
      await cargar();
    });
    conf.append(nodo("span", "¿Eliminar este CV base? No se puede deshacer."), si, no);
    li.append(conf);
    no.focus();
  });
  const copiar = nodo("button", "Copiar texto", "secundario");
  copiar.type = "button";
  copiar.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(c.contenido);
      avisar("Copiado.");
    } catch (e) {
      avisar("No se pudo copiar: abre «Ver el CV» y selecciona el texto.", true);
    }
  });
  const regenerar = nodo("button", "Regenerar", c.desfasado ? "" : "secundario");
  regenerar.type = "button";
  regenerar.disabled = regenerando;
  regenerar.title = "Vuelve a generar este CV con tu perfil actual; la versión anterior queda en el historial.";
  regenerar.addEventListener("click", async () => {
    regenerar.disabled = true;
    const r = await api(`/api/cv-base/${c.id}/regenerar`, { metodo: "POST", cuerpo: {} });
    if (!r.ok) {
      regenerar.disabled = false;
      return avisar(r.motivo, true);
    }
    await cargar();
  });
  acciones.append(regenerar, modificar, copiar, eliminar);
  li.append(acciones);
  return li;
}

async function cargar() {
  clearTimeout(temporizador);
  const r = await api("/api/cv-base");
  if (!r.ok) return avisar(r.motivo, true);
  const { cv_base: lista, avisos, generando, regenerando = [], experiencias = [] } = r.datos;
  $("lista").replaceChildren(...lista.map((c) => tarjeta(c, regenerando.includes(c.id), experiencias)));
  $("vacio").hidden = lista.length > 0 || generando;
  $("generar").disabled = generando;
  $("avisos").replaceChildren(...avisos.map((a) => {
    const li = nodo("li", null, "tarjeta");
    li.append(nodo("span", a.estado === "error" ? "no se pudo generar" : "rechazado", "estado error"));
    li.append(nodo("h3", a.nombre));
    li.append(nodo("p", a.motivo || "Sin motivo registrado.", "alerta"));
    return li;
  }));
  if (generando || regenerando.length) {
    avisar(generando ? "Generando tus CV base… puede tardar un minuto." : "Regenerando… puede tardar un minuto.");
    temporizador = setTimeout(cargar, 3000);
  }
}

$("generar").addEventListener("click", async () => {
  $("generar").disabled = true;
  avisar("Encolando…");
  const r = await api("/api/cv-base", { metodo: "POST" });
  if (!r.ok) {
    $("generar").disabled = false;
    return avisar(r.motivo, true);
  }
  await cargar();
});

(async () => {
  if (!(await arrancar("/cv-base"))) return;
  await cargar();
})();
