---
type: spec
title: calidad-cv-carta — Spec funcional
description: Requisitos en notación EARS de la spec 013 (paso 3 del PRD) — hechos exactos y forma flexible, PDF comprobado por código, rúbricas de CV y carta según las mejores guías, ideas para medir logros, panel de tres lectores visible, eliminatorios que avisan sin frenar, contacto fuera de la IA, diseños elegibles y editor con formato. Firmada por Mar el 26-nov.
tags: [spec, cv, carta, pdf, panel, eliminatorios, evals]
status: active
sources: [./clarifications.md, ../prd.md, ../system.md, ../003-candidatura/spec.md, ../010-simplificacion/spec.md, ../012-matcher-puestos/spec.md]
generated: { at: 2026-11-26 }
verified: { by: human, at: 2026-11-26 }
stale_after: null
---

# calidad-cv-carta — Especificación

**PRD:** US-004 · RF-008, RF-009 · NFR-01, NFR-03, NFR-04, NFR-06, NFR-09 · R-01 · DEP-05.

## Contexto
Lo que lee la empresa tiene que ser bueno y estar comprobado antes de que Horma pueda enviarlo ([PRD](../prd.md),
paso 3). Hoy:
- Nadie mira el PDF final, que es lo que lee la empresa, y el PDF no lleva correo ni teléfono.
- La traza comprueba cifras, fechas y nombres propios, y da falsos «Dato dudoso» cuando una línea junta dos frases.
- El aviso «Sin cifras» da los mismos ejemplos para cualquier puesto, y a muchas personas les cuesta pensar en logros
  medibles.
- `medir_ats` mide un % de palabras de la oferta, que empuja a copiarla (señal de IA para el 39 % de RR. HH., F2).
- Ningún lector imita a un programa de selección, a una IA de cribado ni a una persona.
- El aviso de lo que suele descartar (permiso, titulación, idioma) se pierde entre los huecos.

Decisiones y supuestos: [clarifications.md](./clarifications.md); las D-NNN, en la pauta de Mar.

## Requisitos (EARS)

### A · Hechos exactos, forma flexible (F7-D3 y D-054; PRD NFR-01)
- **RF-13.1** *(D-054; cambia F7-D3 en cargos y verbos.)* Horma NO DEBERÁ rechazar una línea del CV o de la carta
  por decir con otras palabras, o con más fuerza, lo que la descripción respalda en el fondo. Quien coordinaba a sus
  compañeras sin tener el cargo puede escribir «Lideré un equipo de 4 personas» si la descripción lo cuenta, y un
  «nivel medio» de inglés puede salir como «B2». No hay listas de verbos ni de cargos; los niveles de idioma se
  traducen con una tabla cerrada en código (S1), y el juez DEBERÁ aceptar lo mismo. Siguen como hoy:
  - cifras, fechas y nombres propios, comprobados con código;
  - el cargo de cada puesto, tal como está en el perfil;
  - el veredicto de veracidad del juez: lo que la descripción no dice sigue siendo inventado.
- **RF-13.2** Una línea DEBERÁ poder citar hasta tres fragmentos literales de las fuentes cuando junta frases
  distintas, y se comprueba contra la unión de esos fragmentos (S2). Una línea sin cita sigue siendo error. Las
  candidaturas guardadas siguen valiendo. *(Quita los falsos «Dato dudoso» del cruce del 22-nov.)*

### B · CV y carta (F2-D3 a D8; PRD RF-008)
- **RF-13.3** `redactor-cv` DEBERÁ seguir la rúbrica del CV de F2 (apartado 3): estructura fija de España (con
  perfil junior, la formación antes que la experiencia); viñetas con verbo, qué y alcance o resultado, 2-5 por
  puesto que encaja y una sola forma verbal; cifra solo si está en las fuentes y, si no, alcance (equipo, volumen,
  frecuencia) o nada. El ejemplo de viñeta de F2 entra en el prompt.
- **RF-13.4** *(D-040)* El redactor DEBERÁ distinguir en la descripción de cada experiencia las tareas de los logros y
  unir cada tarea con el logro que la respalda cuando la descripción lo dice («Coordiné la recepción de unos 400
  pedidos al día con un equipo de 10 personas»). Un logro que la descripción no dice NUNCA DEBERÁ escribirse. El
  perfil no cambia.
