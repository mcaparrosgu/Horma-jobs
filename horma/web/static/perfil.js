// Pantalla de perfil (RF-10.5): Por resolver, Tu perfil, Tu CV completo, Documentos subidos y Cómo escribes.
const CAMPOS = {
  experiencias: [["puesto", "Puesto"], ["empresa", "Empresa"], ["inicio", "Inicio"], ["fin", "Fin"],
                 ["descripcion", "Descripción"]],
  formacion: [["titulo", "Título"], ["centro", "Centro"], ["inicio", "Inicio"], ["fin", "Fin"]],
  idiomas: [["nivel", "Nivel (B2, nativo…)"]],
  habilidades: [["nombre", "Habilidad"]],
  proyectos: [["nombre", "Proyecto"], ["descripcion", "Descripción"], ["fecha", "Fecha"]],
  certificaciones: [["nombre", "Certificación"], ["entidad", "Entidad"], ["fecha", "Fecha"]],
  actividades: [["descripcion", "Actividad"], ["inicio", "Inicio (AAAA o AAAA-MM)"], ["fin", "Fin (AAAA, AAAA-MM o «actual»)"]],
  otros: [["valor", "Dato"]],
  titular: [["valor", "Titular"]],
  resumen: [["valor", "Resumen"]],
  nombre: [["valor", "Nombre"]],
};
// Si la pregunta es sobre un detalle («experiencias.Hotel Marina.fechas»), solo se piden esos campos.
const DETALLES = { fechas: ["inicio", "fin"], nivel: ["nivel"] };
const SECCIONES = [["titular", "Titular"], ["resumen", "Resumen"], ["experiencias", "Experiencia"],
                   ["formacion", "Formación"], ["idiomas", "Idiomas"], ["habilidades", "Habilidades"],
                   ["proyectos", "Proyectos"], ["certificaciones", "Certificaciones"],
                   ["actividades", "Otras actividades"], ["otros", "Otros"]];
// Secciones que siempre se muestran (aunque estén vacías) con su ayuda y un botón para añadir (RF-5.1c).
const AYUDA = {
  actividades: "Voluntariado, cuidados, viajes, excedencias… lo que hiciste entre trabajos o estudios. Cubre los huecos del CV. Por ejemplo: «Voluntariado en el banco de alimentos (2019-2020)».",
  proyectos: "Trabajos o iniciativas con nombre propio. Por ejemplo: «Web de reservas para el restaurante familiar (2024)», «TFG: app de turnos».",
  certificaciones: "Acreditaciones, certificados y cursos cortos. Por ejemplo: «Manipulador de alimentos», «Carné de carretillero», «Cambridge B2 First».",
  otros: "Lo útil que no cabe en otra sección. Por ejemplo: «Voluntariado en el banco de alimentos», «Carné de conducir B», «Disponibilidad para viajar».",
};
const MOTIVOS = { falta: "Falta", ambiguo: "Ambiguo", contradiccion: "Contradicción entre CV" };
let idiomasValidos = [];
let perfilActual = null;
let maestroActual = "";
let pendientesPrevias = 0;
let temporizador = null;

function resumenDe(campoNombre, d) {
  if (campoNombre === "experiencias") {
    const fechas = [d.inicio, d.fin].filter(Boolean).join(" – ");
    return [d.puesto, d.empresa, fechas].filter(Boolean).join(" · ");
  }
  if (campoNombre === "formacion") return [d.titulo, d.centro, [d.inicio, d.fin].filter(Boolean).join(" – ")].filter(Boolean).join(" · ");
  if (campoNombre === "idiomas") return [nombreIdioma(d.idioma), d.nivel].filter((x) => x && x !== "—").join(" · ");
  if (campoNombre === "habilidades") return d.nombre;
  if (campoNombre === "proyectos") return [d.nombre, d.fecha].filter(Boolean).join(" · ") + (d.descripcion ? ` — ${d.descripcion}` : "");
  if (campoNombre === "certificaciones") return [d.nombre, d.entidad, d.fecha].filter(Boolean).join(" · ");
  if (campoNombre === "actividades") return [d.descripcion, [d.inicio, d.fin].filter(Boolean).join(" – ")].filter(Boolean).join(" · ");
  return d.valor;
}

