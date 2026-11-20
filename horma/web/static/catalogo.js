// Admin › Catálogo (RF-8.2): las ofertas comunes con su auditoría y su taxonomía. Todo el texto que viene de
// ofertas se pinta con textContent: nunca como HTML.
let temporizador = null;

const MOTIVOS_FANTASMA = { sin_fecha: "sin fecha", repetida: "repetida", generica: "genérica" };

function etiquetas(o) {
  const fila = nodo("div", null, "fila");
  fila.append(nodo("span", o.estado, o.estado === "error" ? "estado error" : "estado"));
  if (o.estado !== "procesada") return fila;
  if (o.recomendable) fila.append(nodo("span", "recomendable", "estado bien"));
  if (o.fraude) fila.append(nodo("span", "posible fraude", "estado error"));
  if (o.fantasma) fila.append(nodo("span", "posible fantasma", "estado apagado"));
  if (o.empresa_validada === false) fila.append(nodo("span", "dominio sin validar", "estado apagado"));
  return fila;
}

function tarjeta(o) {
  const li = nodo("li", null, "tarjeta");
  li.append(etiquetas(o));
  if (o.propia) li.append(nodo("span", "Añadida por una usuaria", "estado bien"));
  li.append(nodo("h3", o.titulo || "Oferta sin procesar todavía"));
  const detalle = [o.empresa, o.ubicacion, o.contrato].filter(Boolean).join(" · ");
  if (detalle) li.append(nodo("p", detalle));
  if (o.salario_minimo !== null || o.salario_maximo !== null) {
    const rango = [o.salario_minimo, o.salario_maximo].filter((v) => v !== null).join(" – ");
    li.append(nodo("p", `Salario: ${rango} ${o.salario_moneda || ""}`.trim()));
  }
  if (o.salario_publicado === false && o.frase_pedir_salario) {
    li.append(nodo("p", `Sin salario publicado. Para pedirlo: «${o.frase_pedir_salario}»`, "suave"));
  }
  if (nombreModalidad(o.modalidad)) li.append(nodo("p", nombreModalidad(o.modalidad)));
  if (o.idiomas && o.idiomas.length) li.append(nodo("p", `Idiomas: ${o.idiomas.join(", ")}`));
  if (o.sector) {
    const tax = [o.sector, o.familia, o.nivel].filter(Boolean).join(" · ");
    li.append(nodo("p", `Clasificación: ${tax}`, "suave"));
  }
  if (o.stack && o.stack.length) li.append(nodo("p", `Stack: ${o.stack.join(", ")}`, "suave"));
  if (o.fantasma && o.motivos_fantasma && o.motivos_fantasma.length) {
    li.append(nodo("p", `Fantasma: ${o.motivos_fantasma.map((m) => MOTIVOS_FANTASMA[m] || m).join(", ")}`, "suave"));
  }
  if (o.fraude && o.senales_fraude) {
    for (const s of o.senales_fraude) li.append(nodo("p", `Señal de fraude: «${s}»`, "alerta"));
  }
  if (o.fuente) li.append(nodo("p", `Fuente: ${o.fuente}`, "suave"));
  if (o.instrucciones_embebidas && o.instrucciones_embebidas.length) {
    li.append(nodo("p", `Instrucciones detectadas y no ejecutadas: ${o.instrucciones_embebidas.length}`, "alerta"));
  }
  if (o.estado === "error" && o.motivo_error) li.append(nodo("p", o.motivo_error, "alerta"));
  const original = nodo("button", "Ver oferta original", "secundario");
  original.type = "button";
  original.addEventListener("click", () => verOriginal(o.id));
  li.append(original);
  return li;
}

async function cargarContador() {
  const r = await api("/ofertas/total");
  if (!r.ok) return;
  const { total, por_estado } = r.datos;
  const desglose = Object.entries(por_estado).map(([e, n]) => `${n} ${e}`).join(" · ");
  $("contador").textContent = `Ofertas en total: ${total}` + (desglose ? ` (${desglose})` : "");
}

async function cargarLista() {
  cargarContador();
  const r = await api("/ofertas");
  if (!r.ok) return avisar(r.motivo, true);
  const ofertas = r.datos;
  const lista = $("lista");
  lista.replaceChildren(...ofertas.map(tarjeta));
  $("vacio").hidden = ofertas.length > 0;
  clearTimeout(temporizador);
  if (ofertas.some((o) => o.estado === "pendiente")) temporizador = setTimeout(cargarLista, 3000);
}

async function iniciar() {
  const yo = await arrancarAdmin();
  if (!yo) return;
  await cargarLista();
}

iniciar();
