// Pantalla de CV base: se generan a petición, se leen y se renombran (RF-2.1b, RF-2.9).
let temporizador = null;

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
  detalle.append(nodo("pre", c.contenido, "cv-texto"));
  li.append(detalle);
  const acciones = nodo("div", null, "fila");
  const renombrar = nodo("button", "Cambiar nombre", "secundario");
  renombrar.type = "button";
  renombrar.addEventListener("click", () => {
    acciones.hidden = true;
    const f = nodo("form", null, "fila editor");
    const i = nodo("input");
    i.type = "text";
    i.maxLength = 80;
    i.required = true;
    i.value = c.nombre;
    i.setAttribute("aria-label", "Nombre del CV base");
    const cancelar = nodo("button", "Cancelar", "secundario");
    cancelar.type = "button";
    cancelar.addEventListener("click", () => { f.remove(); acciones.hidden = false; });
    f.append(i, nodo("button", "Guardar"), cancelar);
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const r = await api(`/api/cv-base/${c.id}`, { metodo: "PATCH", cuerpo: { nombre: i.value } });
      if (!r.ok) return avisar(r.motivo, true);
      avisar("Nombre cambiado.");
      await cargar();
    });
    li.append(f);
    i.focus();
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
  acciones.append(renombrar, copiar);
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