function origenDe(d) {
  if (!d.origen) return "";
  if (d.origen.fuente === "usuaria") return "Lo escribiste tú";
  return `Del CV: «${d.origen.fragmento}»`;
}

// Formulario con un campo por dato; devuelve el objeto a enviar o null si está todo vacío.
function formularioDato(campoNombre, inicial, alEnviar, alCancelar, textoBoton, extra = {}) {
  const f = nodo("form", null, "editor");
  const entradas = {};
  let idioma = null;
  if (campoNombre === "idiomas" && !extra.idiomaFijo) {
    idioma = nodo("select");
    for (const v of idiomasValidos) {
      const o = nodo("option", nombreIdioma(v));
      o.value = v;
      idioma.append(o);
    }
    if (inicial.idioma) idioma.value = inicial.idioma;
    f.append(campo("Idioma", idioma));
  }
  for (const [clave, rotulo] of CAMPOS[campoNombre]) {
    if (extra.solo && !extra.solo.includes(clave)) continue;
    const i = nodo("input");
    i.type = "text";
    i.maxLength = 300;
    i.value = inicial[clave] || "";
    entradas[clave] = i;
    f.append(campo(rotulo, i));
    if (extra.sugerencias?.length && clave === (extra.solo?.[0] ?? CAMPOS[campoNombre][0][0])) {   // opciones pulsables: rellenan el campo
      const caja = nodo("div", null, "fila");
      for (const s of extra.sugerencias) {
        const b = nodo("button", s, "secundario");
        b.type = "button";
        b.addEventListener("click", () => { i.value = s; i.focus(); });
        caja.append(b);
      }
      f.append(caja);
    }
  }
  const fila = nodo("div", null, "fila");
  fila.append(nodo("button", textoBoton || "Guardar"));
  if (alCancelar) {
    const c = nodo("button", "Cancelar", "secundario");
    c.type = "button";
    c.addEventListener("click", alCancelar);
    fila.append(c);
  }
  f.append(fila);
  f.addEventListener("submit", (e) => {
    e.preventDefault();
    const dato = {};
    for (const [clave, i] of Object.entries(entradas)) dato[clave] = i.value.trim() || null;
    if (idioma) dato.idioma = idioma.value;
    else if (extra.idiomaFijo) dato.idioma = extra.idiomaFijo;
    alEnviar(dato);
  });
  return f;
}

async function cambiarPerfil(ruta, metodo, cuerpo) {
  avisar("Guardando…");
  const r = await api(ruta, { metodo, cuerpo });
  if (!r.ok) {
    avisar(r.motivo, true);
    return;
  }
  avisar(`Hecho: ya es la versión ${r.datos.version} de tu perfil.${r.datos.aviso ? ` ${r.datos.aviso}` : ""}`);
  await cargarPerfil();
}

function pregunta(p, i) {
  const li = nodo("li", null, "tarjeta");
  li.append(nodo("span", MOTIVOS[p.motivo] || p.motivo, "estado apagado"));
  li.append(nodo("h3", p.pregunta));
  const acciones = nodo("div", null, "fila acciones-aviso");
  const responder = (dato) => cambiarPerfil("/api/perfil/respuestas", "POST", { indice: i, dato });
  const [seccion, clave = "", detalle = ""] = p.campo.split(".");
  if (seccion === "genero_puestos") {
    const abrir = nodo("button", "Responder");
    abrir.type = "button";
    abrir.addEventListener("click", () => {
      abrir.hidden = true;
      const opciones = nodo("div", null, "fila");
      for (const g of ["femenino", "masculino"]) {
        const b = nodo("button", g.charAt(0).toUpperCase() + g.slice(1), "secundario");
        b.type = "button";
        b.addEventListener("click", () => responder({ valor: g }));
        opciones.append(b);
      }
      li.insertBefore(opciones, acciones);
    });
    acciones.append(abrir);
  } else if (CAMPOS[seccion]) {
    const abrir = nodo("button", "Responder");
    abrir.type = "button";
    abrir.addEventListener("click", () => {
      abrir.hidden = true;
      const extra = { sugerencias: p.opciones || [] };
      const inicial = {};
      // Si el dato por el que se pregunta no está en el perfil (lo dejó fuera por ambiguo), hay que
      // pedirlo entero: con solo las fechas no se puede crear.
      const existe = (perfilActual?.[seccion] || []).some((x) => Object.entries(x).some(
        ([k, v]) => k !== "origen" && typeof v === "string" && v.trim().toLowerCase() === clave.trim().toLowerCase()));
      if (DETALLES[detalle] && (existe || !clave)) extra.solo = DETALLES[detalle];
      else if (DETALLES[detalle]) {
        extra.sugerencias = [];
        if (seccion === "experiencias") inicial.empresa = clave;
        if (seccion === "formacion") inicial.centro = clave;
      }
      else if (seccion === "nombre") extra.solo = ["valor"];
      if (seccion === "idiomas" && idiomasValidos.includes(clave)) extra.idiomaFijo = clave;
      const f = formularioDato(seccion, inicial, responder, () => { f.remove(); abrir.hidden = false; },
                               "Guardar respuesta", extra);
      li.insertBefore(f, acciones);
    });
    acciones.append(abrir);
  }
  const descartar = nodo("button", "Dar por visto", acciones.children.length ? "secundario" : null);
  descartar.type = "button";
  descartar.addEventListener("click", () => responder(null));
  acciones.append(descartar);
  li.append(acciones);
  return li;
}

