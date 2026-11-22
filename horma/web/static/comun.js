// Utilidades comunes de las pantallas de la fase 2. Todo texto que viene de la API o de una oferta
// se pinta con textContent (helper nodo): nunca como HTML.
const $ = (id) => document.getElementById(id);
let csrf = null;

const PESTANAS = [
  ["Ofertas", "/ofertas"],
  ["Candidaturas", "/candidaturas"],
  ["Perfil", "/perfil"],
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
  const marca = document.querySelector(".cabecera .marca");   // RF-10.1d: la marca lleva a Ofertas
  if (marca) marca.href = "/ofertas";
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

// Cabecera de las pantallas de Admin (RF-6.3d): solo comprueba la sesión y enlaza «Salir». Sin sesión, a la landing.
async function arrancarAdmin() {
  const r = await fetch("/api/yo");
  if (!r.ok) {
    location.href = "/";
    return null;
  }
  const yo = await r.json();
  csrf = yo.csrf;
  $("salir").addEventListener("click", async () => {
    await fetch("/auth/logout", { method: "POST", headers: { "X-CSRF-Token": csrf } });
    location.href = "/";
  });
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

// Barra de avance (RF-8.7): frase con el porcentaje y pista con `role="progressbar"`. Devuelve `poner(%)` y `quitar()`.
function barraAvance(contenedor, texto, indeterminada = false) {
  const caja = nodo("div", null, "barra-avance");
  const frase = nodo("span", null, "texto");
  const pista = nodo("div", null, "pista");
  pista.setAttribute("role", "progressbar");
  pista.setAttribute("aria-label", texto);
  pista.setAttribute("aria-valuemin", "0");
  pista.setAttribute("aria-valuemax", "100");
  const relleno = nodo("span", null, "relleno");
  pista.append(relleno);
  caja.append(frase, pista);
  contenedor.append(caja);
  const poner = (p) => {
    const v = Math.max(0, Math.min(100, Math.round(Number(p) || 0)));
    frase.textContent = `${texto} · ${v} %`;
    pista.setAttribute("aria-valuenow", String(v));
    relleno.style.width = `${v}%`;   // por CSSOM: la CSP no permite style= en el HTML
  };
  if (indeterminada) {   // sin porcentaje: Horma trabaja y aún no sabe cuánto falta
    caja.classList.add("indeterminada");
    pista.removeAttribute("aria-valuenow");
    pista.setAttribute("aria-busy", "true");
    frase.textContent = `${texto}…`;
  } else {
    poner(0);
  }
  return { poner, quitar: () => caja.remove() };
}

// Sigue una tarea del servidor cada 3 s mientras esté en marcha, sin límite (RF-8.7f). `alAvanzar(progreso, tarea)`
// en cada consulta; `alTerminar(tarea)` al acabar (estado «hecha» o «error»). Devuelve una función para dejar de seguirla.
const SONDEO_TAREA_MS = 3000;
function seguirTarea(id, alAvanzar, alTerminar) {
  let parar = false;
  async function sondear() {
    if (parar) return;
    const r = await api(`/api/tareas/${id}`);
    if (parar) return;
    if (r.estado === 0) return setTimeout(sondear, SONDEO_TAREA_MS);   // sin conexión: se vuelve a intentar
    if (!r.ok) return alTerminar({ id, estado: "error", progreso: 0, motivo: r.motivo });
    const t = r.datos;
    if (alAvanzar) alAvanzar(t.progreso, t);
    if (t.estado === "pendiente" || t.estado === "en_curso") return setTimeout(sondear, SONDEO_TAREA_MS);
    alTerminar(t);
  }
  sondear();
  return () => { parar = true; };
}

// «Ver oferta original» (RF-8.3): ventana con el texto tal como entró. Todo va con textContent y el texto
// conserva sus saltos de línea con CSS; un enlace o una instrucción dentro del texto no se activa.
function urlSegura(u) {
  return typeof u === "string" && /^https?:\/\//i.test(u);
}

function ventanaOriginal() {
  let v = $("ventana-original");
  if (v) return v;
  v = nodo("dialog", null, "ventana");
  v.id = "ventana-original";
  v.setAttribute("aria-labelledby", "original-titulo");
  const cerrar = nodo("button", "Cerrar", "secundario");
  cerrar.type = "button";
  cerrar.id = "original-cerrar";
  cerrar.addEventListener("click", () => v.close());
  const cab = nodo("header");
  cab.append(nodo("h3", null, "titulo-oferta"), cerrar);
  cab.firstChild.id = "original-titulo";
  const cuerpo = nodo("div", null, "ventana-cuerpo");
  cuerpo.id = "original-cuerpo";
  v.append(cab, cuerpo);
  document.body.append(v);
  return v;
}

// Marca de las ofertas propias cuya dirección no es de ninguna fuente del banco de Horma (o que no tienen).
function textoFuenteDesconocida(o) {
  return o.url ? TEXTOS.fuenteDesconocida : TEXTOS.sinFuente;
}

// Da formato legible al texto de una oferta sin tocar su contenido: apartados en negrita, listas y párrafos.
// Todo con textContent (nunca HTML): un <script> o un enlace pegado solo se ve como texto.
function esTituloDeApartado(l) {
  if (l.length > 60 || /[.;,]$/.test(l)) return false;
  if (/:$/.test(l)) return true;
  const letras = l.replace(/[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ]/g, "");
  return letras.length > 3 && letras === letras.toUpperCase();
}

function textoBonito(texto) {
  const hoja = nodo("article", null, "texto-original");
  let lista = null;
  let parrafo = [];
  const cerrarParrafo = () => {
    if (parrafo.length >= 3 && parrafo.every((l) => l.length <= 160)) {   // varias líneas cortas seguidas: una lista
      const ul = nodo("ul", null, "lista-original");
      ul.append(...parrafo.map((l) => nodo("li", l)));
      hoja.append(ul);
    } else if (parrafo.length) {
      hoja.append(nodo("p", parrafo.join(" ")));
    }
    parrafo = [];
  };
  const lineas = String(texto || "").split(/\r?\n/);
  lineas.forEach((crudo, i) => {
    const l = crudo.trim();
    if (!l) { cerrarParrafo(); lista = null; return; }
    const v = l.match(/^(?:[-*+•·–]|\d+[.)])\s+(.*)$/);
    if (v) {
      cerrarParrafo();
      if (!lista) { lista = nodo("ul", null, "lista-original"); hoja.append(lista); }
      lista.append(nodo("li", v[1]));
      return;
    }
    lista = null;
    const sola = (i === 0 || !(lineas[i - 1] || "").trim()) && !(lineas[i + 1] || "").trim();
    if (esTituloDeApartado(l) || (sola && l.length <= 50 && !/[.!?]$/.test(l))) {
      cerrarParrafo();
      hoja.append(nodo("h4", l.replace(/:$/, ""), "apartado-original"));
      return;
    }
    parrafo.push(l);
  });
  cerrarParrafo();
  return hoja;
}

async function verOriginal(id) {
  const disparador = document.activeElement;
  const r = await api(`/api/ofertas/${id}/original`);
  if (!r.ok) return avisar(r.motivo, true);
  const o = r.datos;
  const v = ventanaOriginal();
  $("original-titulo").textContent = o.titulo || "Oferta sin título";
  const origen = o.propia ? TEXTOS.anadidaPorTi : (o.atribucion || o.fuente || "Catálogo de Horma");
  const cuerpo = $("original-cuerpo");
  cuerpo.replaceChildren(
    nodo("p", [o.empresa || "Empresa sin indicar", origen].join(" · "), "suave"),
    nodo("p", o.fecha_publicacion ? `Publicada el ${fecha(o.fecha_publicacion)}` : "No consta fecha de publicación", "suave"),
  );
  if (urlSegura(o.url)) {
    const a = nodo("a", "Abrir en la web de origen");
    a.href = o.url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    cuerpo.append(a);
  }
  cuerpo.append(textoBonito(o.texto));
  v.addEventListener("close", () => { if (disparador && disparador.isConnected) disparador.focus(); }, { once: true });
  v.showModal();
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

// La carta se ve como carta (RF-10.4d): párrafos, sin negritas ni secciones. Cada línea con texto es un párrafo.
function cartaBonita(md) {
  const hoja = nodo("article", null, "cv-hoja carta-hoja");
  for (const crudo of md.split("\n")) {
    const linea = crudo.trim().replace(/^(?:#{1,6}|[-*+•])\s+/, "").replace(/[*_`]/g, "");
    if (linea) hoja.append(nodo("p", linea, "cv-linea"));
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
  ["sectores", "Sector"], ["contratos", "Tipo de contrato"],
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
