// Pestaña «Añadir oferta» (RF-5.3b): pega el texto, Horma la analiza y la puntúa sola; aquí se ve en qué
// punto va cada una de las últimas añadidas. Todo el texto se pinta con textContent.
const ULTIMAS = 10;
const SONDEO_MS = 3000;
let sondeo = null;

// Una oferta tiene tres momentos: analizándose, puntuándose y lista (o con error).
function estadoDe(o, nota) {
  if (o.estado === "error") return ["No se pudo analizar", "estado error", o.motivo_error || ""];
  if (o.estado !== "procesada") return ["Analizándola…", "estado", ""];
  if (nota === null || nota === undefined) return ["Puntuándola…", "estado", ""];
  return [`Lista · compatibilidad ${nota}`, "estado bien", ""];
}

function tarjeta(o, nota) {
  const li = nodo("li", null, "tarjeta");
  const [texto, clase, detalle] = estadoDe(o, nota);
  li.append(nodo("span", texto, clase));
  li.append(nodo("h3", o.titulo || "Oferta en proceso"));
  const linea = [o.empresa, o.ubicacion].filter(Boolean).join(" · ");
  if (linea) li.append(nodo("p", linea));
  if (detalle) li.append(nodo("p", detalle, "alerta"));
  if (o.estado === "procesada") {
    if (o.fantasma) li.append(nodo("p", "Aviso: podría ser una oferta fantasma.", "suave"));
    if (o.fraude) li.append(nodo("p", "Aviso: el auditor ha visto señales de fraude.", "alerta"));
    const a = nodo("a", "Verla en Recomendadas", "bloque");
    a.href = "/recomendadas";
    li.append(a);
  }
  return li;
}

async function cargar() {
  clearTimeout(sondeo);
  const [of, rec] = await Promise.all([api("/ofertas"), api("/api/recomendaciones")]);
  if (!of.ok) return avisar(of.motivo, true);
  const notas = new Map();
  if (rec.ok) for (const x of rec.datos.recomendaciones) notas.set(x.id, x.nota);
  const propias = of.datos.filter((o) => o.propia).slice(0, ULTIMAS);
  $("lista").replaceChildren(...propias.map((o) => tarjeta(o, notas.get(o.id))));
  $("vacio").hidden = propias.length > 0;
  const enCurso = propias.some((o) => o.estado === "pendiente" ||
    (o.estado === "procesada" && (notas.get(o.id) === null || notas.get(o.id) === undefined)));
  if (enCurso) sondeo = setTimeout(cargar, SONDEO_MS);
}

$("formulario").addEventListener("submit", async (e) => {
  e.preventDefault();
  const texto = $("texto").value.trim();
  if (!texto) return avisar("Pega el texto de la oferta.", true);
  $("enviar").disabled = true;
  avisar("Enviando…");
  const r = await api("/ofertas", { metodo: "POST", cuerpo: { texto } });
  $("enviar").disabled = false;
  if (!r.ok) {
    return avisar(r.estado === 422 ? "El texto está vacío o es demasiado largo (máximo 20 000 caracteres)." : r.motivo, true);
  }
  $("texto").value = "";
  avisar("Oferta añadida. Se está analizando y puntuando; se actualizará sola.");
  await cargar();
});

(async () => {
  if (!(await arrancar("/anadir-oferta"))) return;
  await cargar();
})();