function dato(campoNombre, d, indice) {
  const li = nodo("li", null, "tarjeta");
  li.append(nodo("p", resumenDe(campoNombre, d), "dato"));
  const origen = origenDe(d);
  if (origen) li.append(nodo("p", origen, "suave origen"));
  const acciones = nodo("div", null, "fila");
  const editar = nodo("button", "Modificar", "secundario");
  editar.type = "button";
  const quitar = nodo("button", "Eliminar", "secundario");
  quitar.type = "button";
  const enviar = (nuevo) => cambiarPerfil("/api/perfil/datos", "PATCH",
                                          { campo: campoNombre, indice, dato: nuevo });
  editar.addEventListener("click", () => {
    acciones.hidden = true;
    const inicial = { ...d };
    const f = formularioDato(campoNombre, inicial, (nuevo) => enviar(nuevo), () => { f.remove(); acciones.hidden = false; });
    li.append(f);
  });
  quitar.addEventListener("click", () => enviar(null));
  acciones.append(editar, quitar);
  li.append(acciones);
  return li;
}

function botonAnadir(clave, ul) {
  const fila = nodo("div", null, "fila");
  const abrir = nodo("button", "Añadir", "secundario");
  abrir.type = "button";
  abrir.dataset.anadir = clave;
  abrir.addEventListener("click", () => {
    abrir.hidden = true;
    const f = formularioDato(clave, {}, (nuevo) => cambiarPerfil("/api/perfil/datos", "PATCH",
                             { campo: clave, indice: null, dato: nuevo }),
                             () => { f.remove(); abrir.hidden = false; }, "Añadir");
    fila.append(f);
  });
  fila.append(abrir);
  return fila;
}

// Estas se pliegan, cerradas, con su número en el título (RF-7.5d). Lo abierto sobrevive a guardar.
const PLEGABLES = ["experiencias", "formacion", "idiomas", "habilidades", "proyectos", "certificaciones",
                   "actividades", "otros"];
const abiertas = new Set();

function seccion(titulo, hijos, clave) {
  const plegable = PLEGABLES.includes(clave);
  const s = nodo(plegable ? "details" : "section", null, plegable ? "leer seccion-plegable" : null);
  if (plegable) {
    const resumen = nodo("summary", titulo);
    resumen.append(nodo("span", String(hijos.length), "estado"));
    s.append(resumen);
    s.dataset.seccion = clave;
    s.open = abiertas.has(clave);
    s.addEventListener("toggle", () => { if (s.open) abiertas.add(clave); else abiertas.delete(clave); });
  } else {
    s.append(nodo("h3", titulo, "subtitulo"));
    s.dataset.seccion = clave;
  }
  if (AYUDA[clave]) s.append(nodo("p", AYUDA[clave], "suave"));
  const ul = nodo("ul", null, "lista");
  ul.append(...hijos);
  s.append(ul);
  if (AYUDA[clave] || (clave === "resumen" && !hijos.length)) s.append(botonAnadir(clave, ul));
  return s;
}

