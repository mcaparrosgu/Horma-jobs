// Utilidades comunes de las pantallas de la fase 2. Todo texto que viene de la API o de una oferta
// se pinta con textContent (helper nodo): nunca como HTML.
const $ = (id) => document.getElementById(id);
let csrf = null;

const PESTANAS = [
  ["Perfil", "/perfil"],
  ["Preferencias", "/preferencias"],
  ["CV base", "/cv-base"],
  ["Recomendadas", "/recomendadas"],
];

function nodo(etiqueta, texto, clase) {
  const el = document.createElement(etiqueta);
  if (texto !== undefined && texto !== null) el.textContent = texto;
  if (clase) el.className = clase;
  return el;
}

function campo(etiqueta, control) {
  const l = nodo("label");
  l.append(nodo("span", etiqueta), control);
  return l;
}

// Icono de papelera (SVG con DOM, sin HTML): el botón que lo lleva debe tener aria-label.
function iconoPapelera() {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  for (const [k, v] of Object.entries({ viewBox: "0 0 24 24", width: "18", height: "18", fill: "none",
    stroke: "currentColor", "stroke-width": "2", "stroke-linecap": "round", "stroke-linejoin": "round",
    "aria-hidden": "true" })) svg.setAttribute(k, v);
  for (const d of ["M3 6h18", "M8 6V4h8v2", "M6 6l1 14h10l1-14", "M10 11v6", "M14 11v6"]) {
    const p = document.createElementNS(ns, "path");
    p.setAttribute("d", d);
    svg.append(p);
  }
  return svg;
}

// Llama a la API con CSRF si cambia algo. Devuelve { ok, estado, datos, motivo }.
async function api(ruta, { metodo = "GET", cuerpo, formulario } = {}) {
  const cabeceras = {};
  if (metodo !== "GET") cabeceras["X-CSRF-Token"] = csrf;
  let body;
  if (formulario) body = formulario;
  else if (cuerpo !== undefined) {
    cabeceras["Content-Type"] = "application/json";
    body = JSON.stringify(cuerpo);
  }
  let r;
  try {
    r = await fetch(ruta, { method: metodo, headers: cabeceras, body });
  } catch (e) {
    return { ok: false, estado: 0, datos: null, motivo: "No hay conexión con Horma." };
  }
  let datos = null;
  try {
    datos = await r.json();
  } catch (e) {
    datos = null;
  }
  let motivo = null;
  if (!r.ok) {
    const d = datos && datos.detail;
    motivo = typeof d === "string" ? d : "No se pudo completar la acción.";
  }
  return { ok: r.ok, estado: r.status, datos, motivo };
}

function avisar(texto, esError) {
  const a = $("aviso");
  if (!a) return;
  a.className = esError ? "error" : "";
  a.textContent = texto || "";
}

// Pestañas, botón «Salir» y sesión. Sin sesión, a la portada.
async function arrancar(activa) {
  const r = await fetch("/api/yo");
  if (!r.ok) {
    location.href = "/";
    return null;
  }
  const yo = await r.json();
  csrf = yo.csrf;
  const nav = $("pestanas");
  for (const [etiqueta, ruta] of PESTANAS) {
    const a = nodo("a", etiqueta, ruta === activa ? "pestana activa" : "pestana");
    a.href = ruta;
    if (ruta === activa) a.setAttribute("aria-current", "page");
    nav.append(a);
  }
  $("salir").addEventListener("click", async () => {
    await fetch("/auth/logout", { method: "POST", headers: { "X-CSRF-Token": csrf } });
    location.href = "/";
  });
  return yo;
}

function fecha(valor) {
  if (!valor) return "—";
  const d = new Date(valor);
  return Number.isNaN(d.getTime()) ? String(valor) : d.toLocaleDateString("es-ES");
}

const ETIQUETAS = {
  // familias (puestos)
  administracion_oficina: "Administración y oficina", atencion_cliente: "Atención al cliente",
  ventas_comercial: "Ventas y comercial", hosteleria_restauracion: "Hostelería y restauración",
  sanidad_cuidados: "Sanidad y cuidados", educacion_formacion: "Educación y formación",
  logistica_transporte: "Logística y transporte", produccion_operarios: "Producción y operarios",
  construccion_oficios: "Construcción y oficios", desarrollo_software: "Desarrollo de software",
  datos_ia: "Datos e IA", sistemas_redes: "Sistemas y redes", diseno_creatividad: "Diseño y creatividad",
  marketing_comunicacion: "Marketing y comunicación", finanzas_contabilidad: "Finanzas y contabilidad",
  recursos_humanos: "Recursos humanos", legal: "Legal", direccion_gestion: "Dirección y gestión",
  // sectores
  hosteleria_turismo: "Hostelería y turismo", sanidad: "Sanidad", tecnologia: "Tecnología",
  administracion_publica: "Administración pública", comercio_retail: "Comercio y retail",
  educacion: "Educación", industria: "Industria", construccion: "Construcción",
  finanzas_seguros: "Finanzas y seguros", servicios_profesionales: "Servicios profesionales",
  medios_marketing: "Medios y marketing",
  // niveles
  practicas: "Prácticas", junior: "Junior", intermedio: "Intermedio", senior: "Senior",
  direccion: "Dirección", sin_especificar: "Sin especificar",
  otros: "Otros",
};

function etiqueta(valor) {
  if (valor === null || valor === undefined || valor === "") return "—";
  if (ETIQUETAS[valor]) return ETIQUETAS[valor];
  const t = String(valor).replace(/_/g, " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
}

// --- Casillas por grupo (Preferencias y barra de filtros de Recomendadas) ------------------------
const GRUPOS = [
  ["familias", "Puestos"], ["sectores", "Sector"], ["contratos", "Tipo de contrato"],
  ["niveles", "Nivel"], ["paises", "País"], ["idiomas", "Idiomas"],
];

// Un grupo de casillas; cada una con cuántas ofertas tiene entre paréntesis (RF-2.8).
function grupoCasillas(clave, titulo, opciones, marcados, { plegable = false, origen = null, alCambiar = null } = {}) {
  const cont = nodo(plegable ? "details" : "fieldset", null, "grupo");
  cont.dataset.grupo = clave;
  const cabecera = nodo(plegable ? "summary" : "legend", titulo);
  if (origen === "cv") cabecera.append(nodo("span", "desde tu CV", "estado bien"));
  if (plegable && marcados.length) cabecera.append(nodo("span", String(marcados.length), "estado"));
  cont.append(cabecera);
  const caja = nodo("div", null, "casillas");
  for (const o of opciones) {
    const l = nodo("label", null, "casilla");
    const i = nodo("input");
    i.type = "checkbox";
    i.value = o.valor;
    i.checked = marcados.includes(o.valor);
    if (alCambiar) i.addEventListener("change", alCambiar);
    l.append(i, nodo("span", `${etiqueta(o.valor)} (${o.n})`));
    caja.append(l);
  }
  cont.append(caja);
  return cont;
}

function marcadas(cont) {
  return [...cont.querySelectorAll("input:checked")].map((i) => i.value);
}
