// Tablero de candidaturas (RF-3.10): una columna por estado; «Cerradas» va plegada.
const TITULOS = {
  borrador: "Borrador", aprobada: "Aprobadas", enviada: "Enviadas", entrevista: "Entrevista", cerrada: "Cerradas",
};
const MOTIVOS = { rechazo: "Rechazo", descartada: "Descartada", retirada: "Retirada" };
let temporizador = null;

function tarjetaCandidatura(c) {
  const li = nodo("li", null, "tarjeta");
  const enlace = nodo("a", c.titulo || "Oferta sin título", "titulo-oferta");
  enlace.href = `/candidaturas/${c.id}`;
  li.append(nodo("h3"));
  li.firstChild.append(enlace);
  li.append(nodo("p", c.empresa || "Empresa sin indicar"));
  if (c.preparacion === "en_curso") li.append(nodo("span", "preparando…", "estado apagado"));
  else if (c.preparacion === "error") li.append(nodo("span", "no se pudo preparar", "estado error"));
  else if (c.te_toca_revisar) li.append(nodo("span", "Te toca revisar", "estado cond-medio"));
  if (c.estado === "cerrada" && c.motivo_cierre) li.append(nodo("span", MOTIVOS[c.motivo_cierre] || c.motivo_cierre, "estado apagado"));
  li.append(nodo("p", `Último cambio: ${fecha(c.actualizado_en)}`, "suave"));
  return li;
}

function columna(col) {
  const n = col.candidaturas.length;
  const titulo = `${TITULOS[col.estado] || col.estado} (${n})`;
  const lista = nodo("ul", null, "lista");
  lista.append(...col.candidaturas.map(tarjetaCandidatura));
  if (!n) lista.append(nodo("li", "Ninguna.", "suave"));
  if (col.estado === "cerrada") {
    const d = nodo("details", null, "columna columna-cerrada");
    d.append(nodo("summary", titulo), lista);
    return d;
  }
  const s = nodo("section", null, "columna");
  s.append(nodo("h2", titulo, "subtitulo"), lista);
  return s;
}

async function cargar() {
  clearTimeout(temporizador);
  const r = await api("/api/candidaturas");
  if (!r.ok) return avisar(r.motivo, true);
  const { total, columnas } = r.datos;
  $("vacio").hidden = total > 0;
  $("tablero").replaceChildren(...columnas.map(columna));
  if (columnas.some((c) => c.candidaturas.some((x) => x.preparacion === "en_curso"))) {
    temporizador = setTimeout(cargar, 3000);
  }
}

(async () => {
  if (!(await arrancar("/candidaturas"))) return;
  await cargar();
})();
