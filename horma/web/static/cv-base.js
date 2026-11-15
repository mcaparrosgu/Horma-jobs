// Pantalla de CV base: se generan a petición, se leen y se renombran (RF-2.1b, RF-2.9).
let temporizador = null;

// Dibuja el Markdown del CV como un documento (sin HTML pegado: todo va con textContent).
function cvBonito(md) {
  const hoja = nodo("article", null, "cv-hoja");
  let lista = null;
  const lineas = md.split("\n");
  let primero = true;
  for (const crudo of lineas) {
    const linea = crudo.trim();
    if (!linea) { lista = null; continue; }
    const t = linea.match(/^(#{1,6})\s+(.*)$/);
    if (t) {
      lista = null;
      hoja.append(nodo(primero ? "h4" : "h5", t[2].replace(/[*_`]/g, ""), primero ? "cv-nombre" : "cv-seccion"));
      primero = false;
      continue;
    }
    primero = false;
    const v = linea.match(/^(?:[-*+•]|\d+[.)])\s+(.*)$/);
    if (v) {
      if (!lista) { lista = nodo("ul", null, "cv-lista"); hoja.append(lista); }
      lista.append(nodo("li", v[1].replace(/[*_`]/g, "")));
      continue;
    }
    lista = null;
    const partes = linea.replace(/[*_`]/g, "").split(/\s[·|]\s/);
    const p = nodo("p", null, "cv-linea");
    p.append(nodo("strong", partes[0]));
    if (partes.length > 1) p.append(nodo("span", partes.slice(1).join(" · "), "cv-detalle"));
    hoja.append(p);
  }
  return hoja;
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
