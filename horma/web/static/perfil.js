// Pantalla de perfil (RF-10.5): Por resolver, Tu perfil, Tu CV completo, Documentos subidos y Cómo escribes.
const CAMPOS = {
  experiencias: [["puesto", "Puesto"], ["empresa", "Empresa"], ["inicio", "Inicio (MM-AAAA)"], ["fin", "Fin (MM-AAAA o «actual»)"],
                 ["descripcion", "Descripción"]],
  formacion: [["titulo", "Título"], ["centro", "Centro"], ["inicio", "Inicio (MM-AAAA)"], ["fin", "Fin (MM-AAAA)"]],
  idiomas: [["nivel", "Nivel (B2, nativo…)"]],
  habilidades: [["nombre", "Habilidad"]],
  proyectos: [["nombre", "Proyecto"], ["descripcion", "Descripción"], ["fecha", "Fecha (MM-AAAA)"]],
  certificaciones: [["nombre", "Certificación"], ["entidad", "Entidad"], ["fecha", "Fecha (MM-AAAA)"]],
  actividades: [["descripcion", "Actividad"], ["inicio", "Inicio (MM-AAAA o AAAA)"], ["fin", "Fin (MM-AAAA, AAAA o «actual»)"]],
  otros: [["valor", "Dato"]],
  titular: [["valor", "Titular"]],
  resumen: [["valor", "Resumen"]],
  nombre: [["valor", "Tu nombre (sale arriba en tus CV y cartas)"]],
};
// Si la pregunta es sobre un detalle («experiencias.Hotel Marina.fechas»), solo se piden esos campos.
const DETALLES = { fechas: ["inicio", "fin"], nivel: ["nivel"] };
const SECCIONES = [["titular", "Titular"], ["resumen", "Resumen"], ["experiencias", "Experiencia"],
                   ["formacion", "Formación"], ["certificaciones", "Cursos y certificados"], ["idiomas", "Idiomas"],
                   ["habilidades", "Habilidades"], ["proyectos", "Proyectos"],
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
let leyendo = false;   // ya se enseñó la barra «Estamos leyendo tu CV»
let barraLectura = null;   // esa barra, que se conserva entre consultas
let subiendoLote = false;   // hay un lote en camino: la barra no se quita aunque aún no haya tarea (RF-10.18h)
let notaLote = "";
const CLAVE_REHACIENDO = "horma:perfil-rehaciendo";   // borró un CV: la barra dice «Actualizando», no «leyendo»; sobrevive a cambiar de pestaña   // el resultado del lote, que sale junto al «Listo» (RF-10.18i)

const CAMPOS_FECHA = ["inicio", "fin", "fecha"];
const periodoVisto = (d) => [d.inicio, d.fin].filter(Boolean).map(fechaVista).join(" – ");

function resumenDe(campoNombre, d) {
  if (campoNombre === "experiencias") {
    return [d.puesto, d.empresa, periodoVisto(d)].filter(Boolean).join(" · ");
  }
  if (campoNombre === "formacion") return [d.titulo, d.centro, periodoVisto(d)].filter(Boolean).join(" · ");
  if (campoNombre === "idiomas") return [nombreIdioma(d.idioma), d.nivel].filter((x) => x && x !== "—").join(" · ");
  if (campoNombre === "habilidades") return d.nombre;
  if (campoNombre === "proyectos") return [d.nombre, fechaVista(d.fecha)].filter(Boolean).join(" · ") + (d.descripcion ? ` — ${d.descripcion}` : "");
  if (campoNombre === "certificaciones") return [d.nombre, d.entidad, fechaVista(d.fecha)].filter(Boolean).join(" · ");
  if (campoNombre === "actividades") return [d.descripcion, periodoVisto(d)].filter(Boolean).join(" · ");
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
    // Los textos largos (descripción, resumen…) van en un cuadro que crece con lo que se escribe.
    const largo = clave === "descripcion" || (clave === "valor" && ["resumen", "otros"].includes(campoNombre));
    const i = nodo(largo ? "textarea" : "input");
    if (!largo) i.type = "text";
    i.maxLength = largo ? 2000 : 300;
    i.value = CAMPOS_FECHA.includes(clave) ? fechaVista(inicial[clave]) : inicial[clave] || "";
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
    for (const [clave, i] of Object.entries(entradas)) {
      const v = i.value.trim();
      dato[clave] = v ? (CAMPOS_FECHA.includes(clave) ? fechaGuardada(v) : v) : null;
    }
    if (idioma) dato.idioma = idioma.value;
    else if (extra.idiomaFijo) dato.idioma = extra.idiomaFijo;
    alEnviar(dato);
  });
  return f;
}