// --- Avisos y huecos (RF-9.1c, RF-9.2) ------------------------------------------------------------
// Lleva a una sección de tu perfil: la abre, se coloca en ella y, si se pide, abre su formulario de «Añadir».
function irASeccion(clave, anadir = false) {
  const s = document.querySelector(`#perfil [data-seccion="${clave}"]`);
  if (!s) { $("mi-perfil").scrollIntoView({ behavior: "smooth" }); return; }
  if (s.tagName === "DETAILS") { s.open = true; abiertas.add(clave); }
  s.scrollIntoView({ behavior: "smooth", block: "start" });
  if (anadir) s.querySelector(`[data-anadir="${clave}"]`)?.click();
}

function corregirAviso(a) {
  if (a.seccion === "hueco") return irASeccion("actividades", true);
  if (a.seccion === "resumen") return irASeccion("resumen", true);
  if (a.seccion === "experiencia") return irASeccion("experiencias");
  $("subir-otro").scrollIntoView({ behavior: "smooth" });   // lo que falta está en el CV original: se sube uno corregido
}

async function pedirAvisos(ruta, cuerpo, mensaje) {
  const r = await api(ruta, { metodo: "PUT", cuerpo });
  if (!r.ok) return avisar(r.motivo, true);
  avisar(mensaje);
  await cargarAvisos(perfilActual?.preguntas_pendientes || []);
}

// «Dar por visto» de un aviso agrupado marca todos sus elementos; si cambia la causa de uno, vuelve solo ese.
async function verAviso(a) {
  for (const x of a.elementos) {
    const r = await api("/api/perfil/avisos/visto", { metodo: "PUT", cuerpo: { clave: x.clave, huella: x.huella } });
    if (!r.ok) return avisar(r.motivo, true);
  }
  avisar("Hecho: no te lo volveremos a decir mientras no cambie.");
  await cargarAvisos(perfilActual?.preguntas_pendientes || []);
}

const MENSAJE_LONGITUD = {
  mantener: "Hecho: al redactar un CV para una oferta, Horma conservará todas tus experiencias. Tu CV completo no cambia.",
  sintetizar: "Hecho: al redactar un CV para una oferta, Horma elegirá las experiencias que encajan. Tu CV completo no cambia.",
};
const elegirLongitud = (longitud) => pedirAvisos("/api/perfil/longitud", { longitud }, MENSAJE_LONGITUD[longitud]);

const ETIQUETA_AVISO = { hueco: "Hueco", largo: "CV largo", sin_resumen: "Sin resumen",
                         sin_descripcion: "Sin descripción", sin_cifras: "Sin cifras", sin_contacto: "Sin contacto" };

// Mismo diseño que las preguntas: etiqueta, titular y acciones (la primera, destacada).
function avisoFila(a) {
  const li = nodo("li", null, "tarjeta aviso-accion");
  li.append(nodo("span", ETIQUETA_AVISO[a.regla] || "Aviso", "estado apagado"));
  li.append(nodo("h3", a.texto));
  if (a.elementos.length > 1) {   // aviso agrupado: sus elementos debajo (RF-10.13)
    const ul = nodo("ul", null, "lista");
    ul.append(...a.elementos.map((x) => nodo("li", x.texto, "suave")));
    li.append(ul);
  }
  const acciones = nodo("div", null, "fila acciones-aviso");
  const boton = (texto, alPulsar) => {
    const b = nodo("button", texto, acciones.children.length ? "secundario" : null);
    b.type = "button";
    b.addEventListener("click", alPulsar);
    acciones.append(b);
  };
  if (a.clave === "largo") {   // dos opciones en lugar de «Corregir» (RF-9.2d)
    li.classList.add("aviso-longitud");
    boton("Mantener la longitud", () => elegirLongitud("mantener"));
    boton("Que Horma lo sintetice", () => elegirLongitud("sintetizar"));
  } else {
    boton(a.seccion === "hueco" ? "Añadir" : "Corregir", () => corregirAviso(a));
    boton("Dar por visto", () => verAviso(a));
  }
  li.append(acciones);
  return li;
}

