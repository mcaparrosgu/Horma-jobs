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
      cuerpo.append(nodo("p", "Todavía no hay versiones anteriores: aparecen cuando editas este CV base o vuelves a una versión.", "suave"));
      return;
    }
    const origenes = { edicion: "edición", restauracion: "al volver a una versión" };
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

function tarjeta(c) {
  const li = nodo("li", null, "tarjeta");
  const fila = nodo("div", null, "fila");
  fila.append(nodo("span", etiqueta(c.familia), "etiqueta-puesto"));
  if (c.desfasado) fila.append(nodo("span", "desfasado: tu perfil ha cambiado desde entonces", "estado apagado"));
  li.append(fila);
  li.append(nodo("h3", c.nombre));
  li.append(nodo("p", `Perfil versión ${c.perfil_version} · ${fecha(c.creado_en)}`, "suave"));
  const detalle = nodo("details", null, "leer");
  detalle.append(nodo("summary", "Ver el CV"));
  detalle.append(cvBonito(c.contenido));
  li.append(detalle);
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
  acciones.append(modificar, copiar, eliminar);
  li.append(acciones);
  return li;
}

async function cargar() {
  clearTimeout(temporizador);
  const r = await api("/api/cv-base");
  if (!r.ok) return avisar(r.motivo, true);
  const { cv_base: lista, avisos, generando } = r.datos;
  $("lista").replaceChildren(...lista.map(tarjeta));
  $("vacio").hidden = lista.length > 0 || generando;
  $("generar").disabled = generando;
  $("avisos").replaceChildren(...avisos.map((a) => {
    const li = nodo("li", null, "tarjeta");
    li.append(nodo("span", a.estado === "error" ? "no se pudo generar" : "rechazado", "estado error"));
    li.append(nodo("h3", a.nombre));
    li.append(nodo("p", a.motivo || "Sin motivo registrado.", "alerta"));
    return li;
  }));
  if (generando) {
    avisar("Generando tus CV base… puede tardar un minuto.");
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