const NOMBRES_SECCION = { ...Object.fromEntries(SECCIONES), genero_puestos: "Género de los puestos", nombre: "Nombre" };

// El aviso de dato personal quitado se queda a la vista, pegado al borde inferior, hasta que ella lo cierra.
function mostrarAvisoDato() {
  const caja = $("aviso-dato");
  caja.replaceChildren(nodo("strong", TEXTOS.datoPersonalTitulo), nodo("p", TEXTOS.datoPersonalMotivo));
  const cerrar = nodo("button", TEXTOS.datoPersonalCerrar, "secundario");
  cerrar.type = "button";
  cerrar.addEventListener("click", () => { caja.hidden = true; });
  caja.append(cerrar);
  caja.hidden = false;
  cerrar.focus();
}

async function cambiarPerfil(ruta, metodo, cuerpo) {
  avisar("Guardando…");
  const r = await api(ruta, { metodo, cuerpo });
  if (!r.ok) {
    avisar(r.motivo, true);
    return;
  }
  const c = r.datos.cambio;   // qué ha cambiado y dónde (RF-10.14e)
  const donde = c ? ` Actualizado en ${NOMBRES_SECCION[c.campo] || c.campo}: ${c.valor}.` : "";
  avisar(`Hecho: perfil actualizado.${donde}`);
  if (r.datos.aviso) mostrarAvisoDato();
  await cargarPerfil();
}

// Su nombre: sale como título de «Tu CV completo» y de sus PDF. Sin nombre, «Añadir»; con él, «Modificar».
function filaNombre(nombre) {
  const fila = nodo("div", null, "fila");
  const texto = nodo("p", null, nombre ? "dato" : "suave");
  texto.append(nodo("strong", `${CAMPOS.nombre[0][1]}: `), nombre || "aún sin escribir");
  fila.append(texto);
  const abrir = nodo("button", nombre ? "Modificar" : "Añadir nombre", "secundario");
  abrir.type = "button";
  abrir.addEventListener("click", () => {
    abrir.hidden = true;
    const f = formularioDato("nombre", { valor: nombre || "" },
      (dato) => cambiarPerfil("/api/perfil/datos", "PATCH", { campo: "nombre", dato }),
      () => { f.remove(); abrir.hidden = false; }, "Guardar", { solo: ["valor"] });
    fila.after(f);
  });
  fila.append(abrir);
  return fila;
}

// Una propuesta (RF-10.15d): información que ella añadió en una oferta y quiso revisar aquí. Puede editarla,
// colocarla en una sección o descartarla; hasta que la guarda, su perfil no cambia.
// Cada sección, con el campo donde cae el texto.
const SECCIONES_PROPUESTA = [["habilidades", "nombre"], ["experiencias", "descripcion"], ["formacion", "titulo"], ["otros", "valor"]];

function propuesta(p, i) {
  const li = nodo("li", null, "tarjeta");
  const texto = (p.opciones || [])[0] || "";
  li.append(nodo("span", TEXTOS.propuestaEtiqueta, "estado apagado"), nodo("h3", p.pregunta), nodo("p", `«${texto}»`, "dato"));
  const acciones = nodo("div", null, "fila acciones-aviso");
  const revisar = nodo("button", TEXTOS.propuestaRevisar);
  revisar.type = "button";
  revisar.addEventListener("click", () => {
    acciones.hidden = true;
    const donde = nodo("select");
    for (const [clave] of SECCIONES_PROPUESTA) {
      const o = nodo("option", NOMBRES_SECCION[clave]);
      o.value = clave;
      donde.append(o);
    }
    let f = null;
    const pintarFormulario = () => {
      const seccion = donde.value;
      const principal = SECCIONES_PROPUESTA.find(([clave]) => clave === seccion)[1];
      const nuevo = formularioDato(seccion, { [principal]: texto },
        (dato) => cambiarPerfil("/api/perfil/respuestas", "POST", { indice: i, campo: seccion, dato }),
        () => { f.remove(); acciones.hidden = false; }, TEXTOS.propuestaGuardar);
      nuevo.prepend(campo(TEXTOS.propuestaDonde, donde));
      if (f) f.replaceWith(nuevo);
      else li.insertBefore(nuevo, acciones);
      f = nuevo;
    };
    donde.addEventListener("change", pintarFormulario);
    pintarFormulario();
  });
  const descartar = nodo("button", "Descartar", "secundario");
  descartar.type = "button";
  descartar.addEventListener("click", async () => {
    const r = await api("/api/perfil/respuestas", { metodo: "POST", cuerpo: { indice: i, dato: null } });
    if (!r.ok) return avisar(r.motivo, true);
    avisar(TEXTOS.propuestaDescartada);
    await cargarPerfil();
  });
  acciones.append(revisar, descartar);
  li.append(acciones);
  return li;
}