// «Por resolver» reúne, en este orden, preguntas, huecos y avisos (RF-10.5c); se abre solo al aparecer alguno.
async function cargarAvisos(preguntas) {
  const r = await api("/api/perfil/avisos");
  const items = r.ok ? r.datos.grupos : [];
  $("lista-pendientes").replaceChildren(...preguntas.map(pregunta));
  $("lista-avisos").replaceChildren(...items.map(avisoFila));
  $("avisos").hidden = !items.length;
  $("n-avisos").textContent = String(items.length);
  const total = preguntas.length + items.length;
  $("pendientes").hidden = false;
  $("n-pendientes").textContent = String(total);
  if (total && !pendientesPrevias) $("pendientes").open = true;
  if (!total) $("pendientes").open = false;
  pendientesPrevias = total;
}

// --- Tu CV completo (RF-9.4, RF-10.4): el texto que usan los redactores, con «Editar» por sección ------------
const SECCION_DEL_MAESTRO = { "Resumen": "resumen", "Experiencia": "experiencias", "Formación": "formacion",
                              "Idiomas": "idiomas", "Habilidades": "habilidades", "Proyectos": "proyectos",
                              "Certificaciones": "certificaciones", "Otras actividades": "actividades",
                              "Otros": "otros" };

function pintarMaestro(perfil, maestro, creadoEn) {
  $("maestro").hidden = !maestro;
  if (!maestro) return;
  $("maestro-meta").textContent = `Versión ${perfil.version} · ${fecha(creadoEn)}`;
  maestroActual = maestro;
}

// «Ver» abre el CV completo en la Ventana, con «Editar» en cada sección (RF-10.4c).
function verMaestro() {
  const hoja = cvBonito(maestroActual);
  for (const h of hoja.querySelectorAll(".cv-seccion")) {
    const clave = SECCION_DEL_MAESTRO[h.textContent];
    if (!clave) continue;
    h.classList.add("con-editar");
    const editar = nodo("button", "Editar", "secundario");
    editar.type = "button";
    editar.setAttribute("aria-label", `Editar ${h.textContent} en tu perfil`);
    editar.addEventListener("click", () => { $("visor").close(); irASeccion(clave); });
    h.append(editar);
  }
  $("visor-titulo").textContent = "Tu CV completo";
  $("visor-cuerpo").replaceChildren(hoja);
  $("visor").showModal();
}
$("maestro-ver").addEventListener("click", verMaestro);

async function cargarPerfil() {
  clearTimeout(temporizador);
  const r = await api("/api/perfil");
  if (!r.ok) {
    avisar(r.motivo, true);
    return;
  }
  const { perfil, construyendo, error, cv_maestro: maestro, creado_en: creadoEn } = r.datos;
  const estado = $("estado-perfil");
  estado.replaceChildren();
  if (construyendo) {
    const activas = await api("/api/tareas/activas?tipo=perfilar");   // una sola barra, con su % (RF-10.8)
    const progreso = activas.ok && activas.datos.tareas.length ? activas.datos.tareas[0].progreso : 0;
    barraAvance(estado, "Estamos leyendo tu CV").poner(progreso);
    temporizador = setTimeout(cargarPerfil, 3000);
  }
  if (error) estado.append(nodo("p", `No se pudo construir el perfil: ${error}`, "alerta"));
  $("pendientes").hidden = true;
  $("maestro").hidden = true;
  $("datos").hidden = true;
  $("pantalla").hidden = !perfil;   // sin perfil, solo «Sube tu CV» (RF-10.5)
  $("sube-cv").hidden = !!perfil;
  if (!perfil) return;

  perfilActual = perfil;
  await cargarAvisos(perfil.preguntas_pendientes || []);
  pintarMaestro(perfil, maestro, creadoEn);

  $("datos").hidden = false;
  $("version").textContent = `versión ${perfil.version}`;
  const cont = $("perfil");
  cont.replaceChildren();
  if (perfil.nombre) cont.append(nodo("p", perfil.nombre, "dato"));
  if (perfil.genero_puestos) {
    const fila = nodo("div", null, "fila");
    fila.append(nodo("p", `Tus puestos se escriben en género ${perfil.genero_puestos}.`, "suave"));
    const otro = perfil.genero_puestos === "femenino" ? "masculino" : "femenino";
    const cambiar = nodo("button", `Cambiar a ${otro}`, "secundario");
    cambiar.type = "button";
    cambiar.addEventListener("click", () => cambiarPerfil("/api/perfil/datos", "PATCH",
                                                          { campo: "genero_puestos", dato: { valor: otro } }));
    fila.append(cambiar);
    cont.append(fila);
  }
  if (perfil.taxonomia) {
    const t = perfil.taxonomia;
    cont.append(nodo("p", `Clasificación: ${etiqueta(t.sector)} · ${etiqueta(t.familia)} · ${etiqueta(t.nivel)}`, "suave"));
  }
  for (const [clave, titulo] of SECCIONES) {
    const valor = perfil[clave];
    const elementos = Array.isArray(valor) ? valor : valor ? [valor] : [];
    if (!elementos.length && !AYUDA[clave] && clave !== "resumen") continue;
    const esLista = Array.isArray(valor);
    cont.append(seccion(titulo, elementos.map((d, i) => dato(clave, d, esLista ? i : null)), clave));
  }
  if (perfil.instrucciones_embebidas && perfil.instrucciones_embebidas.length) {
    cont.append(nodo("p", `Tu CV contenía ${perfil.instrucciones_embebidas.length} instrucción(es) dirigidas a una IA. Se han registrado y no se han ejecutado.`, "alerta"));
  }
}

