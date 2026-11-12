// Todo el texto que viene de ofertas se pinta con textContent: nunca como HTML.
const $ = (id) => document.getElementById(id);
let csrf = null;
let temporizador = null;

function nodo(etiqueta, texto, clase) {
  const el = document.createElement(etiqueta);
  if (texto !== undefined && texto !== null) el.textContent = texto;
  if (clase) el.className = clase;
  return el;
}

function tarjeta(o) {
  const li = nodo("li", null, "tarjeta");
  const estado = nodo("span", o.estado, o.estado === "error" ? "estado error" : "estado");
  li.append(estado);
  li.append(nodo("h3", o.titulo || "Oferta sin procesar todavía"));
  const detalle = [o.empresa, o.ubicacion, o.contrato].filter(Boolean).join(" · ");
  if (detalle) li.append(nodo("p", detalle));
  if (o.salario_minimo !== null || o.salario_maximo !== null) {
    const rango = [o.salario_minimo, o.salario_maximo].filter((v) => v !== null).join(" – ");
    li.append(nodo("p", `Salario: ${rango} ${o.salario_moneda || ""}`.trim()));
  }
  if (o.remoto !== null && o.remoto !== undefined) li.append(nodo("p", o.remoto ? "Remoto" : "Presencial"));
  if (o.idiomas && o.idiomas.length) li.append(nodo("p", `Idiomas: ${o.idiomas.join(", ")}`));
  if (o.instrucciones_embebidas && o.instrucciones_embebidas.length) {
    li.append(nodo("p", `Instrucciones detectadas y no ejecutadas: ${o.instrucciones_embebidas.length}`, "alerta"));
  }
  if (o.estado === "error" && o.motivo_error) li.append(nodo("p", o.motivo_error, "alerta"));
  return li;
}

async function cargarLista() {
  const r = await fetch("/ofertas");
  if (!r.ok) return;
  const ofertas = await r.json();
  const lista = $("lista");
  lista.replaceChildren(...ofertas.map(tarjeta));
  $("vacio").hidden = ofertas.length > 0;
  clearTimeout(temporizador);
  if (ofertas.some((o) => o.estado === "pendiente")) temporizador = setTimeout(cargarLista, 3000);
}

async function iniciar() {
  const r = await fetch("/api/yo");
  if (!r.ok) {
    $("entrada").hidden = false;
    return;
  }
  csrf = (await r.json()).csrf;
  $("aplicacion").hidden = false;
  $("salir").hidden = false;
  await cargarLista();
}

$("formulario").addEventListener("submit", async (e) => {
  e.preventDefault();
  const boton = e.target.querySelector("button");
  const aviso = $("aviso");
  boton.disabled = true;
  aviso.className = "";
  aviso.textContent = "Enviando…";
  const r = await fetch("/ofertas", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({ texto: $("texto").value }),
  });
  boton.disabled = false;
  if (r.ok) {
    $("texto").value = "";
    aviso.textContent = "Oferta guardada; se está procesando.";
    await cargarLista();
  } else {
    aviso.className = "error";
    aviso.textContent = r.status === 422 ? "El texto está vacío o es demasiado largo." : "No se pudo guardar.";
  }
});

$("salir").addEventListener("click", async () => {
  await fetch("/auth/logout", { method: "POST", headers: { "X-CSRF-Token": csrf } });
  location.reload();
});

iniciar();