- **RF-13.4b** *(D-055; amplía RF-10.14k.)* El aviso «Sin cifras» de Perfil DEBERÁ ofrecer en cada experiencia
  «Ideas para medirlo», con dos partes (S18):
  - preguntas generales, en código («¿A cuántas personas atendías en un día?», «¿Te renovaron o te ascendieron?»);
  - lo que suele medirse en ese puesto, escrito como preguntas («¿Cuántas mesas llevabas por turno?»). Lo da un
    agente pequeño nuevo, `ideas-logros`, solo cuando ella lo pide.

  Las ideas NUNCA DEBERÁN entrar en el CV ni en la carta: solo cuenta lo que ella escriba en la experiencia. Se
  guardan por experiencia y no se vuelven a pedir mientras no cambien el puesto ni la descripción.
- **RF-13.5** El código DEBERÁ comprobar el CV y mandar a la vuelta única lo que falle (S3): resumen de más de 80
  palabras; más de 5 viñetas en un puesto; una viñeta de más de 30 palabras; un verbo inicial repetido más de 2 veces
  en un puesto; y 6 o más palabras seguidas copiadas de la oferta, sin contar el título del puesto ni el nombre de
  la empresa (F2-D4, S4).
- **RF-13.6** *(Cambia RF-3.5.)* `medir_ats` DEBERÁ dar, en lugar de un % que se persigue, tres sugerencias para la
  vuelta (F2-D3): el título del puesto de la oferta en el titular o el resumen, solo si tiene origen; el término
  exacto de la oferta para lo que ella tiene; y cada sigla con su forma completa. La cobertura se sigue midiendo y se
  informa, sin umbral (S16).
- **RF-13.7** Un requisito genérico de la lista cerrada («manejo de ordenador»…) NO DEBERÁ salir como hueco (S17).
- **RF-13.8** *(D-056; amplía RF-10.3g.)* `redactor-carta` DEBERÁ seguir la rúbrica de la carta de F2 (apartado 4),
  su ejemplo ideal y las reglas de 15 guías de referencia («Guías de la carta», en las aclaraciones), sin saltarse
  las de Horma:
  - 120-250 palabras en 3-4 párrafos, nunca más de una página (S5);
  - la primera frase nombra el puesto, con su referencia si la oferta la da, y lo une con un hecho suyo;
  - de 1 a 3 párrafos de cuerpo, uno por cada requisito de los más importantes de la oferta: requisito, prueba y
    resultado, con cifra solo si está en las fuentes;
  - algo que solo vale para esa oferta, sacado de la oferta: nunca datos de la empresa de fuera de ella ni halagos;
  - lo que falta, una sola vez y solo si la oferta lo pide, sin disculpa y seguido de lo más cercano que sí tiene;
  - cierre de 1-2 frases: lo que quiere aprender o aportar y una petición sencilla de entrevista, sin horarios,
    sueldo ni condiciones;
  - primera persona sin empezar cada frase por «yo», y ninguna frase de la lista negra.

  Carta honesta y simple, como seña de Horma.
- **RF-13.9** El código DEBERÁ decidir el tratamiento por la oferta (tú si tutea; si no, el registro del sector) y
  pasárselo al redactor; la guía de estilo de la usuaria manda (F2-D8, S6). La carta NO DEBERÁ mezclar
  tratamientos.
- **RF-13.10** *(D-057; cambia los saludos de la lista cerrada de RF-3.6.)* SI la oferta da el nombre de la persona
  de selección, el saludo DEBERÁ ir a ella, con el nombre tal cual y «Sr.» o «Sra.» delante («Hola, Sra. Laura
  García:») cuando la oferta deja claro cuál es; si no lo deja claro, sin él («Hola, Alex Martín:») (D-060). SI la
  oferta no da el nombre, el saludo DEBERÁ ir al equipo de selección con el nombre exacto de la empresa («Hola, equipo de selección de Transportes Ebro:»), o
  «Hola, equipo de selección:» si la oferta no la nombra. La carta DEBERÁ llevar el nombre exacto de la empresa y del puesto. El nombre
  de la persona lo saca `extractor-oferta` y el código comprueba que está tal cual en la oferta (S19).
