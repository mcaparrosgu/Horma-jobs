// Utilidades comunes de las pantallas de la fase 2. Todo texto que viene de la API o de una oferta
// se pinta con textContent (helper nodo): nunca como HTML.
const $ = (id) => document.getElementById(id);
let csrf = null;

const PESTANAS = [
  ["Perfil", "/perfil"],
  ["Preferencias", "/preferencias"],
  ["CV base", "/cv-base"],
  ["Añadir oferta", "/anadir-oferta"],
  ["Recomendadas", "/recomendadas"],
  ["Candidaturas", "/candidaturas"],
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
    if (typeof d === "string") motivo = d;
    else if (Array.isArray(d) && d.length) {   // validación de FastAPI: lista de {loc, msg}
      motivo = "Revisa los datos: " + d.slice(0, 3).map((x) => {
        const donde = Array.isArray(x.loc) ? x.loc.filter((l) => l !== "body").join(" › ") : "";
        return donde ? `${donde}: ${x.msg}` : x.msg;
      }).join("; ");
    } else motivo = `No se pudo completar la acción (error ${r.status}).`;
  }
  return { ok: r.ok, estado: r.status, datos, motivo };
}

function avisar(texto, esError) {
  const a = $("aviso");
  if (!a) return;
  a.className = esError ? "error" : "";
  a.setAttribute("role", esError ? "alert" : "status");
  a.textContent = texto || "";
  if (esError && texto) a.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

// Cabecera común (RF-6.3): pestañas, nombre con su inicial, botón de tema y «Salir». Sin sesión, a la portada.
// Nunca se pinta una foto. Sin nombre en el perfil, no se pinta ni el nombre ni la inicial.
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
    const activaAhora = ruta === activa;
    const a = nodo("a", etiqueta, activaAhora ? "pestana activa" : "pestana");
    a.href = ruta;
    if (activaAhora) a.setAttribute("aria-current", "page");
    nav.append(a);
    if (activaAhora) requestAnimationFrame(() => a.scrollIntoView({ inline: "center", block: "nearest" }));
  }
  if (yo.admin) {   // RF-7.7: «Admin» solo para administradoras, la última pestaña
    const a = nodo("a", "Admin", "pestana");
    a.href = "/ingesta";
    nav.append(a);
  }
  const derecha = $("derecha");
  const persona = nodo("span", null, "persona");
  derecha.append(persona);
  const tema = nodo("button", "Tema oscuro", "secundario");
  tema.type = "button";
  tema.id = "tema";
  if (window.vincularTema) window.vincularTema(tema);
  const salir = nodo("button", "Salir", "secundario");
  salir.type = "button";
  salir.id = "salir";
  salir.addEventListener("click", async () => {
    await fetch("/auth/logout", { method: "POST", headers: { "X-CSRF-Token": csrf } });
    location.href = "/";
  });
  derecha.append(tema, salir);
  pintarPersona(persona);
  return yo;
}

// El nombre sale del perfil (GET /api/perfil); si falla o no hay nombre, la cabecera queda sin persona.
async function pintarPersona(persona) {
  try {
    const r = await fetch("/api/perfil");
    if (!r.ok) return;
    const nombre = ((await r.json()).perfil || {}).nombre;
    if (!nombre || !nombre.trim()) return;
    persona.append(nodo("span", nombre.trim().charAt(0).toUpperCase(), "avatar"), nodo("span", nombre.trim(), "nombre"));
    persona.firstChild.setAttribute("aria-hidden", "true");
  } catch (e) {
    /* sin nombre: la cabecera sigue funcionando */
  }
}

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

// Nombres enteros en español (RF-7.4): «ES» → «España», «en» → «Inglés». Sin nombre conocido, el código tal cual.
const NOMBRES_PAIS = new Intl.DisplayNames(["es"], { type: "region" });
const NOMBRES_IDIOMA = new Intl.DisplayNames(["es"], { type: "language" });
function nombrePais(codigo) {
  if (String(codigo || "").toUpperCase() === "REMOTO") return "Remoto (cualquier país)";
  if (!/^[A-Za-z]{2}$/.test(codigo || "")) return codigo;
  try { return NOMBRES_PAIS.of(codigo.toUpperCase()) || codigo; } catch (e) { return codigo; }
}
function nombreIdioma(codigo) {
  if (!/^[A-Za-z]{2,3}$/.test(codigo || "")) return etiqueta(codigo);
  try {
    const n = NOMBRES_IDIOMA.of(String(codigo).toLowerCase());
    return !n || n.toLowerCase() === String(codigo).toLowerCase() ? codigo : n.charAt(0).toUpperCase() + n.slice(1);
  } catch (e) { return codigo; }
}
const MODALIDADES = { remoto: "Remoto", hibrido: "Híbrido", presencial: "Presencial" };
function nombreModalidad(valor) { return MODALIDADES[valor] || ""; }
function nombreOpcion(clave, valor) {
  if (clave === "paises") return nombrePais(valor);
  if (clave === "idiomas") return nombreIdioma(valor);
  return etiqueta(valor);
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
  // Con más de 2 casillas, «Seleccionar todo» y «Quitar selección» (una sola notificación de cambio).
  if (opciones.length > 2) {
    const masivo = nodo("div", null, "masivo");
    for (const [texto, valor] of [["Seleccionar todo", true], ["Quitar selección", false]]) {
      const b = nodo("button", texto, "secundario enlace");
      b.type = "button";
      b.addEventListener("click", () => {
        for (const i of caja.querySelectorAll("input[type=checkbox]")) i.checked = valor;
        const n = cont.querySelector("summary .estado:not(.bien)");
        if (n) n.textContent = String(valor ? opciones.length : 0);
        if (alCambiar) alCambiar();
      });
      masivo.append(b);
    }
    caja.append(masivo);
  }
  for (const o of opciones) {
    const l = nodo("label", null, "casilla");
    const i = nodo("input");
    i.type = "checkbox";
    i.value = o.valor;
    i.checked = marcados.includes(o.valor);
    if (alCambiar) i.addEventListener("change", alCambiar);
    l.append(i, nodo("span", `${nombreOpcion(clave, o.valor)} (${o.n})`));
    caja.append(l);
  }
  cont.append(caja);
  return cont;
}

function marcadas(cont) {
  return [...cont.querySelectorAll("input:checked")].map((i) => i.value);
}