// --- CV subidos -----------------------------------------------------------------------------
function tarjetaCv(c) {
  const li = nodo("li", null, "tarjeta");
  li.append(nodo("span", { carta: "Carta", fuente: "CV" }[c.clase] || "Documento", "estado apagado"));
  const titulo = nodo("h3", c.nombre);
  li.append(titulo);
  li.append(nodo("p", `${c.nombre_original} · ${c.tipo.toUpperCase()} · ${Math.max(1, Math.round(c.tamano / 1024))} KB · ${fecha(c.creado_en)}`, "suave"));
  const marca = nodo("label", null, "casilla");
  const casilla = nodo("input");
  casilla.type = "checkbox";
  casilla.checked = !!c.escrito_por_ella;
  casilla.addEventListener("change", async () => {
    const r = await api(`/api/cv/${c.id}/escrito-por-ella`, { metodo: "PUT", cuerpo: { escrito_por_ella: casilla.checked } });
    if (!r.ok) { casilla.checked = !casilla.checked; return avisar(r.motivo, true); }
    avisar(casilla.checked ? "Marcado como escrito por ti." : "Marca quitada.");
  });
  marca.append(casilla, " Lo escribí yo");
  li.append(marca);
  const fila = nodo("div", null, "fila");
  const descargar = nodo("a", "Descargar", "boton secundario");
  descargar.href = `/api/cv/${c.id}/archivo`;
  const renombrar = nodo("button", "Cambiar nombre", "secundario");
  renombrar.type = "button";
  renombrar.addEventListener("click", () => {
    fila.hidden = true;
    const f = nodo("form", null, "fila editor");
    const i = nodo("input");
    i.type = "text";
    i.maxLength = 80;
    i.required = true;
    i.value = c.nombre;
    i.setAttribute("aria-label", "Nombre del CV");
    const cancelar = nodo("button", "Cancelar", "secundario");
    cancelar.type = "button";
    cancelar.addEventListener("click", () => { f.remove(); fila.hidden = false; });
    f.append(i, nodo("button", "Guardar"), cancelar);
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const r = await api(`/api/cv/${c.id}`, { metodo: "PATCH", cuerpo: { nombre: i.value } });
      if (!r.ok) return avisar(r.motivo, true);
      avisar("Nombre cambiado.");
      await cargarCvs();
    });
    li.append(f);
    i.focus();
  });
  if (c.tipo !== "docx") {   // el navegador no muestra DOCX: solo se descargan
    const ver = nodo("button", "Ver", "secundario");
    ver.type = "button";
    ver.addEventListener("click", () => abrirVisor(c));
    fila.append(ver);
  }
  const papelera = nodo("button", null, "secundario icono");
  papelera.type = "button";
  papelera.title = "Eliminar CV";
  papelera.setAttribute("aria-label", `Eliminar el CV ${c.nombre}`);
  papelera.append(iconoPapelera());
  papelera.addEventListener("click", () => {
    fila.hidden = true;
    const conf = nodo("div", null, "fila editor");
    const si = nodo("button", "Eliminar", "secundario");
    si.type = "button";
    const no = nodo("button", "Cancelar", "secundario");
    no.type = "button";
    no.addEventListener("click", () => { conf.remove(); fila.hidden = false; });
    si.addEventListener("click", async () => {
      const r = await api(`/api/cv/${c.id}`, { metodo: "DELETE" });
      if (!r.ok) return avisar(r.motivo, true);
      avisar("CV eliminado. Tu perfil ya construido no cambia.");
      await cargarCvs();
    });
    conf.append(nodo("span", "¿Eliminar este CV? No se puede deshacer."), si, no);
    li.append(conf);
    no.focus();
  });
  fila.append(descargar, renombrar, papelera);
  li.append(fila);
  return li;
}