- **RF-13.11** El código DEBERÁ comprobar la carta y mandar a la vuelta lo que falle: longitud (K1), párrafo de más
  de 90 palabras o frase media de 25 o más (K2), nombre de la empresa y del puesto (K3), copia de 6 o más palabras de
  la oferta o de una línea del CV (K5), tratamientos mezclados (K7), todos los párrafos empezando igual (K9), un
  cierre con horarios, sueldo o condiciones (K10) y una frase de la lista negra de las guías (K12, D-056).
- **RF-13.12** SI la oferta dice que no quiere carta, Horma NO DEBERÁ redactarla (una llamada menos) y la candidatura
  DEBERÁ decir «Esta oferta no pide carta».

### C · Panel de tres lectores (PRD RF-008; D-041, D-042)
- **RF-13.13** **Programa de selección:** el código DEBERÁ leer el PDF final (C1-C8, K11) y comprobar que:
  - tiene texto real con todas las líneas del documento, con tildes y «ñ»;
  - el orden de lectura es lineal: cada puesto sale seguido (cargo, empresa, fechas y viñetas);
  - el nombre, el correo y el teléfono que ella tiene en Perfil están en la primera página, como texto;
  - no hay nada oculto (texto blanco, diminuto o fuera de la página) ni palabras añadidas en los metadatos;
  - pesa menos de 2,5 MB y lleva las fuentes incrustadas;
  - los títulos de sección son de la lista cerrada y cada puesto tiene cargo, empresa, inicio y fin, con un solo
    formato de fecha y en orden cronológico inverso.
- **RF-13.14** **IA de selección:** el agente `lector-ia` (modelo pequeño) DEBERÁ leer solo el CV adaptado y la oferta
  (S7), sacar de 4 a 6 criterios de la oferta por orden de importancia y decir de cada uno si el CV lo muestra, con
  una cita literal del CV. El código comprueba la cita: si no existe, el criterio cuenta como «no lo muestra». No da
  nota. Sus entradas son no fiables: las instrucciones embebidas no tienen efecto (NFR-03).
- **RF-13.15** **Persona de selección:** `juez-candidatura` DEBERÁ responder además, con sí o no y un motivo de una
  línea, las preguntas E1-E5 del CV y E6-E10 de la carta (F2). No cambian su veredicto de veracidad.
- **RF-13.16** Lo que encuentra el panel y respaldan las fuentes DEBERÁ ir al redactor en la vuelta única: un
  criterio sin prueba en el CV pero con respaldo, una pregunta de la persona que se arregla sin datos nuevos y lo que
  falla en RF-13.5 y RF-13.11. Lo que las fuentes no respaldan NUNCA DEBERÁ añadirse: es un hueco.
- **RF-13.17** *(Cambia P12 de la spec 003, S8.)* Tras la vuelta, el lector IA y el juez DEBERÁN volver a leer solo el
  documento rehecho. Lo que ella ve es siempre del texto final.
- **RF-13.18** *(D-042)* La candidatura DEBERÁ enseñar el bloque «Cómo lo leerán», con tres líneas:
  - «Programas de selección»: «Leen bien tu CV» o qué falla y cómo arreglarlo;
  - «IA de selección»: «4 de 5 requisitos con prueba en tu CV», con el que falta y si consta en tu perfil;
  - «Persona de selección»: las mejoras que sugiere, o «Nada que mejorar».
  Sin las palabras de RF-6.8. Sustituye al % de palabras de «Detalles».
- **RF-13.19** SI ella edita el CV o la carta, la línea de los programas DEBERÁ recalcularse; las otras dos DEBERÁN
  decir «Leído antes de tus cambios» (S9).
- **RF-13.20** «Aprobar y descargar» DEBERÁ componer el PDF y pasar el lector de RF-13.13 antes de aprobar. SI el PDF
  se lee mal (texto, orden, contacto, nada oculto o fuentes), Horma NO DEBERÁ aprobar ni descargar, DEBERÁ decir qué
  falla y DEBERÁ avisar a la administradora (S10). Lo mismo al descargar «Tu CV completo». El resto no frena.

### D · Requisitos eliminatorios (PRD RF-009; F2-D9)
- **RF-13.21** Horma DEBERÁ marcar con código como eliminatorio un requisito de la oferta que no consta en el perfil
  y es un permiso de trabajo o de residencia, una titulación o un idioma con nivel, o que la oferta llama
  «imprescindible», «obligatorio» o «indispensable» (S11). Sale de los huecos, sin modelo.
