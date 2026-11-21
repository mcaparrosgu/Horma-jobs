// Tablero de candidaturas (RF-3.10): una columna por estado; «Cerradas» va plegada.
// Un solo estado visible por candidatura (RF-10.7): las columnas del servidor se reagrupan aquí.
const COLUMNAS = [...ESTADOS_VISIBLES, "No se pudo preparar"];
let temporizador = null;

function tarjetaCandidatura(c) {
  const li = nodo("li", null, "tarjeta");
  const enlace = nodo("a", c.titulo || "Oferta sin título", "titulo-oferta");
  enlace.href = `/candidaturas/${c.id}`;
  li.append(nodo("h3"));
  li.firstChild.append(enlace);
  li.append(nodo("p", c.empresa || "Empresa sin indicar"));
  const visible = estadoVisible(c.estado, c.preparacion);
  li.append(nodo("span", visible, visible === "No se pudo preparar" ? "estado error" : visible === "Preparando" ? "estado apagado" : "estado bien"));
  if (c.estado === "cerrada" && c.motivo_cierre) li.append(nodo("span", MOTIVOS_CIERRE[c.motivo_cierre] || c.motivo_cierre, "estado apagado"));
  li.append(nodo("p", `Último cambio: ${fecha(c.actualizado_en)}`, "suave"));
  return li;
}

function columna(col) {
  const n = col.candidaturas.length;
  const titulo = `${col.estado} (${n})`;
  const lista = nodo("ul", null, "lista");
  lista.append(...col.candidaturas.map(tarjetaCandidatura));
  if (!n) lista.append(nodo("li", "Ninguna.", "suave"));
  if (col.estado === "Cerrada") {
    const d = nodo("details", null, "columna columna-cerrada");
    d.append(nodo("summary", titulo), lista);
    return d;
  }
  const s = nodo("section", null, "columna");
  s.append(nodo("h2", titulo), lista);
  return s;
}

async function cargar() {
  clearTimeout(temporizador);
  const r = await api("/api/candidaturas");
  if (!r.ok) return avisar(r.motivo, true);
  const { total, columnas } = r.datos;
  const todas = columnas.flatMap((c) => c.candidaturas);
  $("vacio").textContent = TEXTOS.sinCandidaturas;
  $("vacio").hidden = total > 0;
  const grupos = COLUMNAS.map((estado) => ({
    estado, candidaturas: todas.filter((c) => estadoVisible(c.estado, c.preparacion) === estado),
  })).filter((g) => g.candidaturas.length || g.estado !== "No se pudo preparar");
  $("tablero").replaceChildren(...grupos.map(columna));
  if (columnas.some((c) => c.candidaturas.some((x) => x.preparacion === "en_curso"))) {
    temporizador = setTimeout(cargar, 3000);
  }
}

(async () => {
  if (!(await arrancar("/candidaturas"))) return;
  await cargar();
})();