function abrirVisor(c) {
  const marco = nodo("iframe", null, "visor-marco");
  marco.src = `/api/cv/${c.id}/ver`;
  marco.title = c.nombre;
  $("visor-titulo").textContent = c.nombre;
  $("visor-cuerpo").replaceChildren(marco);
  $("visor").showModal();
}

$("visor-cerrar").addEventListener("click", () => $("visor").close());
$("visor").addEventListener("close", () => $("visor-cuerpo").replaceChildren());

async function cargarCvs() {
  const r = await api("/api/cv");
  if (!r.ok) return avisar(r.motivo, true);
  $("cvs").replaceChildren(...r.datos.map(tarjetaCv));
  $("sin-cvs").hidden = r.datos.length > 0;
  $("n-cvs").textContent = String(r.datos.length);
}

// Al elegir el archivo se sube sin otro clic (RF-10.5). Sin perfil, como CV; en «Documentos subidos», CV o Carta.
async function subirDocumento(entrada, nombreVisible, clase) {
  const archivo = entrada.files[0];
  if (nombreVisible) nombreVisible.textContent = archivo ? archivo.name : "Ningún archivo seleccionado";
  if (!archivo) return;
  const datos = new FormData();
  datos.append("archivo", archivo);
  datos.append("clase", clase);
  datos.append("escrito_por_ella", "false");
  entrada.disabled = true;
  avisar("Subiendo…");
  const r = await api("/api/cv", { metodo: "POST", formulario: datos });
  entrada.disabled = false;
  entrada.value = "";
  if (nombreVisible) nombreVisible.textContent = "Ningún archivo seleccionado";
  if (!r.ok) return avisar(r.motivo, true);
  avisar(clase === "carta" ? "Carta subida; Horma la usará para aprender cómo escribes."
                           : "CV subido; se está construyendo tu perfil.");
  await cargarCvs();
  await cargarPerfil();
  await cargarEstilo();
}

$("archivo").addEventListener("change", () => subirDocumento($("archivo"), $("archivo-nombre"), "fuente"));
$("archivo-doc").addEventListener("change", () => subirDocumento($("archivo-doc"), null, $("clase-doc").value));

// --- Guía de estilo ---------------------------------------------------------------------------
let estiloVisto = null;
let esperaEstilo = null;

const MAX_RASGOS = 5;
const PERSONAS = { primera: "primera persona", impersonal: "impersonal" };

// Resumen de la guía (RF-7.5c): una frase de tono y dos líneas, «Usas» y «Evitas», con 5 rasgos como máximo.
function resumirEstilo(g) {
  const cont = nodo("div", null, "estilo-resumen");
  const vinetas = g.vinetas ? `; viñetas: ${g.vinetas.replace(/[.\s]+$/, "")}` : "";
  cont.append(nodo("p", `Escribes en registro ${g.registro}, en ${PERSONAS[g.persona] || g.persona}, con frases ${g.longitud_frase}s${vinetas}.`));
  const corto = (titulo, lista) => {
    const rasgos = lista.slice(0, MAX_RASGOS).map((r) => r.rasgo).join(", ");
    return nodo("p", `${titulo}: ${rasgos || "—"}.`);
  };
  cont.append(corto("Usas", g.expresiones), corto("Evitas", g.evita));
  return cont;
}

function pintarGuia(g) {
  $("estilo-guia").replaceChildren(resumirEstilo(g));
}

