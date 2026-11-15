// Pantalla de perfil: CV subidos, preguntas pendientes y datos con su origen (RF-2.1b, 2.2-2.4, 2.15).
const CAMPOS = {
  experiencias: [["puesto", "Puesto"], ["empresa", "Empresa"], ["inicio", "Inicio"], ["fin", "Fin"],
                 ["descripcion", "Descripción"]],
  formacion: [["titulo", "Título"], ["centro", "Centro"], ["inicio", "Inicio"], ["fin", "Fin"]],
  idiomas: [["nivel", "Nivel (B2, nativo…)"]],
  habilidades: [["nombre", "Habilidad"]],
  titular: [["valor", "Titular"]],
  resumen: [["valor", "Resumen"]],
  nombre: [["valor", "Nombre"]],
};
// Si la pregunta es sobre un detalle («experiencias.Hotel Marina.fechas»), solo se piden esos campos.
const DETALLES = { fechas: ["inicio", "fin"], nivel: ["nivel"] };
const SECCIONES = [["titular", "Titular"], ["resumen", "Resumen"], ["experiencias", "Experiencia"],
                   ["formacion", "Formación"], ["idiomas", "Idiomas"], ["habilidades", "Habilidades"]];
const MOTIVOS = { falta: "Falta", ambiguo: "Ambiguo", contradiccion: "Contradicción entre CV" };
let idiomasValidos = [];
let perfilActual = null;
let temporizador = null;

function resumenDe(campoNombre, d) {
  if (campoNombre === "experiencias") {
    const fechas = [d.inicio, d.fin].filter(Boolean).join(" – ");
    return [d.puesto, d.empresa, fechas].filter(Boolean).join(" · ");
  }
  if (campoNombre === "formacion") return [d.titulo, d.centro, [d.inicio, d.fin].filter(Boolean).join(" – ")].filter(Boolean).join(" · ");
  if (campoNombre === "idiomas") return [etiqueta(d.idioma), d.nivel].filter((x) => x && x !== "—").join(" · ");
  if (campoNombre === "habilidades") return d.nombre;
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
      const o = nodo("option", etiqueta(v));
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
  avisar(`Hecho: ya es la versión ${r.datos.version} de tu perfil.`);
  await cargarPerfil();
}

function pregunta(p, i) {
  const li = nodo("li", null, "tarjeta");
  li.append(nodo("span", MOTIVOS[p.motivo] || p.motivo, "estado apagado"));
  li.append(nodo("h3", p.pregunta));
  const acciones = nodo("div", null, "fila");
  const responder = (dato) => cambiarPerfil("/api/perfil/respuestas", "POST", { indice: i, dato });
  const [seccion, clave = "", detalle = ""] = p.campo.split(".");
  if (seccion === "genero_puestos") {
    for (const g of ["femenino", "masculino"]) {
      const b = nodo("button", g.charAt(0).toUpperCase() + g.slice(1));
      b.type = "button";
      b.addEventListener("click", () => responder({ valor: g }));
      acciones.append(b);
    }
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
  const descartar = nodo("button", "No lo sé / descartar", "secundario");
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

function seccion(titulo, hijos) {
  const s = nodo("section");
  s.append(nodo("h3", titulo, "subtitulo"));
  const ul = nodo("ul", null, "lista");
  ul.append(...hijos);
  s.append(ul);
  return s;
}

async function cargarPerfil() {
  clearTimeout(temporizador);
  const r = await api("/api/perfil");
  if (!r.ok) {
    avisar(r.motivo, true);
    return;
  }
  const { perfil, construyendo, error } = r.datos;
  const estado = $("estado-perfil");
  estado.replaceChildren();
  if (construyendo) {
    estado.append(nodo("p", "Estamos leyendo tu CV para construir tu perfil. Esto puede tardar un minuto…", "estado apagado"));
    temporizador = setTimeout(cargarPerfil, 3000);
  }
  if (error) estado.append(nodo("p", `No se pudo construir el perfil: ${error}`, "alerta"));
  $("pendientes").hidden = true;
  $("datos").hidden = true;
  if (!perfil) return;

  perfilActual = perfil;
  const pend = perfil.preguntas_pendientes || [];
  $("pendientes").hidden = pend.length === 0;
  $("lista-pendientes").replaceChildren(...pend.map(pregunta));

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
    if (!elementos.length) continue;
    const esLista = Array.isArray(valor);
    cont.append(seccion(titulo, elementos.map((d, i) => dato(clave, d, esLista ? i : null))));
  }
  if (perfil.instrucciones_embebidas && perfil.instrucciones_embebidas.length) {
    cont.append(nodo("p", `Tu CV contenía ${perfil.instrucciones_embebidas.length} instrucción(es) dirigidas a una IA. Se han registrado y no se han ejecutado.`, "alerta"));
  }
}

// --- CV subidos -----------------------------------------------------------------------------
function tarjetaCv(c) {
  const li = nodo("li", null, "tarjeta");
  li.append(nodo("span", c.clase === "estetico" ? "estético" : "fuente", "estado apagado"));
  const titulo = nodo("h3", c.nombre);
  li.append(titulo);
  li.append(nodo("p", `${c.nombre_original} · ${c.tipo.toUpperCase()} · ${Math.max(1, Math.round(c.tamano / 1024))} KB · ${fecha(c.creado_en)}`, "suave"));
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
}

$("subir").addEventListener("submit", async (e) => {
  e.preventDefault();
  const archivo = $("archivo").files[0];
  if (!archivo) return;
  const boton = e.target.querySelector("button");
  const datos = new FormData();
  datos.append("archivo", archivo);
  datos.append("clase", $("clase-cv").value);
  if ($("nombre-cv").value.trim()) datos.append("nombre", $("nombre-cv").value.trim());
  boton.disabled = true;
  avisar("Subiendo…");
  const r = await api("/api/cv", { metodo: "POST", formulario: datos });
  boton.disabled = false;
  if (!r.ok) return avisar(r.motivo, true);
  e.target.reset();
  avisar($("clase-cv").value === "fuente" ? "CV subido; se está construyendo tu perfil." : "CV guardado.");
  await cargarCvs();
  await cargarPerfil();
});

(async () => {
  if (!(await arrancar("/perfil"))) return;
  const op = await api("/api/preferencias/opciones");
  if (op.ok) idiomasValidos = op.datos.grupos.idiomas.map((x) => x.valor);
  await cargarCvs();
  await cargarPerfil();
})();