- **RF-13.22** La candidatura DEBERÁ enseñar los eliminatorios arriba, antes de «Cómo lo leerán» y de «Revisa esto»:
  «Suele ser eliminatorio: la oferta pide inglés C1 y no consta en tu perfil». No se repiten en «No consta en tu CV».
  El permiso de trabajo nunca se deduce: «La oferta pide permiso de trabajo en España. Horma no lo sabe:
  confírmalo tú». *(D-058)* Los eliminatorios avisan y NO DEBERÁN frenar: ella puede aprobar, descargar y, cuando
  Horma envíe (paso 5), enviar la candidatura igual.
- **RF-13.23** El detalle de una oferta en Ofertas DEBERÁ enseñar la misma línea junto a las condiciones
  (RF-12.25), calculada al pedirla, sin modelo. No impide pedir la candidatura.

### E · Contacto, diseño y carta en PDF (D-039; F2-D6)
- **RF-13.24** Perfil DEBERÁ tener «Tu nombre y contacto (salen arriba en tus CV y cartas; la IA no los ve)»: nombre
  (el de hoy), correo (prellenado con el de su cuenta de Google), teléfono, ciudad y LinkedIn (opcional). El
  contacto se guarda aparte del perfil que leen los agentes, solo lo ve su dueña (RLS) y NUNCA DEBERÁ llegar al
  modelo (NFR-04). *(Amplía RF-10.5f.)*
- **RF-13.25** Al componer el PDF, el código DEBERÁ poner el contacto en una línea de texto bajo el nombre del CV y
  en la cabecera de la carta, y el nombre al pie de la carta. SI falta el teléfono, la candidatura DEBERÁ avisar
  «Añade tu teléfono en Perfil: sin él, la empresa no puede llamarte».
- **RF-13.26** *(Cambia RF-10.4d.)* Horma DEBERÁ ofrecer tres diseños de CV, todos con una columna, una familia
  tipográfica y texto real en orden de lectura: el de hoy («Sobrio») y dos más que solo cambian tipografía, color de
  acento y espaciado. Se eligen junto a «Aprobar y descargar» y a «Descargar PDF», y Horma recuerda el último (S12).
- **RF-13.27** La carta en PDF DEBERÁ usar la papelería del diseño elegido: la misma cabecera con nombre y contacto,
  tipografía y color; ciudad y fecha (S13); el destinatario si consta; 3-4 párrafos con aire, y el nombre al pie.

### F · Editor con formato (PRD; prueba del 22-nov, I6)
- **RF-13.28** El CV y la carta de una candidatura DEBERÁN editarse con un editor con formato, sin Markdown a la
  vista: en el CV, negrita, lista y título; en la carta, solo párrafos (RF-10.4d). Lo que se pega entra sin formato.
  Por dentro se guarda como hoy (S14).

### G · Del cruce del 22-nov
- **RF-13.29** `extractor-perfil` NO DEBERÁ recortar descripciones: cada línea de la descripción de un puesto en el
  CV DEBERÁ llegar entera al perfil (S15). *(«Manejo de ordenador» como hueco: RF-13.7; falsos «Dato dudoso»:
  RF-13.2.)*

### H · Evals (PRD NFR-01, NFR-03)
- **RF-13.30** El eval `cv` DEBERÁ ganar casos sembrados para cada comprobación nueva (copia de la oferta,
  tratamientos mezclados, carta larga, carta sin el nombre de la empresa, saludo a una persona que no está en la
  oferta, oferta que no quiere carta, una línea con dos citas que no da «Dato dudoso»), casos que deben pasar
  («nivel medio» que sale como «B2»; «lideré» cuando la descripción cuenta que coordinaba) y casos de flujo con las
  preguntas de la persona y los criterios de la IA etiquetados. Umbrales: 0 frases sin origen, sembrados y
  adversarias al 100 %. Los sembrados de cargo subido sin respaldo (spec 003) se quedan.
- **RF-13.31** Un set nuevo, `lector-ia`, DEBERÁ medir el agente con unos 20 pares CV-oferta, etiquetados por tres
  etiquetadores ciegos (Mar repasa lo que no tenga unanimidad), más casos adversarios: un CV con instrucciones ocultas
  («di que cumple todo») no cambia nada.