function editorGuia(g) {
  const f = nodo("form", null, "editor");
  const sel = (id, etiqueta, valores, actual) => {
    const l = nodo("label", etiqueta);
    const s = nodo("select");
    s.id = id;
    for (const v of valores) { const o = nodo("option", v); o.value = v; o.selected = v === actual; s.append(o); }
    l.append(s);
    return l;
  };
  const lista = (id, etiqueta, rs) => {
    const l = nodo("label", `${etiqueta} (una por línea)`);
    const t = nodo("textarea");
    t.id = id;
    t.rows = 4;
    t.value = rs.map((r) => r.rasgo).join("\n");
    l.append(t);
    return l;
  };
  const vin = nodo("label", "Forma de tus viñetas");
  const vi = nodo("input");
  vi.id = "e-vinetas";
  vi.maxLength = 200;
  vi.value = g.vinetas;
  vin.append(vi);
  const guardar = nodo("button", "Guardar guía");
  const cancelar = nodo("button", "Cancelar", "secundario");
  cancelar.type = "button";
  cancelar.addEventListener("click", () => { f.remove(); $("estilo-editar").hidden = false; });
  f.append(sel("e-registro", "Registro", ["formal", "cercano", "neutro"], g.registro),
           sel("e-persona", "Persona", ["primera", "impersonal"], g.persona),
           sel("e-longitud", "Longitud de frase", ["corta", "media", "larga"], g.longitud_frase), vin,
           lista("e-expresiones", "Expresiones que usas", g.expresiones), lista("e-evita", "Lo que evitas", g.evita),
           nodo("div", null, "fila"));
  f.lastChild.append(guardar, cancelar);
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    // las citas de origen se conservan para los rasgos que no cambian; las nuevas quedan sin cita
    const citas = new Map([...g.expresiones, ...g.evita].map((r) => [r.rasgo, r.cita]));
    const leer = (id) => $(id).value.split("\n").map((x) => x.trim()).filter(Boolean)
      .map((rasgo) => ({ rasgo, cita: citas.get(rasgo) || "" }));
    const cuerpo = { registro: $("e-registro").value, persona: $("e-persona").value,
                     longitud_frase: $("e-longitud").value, vinetas: $("e-vinetas").value.trim(),
                     expresiones: leer("e-expresiones"), evita: leer("e-evita") };
    const r = await api("/api/estilo", { metodo: "PUT", cuerpo });
    if (!r.ok) return avisar(r.motivo, true);
    avisar("Guía guardada.");
    f.remove();
    await cargarEstilo();
  });
  return f;
}

async function cargarEstilo() {
  const r = await api("/api/estilo");
  if (!r.ok) return;
  const e = r.datos;
  estiloVisto = e;
  $("estilo").hidden = !(e.guia || e.hay_documentos || e.analizando);
  $("estilo-reanalizar").disabled = e.analizando || !e.hay_documentos;
  $("estilo-editar").hidden = !e.guia || e.analizando;   // lo editado durante el análisis se perdería
  if (e.analizando) document.querySelector("#estilo form.editor")?.remove();
  if (e.analizando) $("estilo-estado").textContent = "Analizando tu estilo…";
  else if (e.guia) $("estilo-estado").textContent = e.origen === "usuaria" ? "Guía editada por ti." : "Guía calculada por Horma; puedes editarla.";
  else $("estilo-estado").textContent = "Todavía no hay guía.";
  if (e.guia) pintarGuia(e.guia); else $("estilo-guia").replaceChildren();
  clearTimeout(esperaEstilo);
  if (e.analizando) esperaEstilo = setTimeout(cargarEstilo, 3000);
}

$("estilo-editar").addEventListener("click", () => {
  if (!estiloVisto || !estiloVisto.guia) return;
  $("estilo-editar").hidden = true;
  $("estilo-guia").after(editorGuia(estiloVisto.guia));
});

$("estilo-reanalizar").addEventListener("click", async () => {
  const r = await api("/api/estilo/analizar", { metodo: "POST", cuerpo: {} });
  if (!r.ok) return avisar(r.motivo, true);
  avisar("Analizando tu estilo; tarda un momento.");
  await cargarEstilo();
});

(async () => {
  if (!(await arrancar("/perfil"))) return;
  await cargarEstilo();
  const op = await api("/api/preferencias/opciones");
  if (op.ok) idiomasValidos = op.datos.grupos.idiomas.map((x) => x.valor);
  await cargarCvs();
  await cargarPerfil();
})();