function pregunta(p, i) {
  if (p.campo === "propuesta") return propuesta(p, i);
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
  editar.dataset.modificar = "1";
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
  if (AYUDA[clave] || clave === "experiencias" || (clave === "resumen" && !hijos.length)) s.append(botonAnadir(clave, ul));
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

// Abre la caja «Modificar» de esa experiencia (RF-10.14k).
function corregirExperiencia(indice) {
  irASeccion("experiencias");
  document.querySelectorAll('#perfil [data-seccion="experiencias"] > ul > li')[indice]?.querySelector("[data-modificar]")?.click();
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

// «Añadir» en un hueco pregunta qué fue y abre Experiencia u «Otras actividades» (RF-10.14i).
function preguntarTipoDeHueco(li, acciones) {
  if (li.querySelector(".tipo-hueco")) return;
  const caja = nodo("div", null, "fila tipo-hueco");
  caja.append(nodo("span", TEXTOS.preguntaTipoHueco));
  for (const [texto, clave] of [["Un empleo", "experiencias"], ["Otra cosa", "actividades"]]) {
    const b = nodo("button", texto, "secundario");
    b.type = "button";
    b.addEventListener("click", () => irASeccion(clave, true));
    caja.append(b);
  }
  li.insertBefore(caja, acciones);
}

// Mismo diseño que las preguntas: etiqueta, titular y acciones (la primera, destacada).
function avisoFila(a) {
  const li = nodo("li", null, "tarjeta aviso-accion");
  li.append(nodo("span", ETIQUETA_AVISO[a.regla] || "Aviso", "estado apagado"));
  li.append(nodo("h3", a.texto));
  if (a.regla === "sin_cifras") li.append(nodo("p", TEXTOS.ejemplosCifras, "suave"));   // RF-10.14k
  if (a.elementos.length > 1) {   // aviso agrupado: sus elementos debajo (RF-10.13)
    const ul = nodo("ul", null, "lista");
    ul.append(...a.elementos.map((x) => {
      const e = nodo("li", null, "fila");
      e.append(nodo("span", x.texto, "suave"));
      if (x.indice != null) {   // un «Corregir» por experiencia
        const b = nodo("button", "Corregir", "secundario");
        b.type = "button";
        b.addEventListener("click", () => corregirExperiencia(x.indice));
        e.append(b);
      }
      return e;
    }));
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
    const porElemento = a.elementos.length > 1 && a.elementos.every((x) => x.indice != null);   // cada uno tiene su «Corregir»
    if (a.seccion === "hueco") boton("Añadir", () => preguntarTipoDeHueco(li, acciones));
    else if (!porElemento) boton("Corregir", () => (a.elementos[0]?.indice != null ? corregirExperiencia(a.elementos[0].indice) : corregirAviso(a)));
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
                              "Información adicional": "otros", "Otros": "otros" };   // «Otros»: maestros viejos

function pintarMaestro(perfil, maestro, creadoEn) {
  $("maestro").hidden = !maestro;
  if (!maestro) return;
  $("maestro-meta").textContent = `Actualizado el ${fecha(creadoEn)}`;
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
  const { perfil, construyendo, aplazado, error, cv_maestro: maestro, creado_en: creadoEn } = r.datos;
  const estado = $("estado-perfil");
  if (!construyendo && !subiendoLote && barraLectura) {
    barraLectura.quitar();
    barraLectura = null;
  }
  // se quita todo menos la barra viva: vaciar el contenedor y recolocarla tras un `await` la hacía parpadear
  for (const hijo of [...estado.children]) if (!(barraLectura && hijo === barraLectura.caja)) hijo.remove();
  if (!construyendo) sessionStorage.removeItem(CLAVE_REHACIENDO);
  if (construyendo) leyendo = true;
  else if (leyendo && perfil) {   // acaba de terminar: ahora sí el mensaje siguiente (RF-10.14n)
    leyendo = false;
    avisar(["Listo: tu perfil está construido.", notaLote].filter(Boolean).join("\n"));
    notaLote = "";
  }
  if (construyendo) {
    const activas = await api("/api/tareas/activas?tipo=perfilar");   // una sola barra, con su % (RF-10.8)
    const progreso = activas.ok && activas.datos.tareas.length ? activas.datos.tareas[0].progreso : 0;
    // la misma barra en cada consulta: sigue rellenándose en vez de empezar de cero (RF-10.8c)
    const rehaciendo = sessionStorage.getItem(CLAVE_REHACIENDO) === "1";
    if (!barraLectura) barraLectura = barraAvance(estado, rehaciendo ? TEXTOS.actualizandoPerfil : "Estamos leyendo tu CV");
    else if (barraLectura.caja.parentNode !== estado) estado.append(barraLectura.caja);
    barraLectura.poner(progreso);
    temporizador = setTimeout(cargarPerfil, 3000);
  }
  // sin presupuesto hoy no hay nada que leer: el aviso queda fijo, sin barra ni consultas (RF-10.18g)
  if (aplazado) estado.append(nodo("p", TEXTOS.perfilAplazado, "suave"));
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
  const cont = $("perfil");
  cont.replaceChildren();
  cont.append(filaNombre(perfil.nombre));
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
  let formacion = null;
  for (const [clave, titulo] of SECCIONES) {
    const valor = perfil[clave];
    const elementos = Array.isArray(valor) ? valor : valor ? [valor] : [];
    if (!elementos.length && !AYUDA[clave] && clave !== "resumen") continue;
    const esLista = Array.isArray(valor);
    const bloque = seccion(titulo, elementos.map((d, i) => dato(clave, d, esLista ? i : null)), clave);
    if (clave === "formacion") formacion = bloque;
    // «Formación» reúne los títulos y, debajo, «Cursos y certificados» (RF-10.14g)
    if (clave === "certificaciones" && formacion) formacion.append(bloque);
    else cont.append(bloque);
    if (clave === "resumen" && (perfil.resumenes || []).length > 1) cont.append(otrosResumenes(perfil.resumenes));
  }
  if (perfil.instrucciones_embebidas && perfil.instrucciones_embebidas.length) {
    cont.append(nodo("p", `Tu CV contenía ${perfil.instrucciones_embebidas.length} instrucción(es) dirigidas a una IA. Se han registrado y no se han ejecutado.`, "alerta"));
  }
}

// Un resumen por CV (RF-10.14d): se guardan todos y, al redactar un CV, Horma elige el que mejor encaja.
function otrosResumenes(resumenes) {
  const d = nodo("details", null, "leer");
  d.append(nodo("summary", `Resumen de cada uno de tus CV (${resumenes.length})`));
  d.append(nodo("p", TEXTOS.resumenesPorCv, "suave"));
  const ul = nodo("ul", null, "lista");
  ul.append(...resumenes.map((r) => nodo("li", r.valor)));
  d.append(ul);
  return d;
}

// --- CV subidos -----------------------------------------------------------------------------
function tarjetaCv(c, _i, todos) {
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
  const esCv = c.clase === "fuente";
  const cambiar = nodo("button", esCv ? "¿No es un CV? Cámbialo" : "¿No es una carta? Cámbialo", "secundario");
  cambiar.type = "button";
  cambiar.addEventListener("click", async () => {
    const r = await api(`/api/cv/${c.id}/clase`, { metodo: "PATCH", cuerpo: { clase: esCv ? "carta" : "fuente" } });
    if (!r.ok) return avisar(r.motivo, true);
    avisar(esCv ? "Ahora es una carta." : "Ahora es un CV; se está rehaciendo tu perfil.");
    await cargarCvs();
    await cargarPerfil();
    await cargarEstilo();
  });
  const fila = nodo("div", null, "fila");
  const descargar = nodo("a", c.tipo === "docx" ? "Descargar original" : "Descargar", "boton secundario");
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
  const ver = nodo("button", "Ver", "secundario");   // un DOCX no se muestra: se enseña su texto (RF-10.14c)
  ver.type = "button";
  ver.addEventListener("click", () => abrirVisor(c));
  fila.append(ver);
  const papelera = nodo("button", null, "secundario icono");
  papelera.type = "button";
  const ultimoCv = esCv && todos.filter((x) => x.clase === "fuente").length === 1;   // su borrado deja sin perfil
  papelera.title = esCv ? "Eliminar CV" : "Eliminar carta";
  papelera.setAttribute("aria-label", `${esCv ? "Eliminar el CV" : "Eliminar la carta"} ${c.nombre}`);
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
      if (esCv && !ultimoCv) sessionStorage.setItem(CLAVE_REHACIENDO, "1");
      avisar(!esCv ? TEXTOS.cartaEliminada : ultimoCv ? TEXTOS.ultimoCvEliminado : TEXTOS.cvEliminado);
      await cargarCvs();
      await cargarPerfil();   // el perfil se rehace con los CV que quedan (RF-10.14)
    });
    conf.append(nodo("span", !esCv ? TEXTOS.confirmarEliminarCarta : ultimoCv ? TEXTOS.confirmarEliminarUltimoCv
      : TEXTOS.confirmarEliminarCv), si, no);
    li.append(conf);
    no.focus();
  });
  fila.append(descargar, renombrar, cambiar, papelera);
  li.append(fila);
  return li;
}

