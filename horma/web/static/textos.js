// Todos los textos que lee la usuaria (RF-10.2e): estados, motivos, ayudas y avisos. Lo cargan todas las pantallas,
// también las de Admin, antes que comun.js. Vocabulario cerrado de RF-10.2: «compatibilidad», «Tu CV completo»,
// «Por resolver»… Nada de piezas internas ni de personas del equipo (RF-10.2d).

// Un solo estado por candidatura, que junta `estado` y `preparacion` (RF-10.7). La máquina interna no cambia.
const ESTADOS_VISIBLES = ["Preparando", "Por revisar", "Lista para enviar", "Enviada", "Entrevista", "Cerrada"];

function estadoVisible(estado, preparacion) {
  if (estado === "borrador") {
    if (preparacion === "error") return "No se pudo preparar";
    if (preparacion === "lista" || preparacion === "pendiente_de_ti") return "Por revisar";
    return "Preparando";
  }
  if (estado === "aprobada") return "Lista para enviar";
  return { enviada: "Enviada", entrevista: "Entrevista", cerrada: "Cerrada" }[estado] || estado;
}

const MOTIVOS_CIERRE = { rechazo: "Rechazo", descartada: "Descartada", retirada: "Retirada" };
const MOTIVOS_PREGUNTA = [["descartada", "La descarto yo"], ["retirada", "La retiro"]];

// Lo que la oferta pide y el perfil no tiene (RF-10.2c). «Hueco» queda para un periodo sin actividad.
const textoNoConsta = (requisito) => `La oferta pide ${requisito} y no consta en tu perfil`;
// Los huecos de una oferta, en una sola línea corta (RF-10.13): como mucho 5, cada uno recortado, y «y N más».
// «La oferta pide Python, SQL y AWS, y no constan en tu perfil». La lista entera va aparte, desplegable.
const MAX_HUECOS_LINEA = 5;
const MAX_LETRAS_HUECO = 48;
const corto = (t) => (t.length > MAX_LETRAS_HUECO ? `${t.slice(0, MAX_LETRAS_HUECO - 1).replace(/[\s,;(]+$/, "")}…` : t);
const textoNoConstaVarios = (requisitos) => {
  if (requisitos.length < 2) return requisitos.length ? textoNoConsta(corto(requisitos[0])) : "";
  const vistos = requisitos.slice(0, MAX_HUECOS_LINEA).map(corto);
  const resto = requisitos.length - vistos.length;
  const lista = resto > 0 ? `${vistos.join(", ")} y ${resto} más`
    : `${vistos.slice(0, -1).join(", ")} y ${vistos[vistos.length - 1]}`;
  return `La oferta pide ${lista}, y no constan en tu perfil`;
};

const TEXTOS = {
  compatibilidad: "Número de 0 a 100 de lo bien que encajan tu experiencia y formación con lo que pide la oferta. Orienta, no decide. Despliega la fila para ver por qué.",
  sinCompatibilidad: "Sin compatibilidad",
  sinPerfil: "Sube tu CV para ver qué ofertas encajan contigo",
  sinPerfilBoton: "Subir mi CV",
  preguntaClase: "No sabemos si este documento es un CV o una carta. ¿Cuál es?",   // RF-10.14b
  confirmarEliminarCv: "¿Eliminar este CV? Rehacemos tu perfil sin él. No se puede deshacer.",   // RF-10.14
  listaVaciaPorPuestos: "Ninguna oferta casa ahora con los puestos que marcaste. Desmarca alguno o añade una oferta.",   // RF-10.14q
  anadidaPorTi: "Añadida por ti",
  corregirNota: "Compatibilidad que te parece justa (opcional)",
  correccionRango: "La compatibilidad va de 0 a 100 y el motivo no puede estar vacío.",
  correccionGuardada: "Corrección guardada. Gracias.",
  propuesta: (n) => ` (compatibilidad que propones: ${n})`,
  sinNota: "Esta oferta todavía no tiene compatibilidad. Horma la calculará sola; si la quieres ya, pulsa «Puntuar ahora».",
  explicacionRetirada: "No mostramos la explicación de esta oferta: mencionaba un dato personal (como tu edad, sexo, salud o religión) y Horma nunca los usa para recomendar. La compatibilidad solo tiene en cuenta tu experiencia, formación e idiomas, y sigue siendo válida.",
  desfasada: "Esta compatibilidad se calculó con una versión anterior de tu perfil.",
  eligeCv: "Horma prepara tu CV a partir de tu perfil.",
  presupuesto: "Hoy ya hemos trabajado todo lo posible para ti. Mañana seguimos.",
  errorPuntuar: "No se ha podido puntuar esta oferta. Inténtalo otra vez.",
  errorPuntuacion: "El cálculo de compatibilidad se ha detenido por un error. Lo ya calculado se conserva.",
  errorPresupuesto: "Se ha alcanzado el límite de gasto de hoy. Lo ya calculado se conserva.",
  senalesFraude: "Señales de fraude: Horma ha visto en esta oferta indicios de que podría no ser real.",
  fuenteDesconocida: "Fuente no reconocida por Horma",
  sinFuente: "Sin fuente indicada",
  anadirIntro: "Pega el texto de una oferta o la dirección de su página. Es solo tuya: nadie más la ve. Horma la analiza y calcula su compatibilidad con tu perfil, y aparece siempre en Ofertas, pase o no tus filtros.",
  anadirUrl: "Para leerla, la dirección se envía a un servicio externo de lectura de páginas. LinkedIn, Indeed, Glassdoor e InfoJobs no se pueden leer: pega su texto.",
  anadirAplazada: "Oferta guardada. La analizamos mañana: hoy ya hemos trabajado todo lo posible para ti.",
  anadirOk: "Oferta añadida. Se está analizando; se actualizará sola.",
  leidaOk: "Oferta leída. Se está analizando; se actualizará sola.",
  sinCandidaturas: "Todavía no tienes candidaturas.",
  revisaFalta: "Horma no pudo cerrar algo por su cuenta: revisa el CV y la carta con cuidado.",
  editaDocumento: "Lo que escribas es tuyo: Horma lo vuelve a comprobar y lo que no esté en tu CV saldrá en «Revisa esto».",
};