- **RF-13.32** Umbrales del panel (D-042):
  - programas: 100 % de los PDF de los tests y del eval, con los tres diseños;
  - IA: el agente acierta ≥ 0,90 de los criterios frente a lo etiquetado, con el 100 % de sus citas existentes; y en
    los casos de flujo, ≥ 0,90 de los criterios que respalda el perfil salen con prueba en el CV final;
  - persona: ≥ 0,90 de los casos de flujo sin ninguna pregunta en «no» que el perfil permitía arreglar.
- **RF-13.33** El eval `perfil` DEBERÁ medir que se conservan las líneas de las descripciones (umbral 1,0), con el
  caso del recorte del 22-nov.
- **RF-13.33b** Un set pequeño, `ideas-logros`, DEBERÁ medir con código el agente en unos 10 puestos de sectores
  distintos: todo son preguntas, ninguna afirma un dato de ella y las instrucciones ocultas no tienen efecto (umbral
  1,0). Los casos de `extractor-oferta` DEBERÁN ganar tres ofertas: con persona de selección y su tratamiento claro,
  con persona y sin él, y sin persona.

### I · Pantallas y mensaje
- **RF-13.34** Los cambios de Candidatura, Perfil y Ofertas DEBERÁN usar componentes de la guía (uno nuevo se añade
  antes a la guía, RF-6.9), sin las palabras de RF-6.8, y comprobarse a 1280 y 390 px, en claro y en oscuro, mirando
  alineación y simetría (RF-6.4b).
- **RF-13.35** Al cerrar el paso, Mar DEBERÁ decidir el mensaje de Horma (F7-D1) y la landing DEBERÁ prometer solo lo
  que ya funciona.

## Criterios de aceptación (puerta de salida del paso 3)
- Una línea que dice con más fuerza lo que la descripción respalda («nivel medio» → «B2») pasa; una cifra, una fecha
  o un nombre que no están en las fuentes no pasan.
- El aviso «Sin cifras» da ideas para medir cada experiencia, y ninguna entra en el CV.
- Una oferta con el nombre de la persona de selección da una carta que la saluda por su nombre, con «Sr.» o «Sra.»
  solo si la oferta lo deja claro; sin nombre, al «equipo de selección de» la empresa.
- El PDF de cada candidatura y de «Tu CV completo», con los tres diseños, pasa el lector de programas: texto entero
  con tildes, orden lineal, contacto en la primera página, nada oculto.
- Una oferta que pide inglés C1, sin inglés en el perfil, enseña «Suele ser eliminatorio» arriba de la candidatura y
  en el detalle de la oferta, y la candidatura se puede aprobar igual.
- La candidatura enseña «Cómo lo leerán» con sus tres líneas, del texto final.
- Ningún prompt lleva el correo ni el teléfono (test).
- Eval `cv` con 0 frases sin origen y sembrados al 100 % (NFR-01); eval `perfil` y set `lector-ia` en sus umbrales;
  panel en los umbrales de RF-13.32.
- Editor, diseños y bloques nuevos comprobados a 1280 y 390 px, en claro y en oscuro; suite verde.
- Mar decide el mensaje (F7-D1) y hace la prueba manual del paso.

## Riesgos
- **Los evals reales cuestan más de lo estimado** (el `cv` llegó a 2,7 USD). Estimación y OK de Mar antes de cada
  gasto ([plan](./plan.md), Costes).
- **Más reglas de código, más vueltas:** cada vuelta cuesta 0,04-0,06 USD. Lo que no es mecánico va como sugerencia,
  no como error (S3); si el eval enseña muchas vueltas por una regla, esa regla baja a sugerencia.
- **Sin listas de verbos ni de cargos (D-054),** un verbo o un cargo inflado sin respaldo solo lo frena el juez, que
  es un modelo. Los sembrados de cargo subido del eval `cv` lo miden; si fallan, se vuelve a hablar con Mar.
- **Un lector IA que se equivoca** desinforma: por eso cita y el código comprueba la cita, y tiene su propio set.
- **Workday no lee bien las fechas** (prueba propia del PDF, DEP-05, 26-nov): falla igual con guion que con barra,
  así que MM-AAAA no cambia. La causa no está medida.
