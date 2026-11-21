// Pestaña «Añadir oferta» (RF-5.3b): pega el texto, Horma la analiza y la puntúa sola; aquí se ve en qué
// punto va cada una de las últimas añadidas. Todo el texto se pinta con textContent.
const ULTIMAS = 10;
const SONDEO_MS = 3000;
let sondeo = null;
let lecturaBarra = null;   // barra mientras se lee la URL (RF-8.7: «Analizando la oferta»)

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
  if (o.estado === "pendiente" || (o.estado === "procesada" && (nota === null || nota === undefined))) {
    // RF-8.7: «Analizando la oferta · 60 %»; al analizarse queda en 100 y la puntuación la sigue
    barraAvance(li, o.estado === "pendiente" ? "Analizando la oferta" : "Puntuando la oferta")
      .poner(o.estado === "pendiente" ? o.progreso || 0 : 100);
  }
  li.append(nodo("h3", o.titulo || "Oferta en proceso"));
  const linea = [o.empresa, o.ubicacion].filter(Boolean).join(" · ");
  if (linea) li.append(nodo("p", linea));
  if (detalle) li.append(nodo("p", detalle, "alerta"));
  if (o.estado === "procesada") {
    if (o.fuente_desconocida) li.append(nodo("p", textoFuenteDesconocida(o), "estado apagado"));
    if (o.fraude) li.append(nodo("p", "Aviso: el auditor ha visto señales de fraude.", "alerta"));
    const a = nodo("a", "Verla en Recomendadas", "bloque");
    a.href = "/recomendadas";
    li.append(a);
    const original = nodo("button", "Ver oferta original", "secundario");
    original.type = "button";
    original.addEventListener("click", () => verOriginal(o.id));
    li.append(original);
  }
  return li;
}

async function cargar() {
  clearTimeout(sondeo);
  const [of, rec] = await Promise.all([api("/api/ofertas/propias"), api("/api/recomendaciones")]);
  if (!of.ok) return avisar(of.motivo, true);
  const notas = new Map();
  if (rec.ok) for (const x of rec.datos.recomendaciones) notas.set(x.id, x.nota);
  const propias = of.datos.slice(0, ULTIMAS);
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
    return avisar(r.estado === 422 && /^Revisa los datos/.test(r.motivo || "")
      ? "El texto está vacío o es demasiado largo (máximo 20 000 caracteres)." : r.motivo, true);
  }
  $("texto").value = "";
  avisar("Oferta añadida. Se está analizando y puntuando; se actualizará sola.");
  await cargar();
});

// Por dirección (RF-5.3f): se lee en segundo plano; si no se puede, se pide pegar el texto.
const MOTIVO_URL = "La página no se ha podido leer: pega el texto de la oferta.";
function avisarUrl(texto, error) {
  const a = $("aviso-url");
  a.textContent = texto;
  a.className = error ? "alerta" : "suave";
}

async function esperarLectura(id) {
  const r = await api(`/ofertas/url/${id}`);
  if (!r.ok) return avisarUrl(r.motivo, true);
  if (r.datos.estado === "pendiente") return setTimeout(() => esperarLectura(id), SONDEO_MS);
  $("enviar-url").disabled = false;
  if (r.datos.estado === "error") {
    $("lectura-url").replaceChildren();
    avisarUrl(r.datos.motivo || MOTIVO_URL, true);
    $("texto").focus();
    return;
  }
  $("url").value = "";
  $("lectura-url").replaceChildren();
  avisarUrl("Oferta leída. Se está analizando y puntuando; se actualizará sola.");
  await cargar();
}

$("formulario-url").addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = $("url").value.trim();
  if (!url) return avisarUrl("Pega la dirección de la oferta.", true);
  $("enviar-url").disabled = true;
  avisarUrl("Leyendo la página…");
  $("lectura-url").replaceChildren();
  lecturaBarra = barraAvance($("lectura-url"), "Analizando la oferta");
  lecturaBarra.poner(10);
  const r = await api("/ofertas/url", { metodo: "POST", cuerpo: { url } });
  if (!r.ok) {
    $("enviar-url").disabled = false;
    $("lectura-url").replaceChildren();
    return avisarUrl(r.motivo, true);
  }
  await esperarLectura(r.datos.id);
});

(async () => {
  if (!(await arrancar("/anadir-oferta"))) return;
  await cargar();
})();