async function abrirVisor(c) {
  if (c.tipo === "docx") {
    const r = await api(`/api/cv/${c.id}/texto`);
    if (!r.ok) return avisar(r.motivo, true);
    const cuerpo = nodo("div");
    cuerpo.append(nodo("p", r.datos.aviso, "suave"), nodo("pre", r.datos.texto, "cv-texto"));
    $("visor-titulo").textContent = c.nombre;
    $("visor-cuerpo").replaceChildren(cuerpo);
    $("visor").showModal();
    return;
  }
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

// Al elegir los archivos se suben sin otro clic, hasta 5 a la vez en una sola llamada (RF-10.18). Horma detecta si cada
// uno es un CV o una carta (RF-10.14b); si duda de alguno, pregunta una sola vez al final.
const MAX_LOTE = 5;
let resumenLote = null;   // lo acumulado en las llamadas del mismo lote: subidos, repetidos, fallidos, sin guardar

function nuevoResumen() {
  return { subidos: 0, cartas: 0, repetidos: [], fallidos: [], sinGuardar: [] };
}

function textoResumen(r) {
  const lineas = [];
  if (r.subidos === 1 && !r.repetidos.length && !r.fallidos.length && !r.sinGuardar.length) {
    if (r.cartas === 1) lineas.push("Carta subida; Horma la usará para aprender cómo escribes.");
  } else if (r.subidos) lineas.push(r.subidos === 1 ? "1 archivo subido." : `${r.subidos} archivos subidos.`);
  else lineas.push("No se ha subido ningún archivo.");
  for (const x of r.repetidos) lineas.push(`${x.nombre} ya estaba subido`);
  for (const x of r.fallidos) lineas.push(`${x.nombre}: ${x.motivo}`);
  if (r.sinGuardar.length) lineas.push(TEXTOS.dudososSinResponder(r.sinGuardar));
  return lineas.join("\n");   // «perfil aplazado» lo dice `cargarPerfil`, fijo, para que no salga dos veces
}

function quitarBarraLote() {
  subiendoLote = false;
  if (barraLectura) {
    barraLectura.quitar();
    barraLectura = null;
  }
}

async function enviarLote(archivos, { clases = null, cerrar = false } = {}) {
  const datos = new FormData();
  for (const a of archivos) datos.append("archivos", a);
  for (const c of clases || []) datos.append("clases", c);
  if (cerrar) datos.append("cerrar", "true");
  avisar("");
  sessionStorage.removeItem(CLAVE_REHACIENDO);   // subir un CV es leer, no rehacer
  $("pregunta-clase").hidden = true;
  // una sola barra continua, creada ahora: `cargarPerfil` la reutiliza en vez de pintar otra (RF-10.18h)
  subiendoLote = true;
  if (!barraLectura && archivos.length) {
    barraLectura = barraAvance($("estado-perfil"), archivos.length > 1 ? TEXTOS.leyendoArchivos(archivos.length) : "Estamos leyendo tu CV");
  }
  const r = await api("/api/cv/lote", { metodo: "POST", formulario: datos });
  if (!r.ok) {
    quitarBarraLote();
    return avisar(r.motivo, true);
  }
  const d = r.datos;
  resumenLote = resumenLote || nuevoResumen();
  resumenLote.subidos += d.subidos.length;
  resumenLote.cartas += d.subidos.filter((x) => x.clase === "carta").length;
  resumenLote.repetidos.push(...d.repetidos);
  resumenLote.fallidos.push(...d.fallidos);
  if (d.perfil === "pendiente_de_respuesta" || d.dudosos.length) {
    quitarBarraLote();
    await cargarCvs();
    return preguntarClases(d.dudosos.map((x) => ({ nombre: x.nombre, archivo: archivos[x.indice] })));
  }
  const resumen = resumenLote;
  resumenLote = null;
  subiendoLote = false;
  if (d.perfil === "en_marcha") {
    // RF-10.14n y 10.18i: mientras lee, solo la barra; el resultado sale junto al «Listo» al terminar
    notaLote = textoResumen(resumen);
  } else {
    quitarBarraLote();
    avisar(textoResumen(resumen));
  }
  await cargarCvs();
  await cargarPerfil();
  await cargarEstilo();
}

function preguntarClases(dudosos) {
  const caja = $("pregunta-clase");
  const texto = nodo("p", TEXTOS.preguntaLote, null);
  texto.id = "pregunta-clase-texto";
  const filas = nodo("div", null, "rejilla-clases");
  const elegidos = [];
  for (const d of dudosos) {
    const etiqueta = nodo("label", null, null);
    etiqueta.append(nodo("span", d.nombre, "nombre-doc"));
    const selector = nodo("select", null, null);
    for (const [valor, nombre] of [["", "Elige…"], ["fuente", "CV"], ["carta", "Carta"]]) {
      const o = nodo("option", nombre, null);
      o.value = valor;
      if (!valor) o.selected = true;
      selector.append(o);
    }
    etiqueta.append(selector);
    elegidos.push(selector);
    filas.append(etiqueta);
  }
  const acciones = nodo("div", null, "fila");
  const seguir = nodo("button", "Continuar", null);
  seguir.type = "button";
  seguir.addEventListener("click", () => elegidos.some((s) => !s.value)
    ? avisar(TEXTOS.preguntaLoteElegir, true)
    : enviarLote(dudosos.map((d) => d.archivo), { clases: elegidos.map((s) => s.value) }));
  const cerrar = nodo("button", "Ahora no", "secundario");
  cerrar.type = "button";
  cerrar.addEventListener("click", () => {
    resumenLote.sinGuardar.push(...dudosos.map((d) => d.nombre));
    enviarLote([], { cerrar: true });
  });
  acciones.append(seguir, cerrar);
  caja.replaceChildren(texto, filas, acciones);
  caja.hidden = false;
  avisar("");
  caja.scrollIntoView({ block: "start", behavior: "smooth" });   // en el móvil la caja queda sobre las tarjetas
  elegidos[0].focus({ preventScroll: true });
}

async function subirDocumento(entrada, nombreVisible) {
  const archivos = [...entrada.files];
  const reponer = () => {
    entrada.value = "";
    if (nombreVisible) nombreVisible.textContent = "Ningún archivo seleccionado";
  };
  if (archivos.length > MAX_LOTE) {   // no se sube ninguno (RF-10.18b)
    reponer();
    return avisar(TEXTOS.maxLote, true);
  }
  if (nombreVisible) nombreVisible.textContent = archivos.length > 1 ? `${archivos.length} archivos` : archivos[0] ? archivos[0].name : "Ningún archivo seleccionado";
  if (!archivos.length) return;
  entrada.disabled = true;
  resumenLote = nuevoResumen();
  try {
    await enviarLote(archivos);
  } finally {
    entrada.disabled = false;
    reponer();
  }
}

$("archivo").addEventListener("change", () => subirDocumento($("archivo"), $("archivo-nombre")));
$("archivo-doc").addEventListener("change", () => subirDocumento($("archivo-doc"), null));

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
  // Un rasgo por viñeta (RF-10.14l); «Evitas» vacío lo dice en lugar de dejar un guion.
  const lista = (titulo, rasgos, vacio) => {
    const caja = nodo("div");
    caja.append(nodo("p", `${titulo}:`, "etiqueta-mono"));
    if (!rasgos.length) {
      caja.append(nodo("p", vacio, "suave"));
      return caja;
    }
    const ul = nodo("ul", null, "lista");
    ul.append(...rasgos.slice(0, MAX_RASGOS).map((r) => nodo("li", r.rasgo)));
    caja.append(ul);
    return caja;
  };
  cont.append(lista("Usas", g.expresiones, TEXTOS.usasVacio), lista("Evitas", g.evita, TEXTOS.evitasVacio));
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
  else if (e.guia) $("estilo-estado").textContent = e.origen === "usuaria" ? "Editada por ti" : "Hecha por Horma";
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
