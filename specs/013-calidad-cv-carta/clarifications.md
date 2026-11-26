---
type: clarifications
title: calidad-cv-carta — Aclaraciones
description: Decisiones que sostienen la spec 013 (paso 3 del PRD) — las ya tomadas en F2, F7 y F9, las cuatro que Mar cerró el 26-nov (D-039 a D-042) y los supuestos de Opus, pendientes de su firma.
tags: [clarify, cv, carta, pdf, panel, eliminatorios]
status: draft
sources: [../prd.md, ../003-candidatura/clarifications.md, ../010-simplificacion/spec.md, ../012-matcher-puestos/spec.md]
generated: { by: claude-code, at: 2026-11-26 }
verified: null
stale_after: null
---

# calidad-cv-carta — Aclaraciones

## Decisiones ya tomadas (no se repreguntan)
Están en los informes F2 (`docs/investigacion/f2-cv-carta-ideales.md`, apartados 2 a 4), F7 (`comparativas.md`) y F9
(`f9-rgpd.md`), documentos de trabajo fuera del repo. El PRD firmado (paso 3) recoge F2-D1 a D9. Aquí solo se citan.

| Decisión | Qué dice |
|---|---|
| F2-D1 | Panel de tres lectores: programa de selección por código sobre el PDF, IA de selección y persona de selección (criterios nuevos del juez). Cambiada en parte por D-041 |
| F2-D2 | Se comprueba el PDF, no el Markdown |
| F2-D3 | `medir_ats` pasa de «% de palabras» a tres avisos; la cobertura se informa, no se fuerza |
| F2-D4 | Regla anticopia: ninguna secuencia de 6 o más palabras de la oferta en el CV ni en la carta |
| F2-D5 | Carta con rúbrica nueva; sin agente nuevo: `redactor-carta` ya es uno aparte. Saludo con el nombre de la empresa |
| F2-D6 | La carta usa la papelería del CV |
| F2-D7 | Viñetas con verbo, qué y alcance o resultado; cifra solo si está en el perfil |
| F2-D8 | Tú o usted, espejo de la oferta; la guía de estilo de la usuaria manda |
| F2-D9 | Eliminatorias a la vista, sin modelo, desde los huecos |
| F7-D3 | Puerta de hechos sin modelo antes del PDF (cifras, cargos, deriva de verbos), tras ver qué cubre `verificar_trazabilidad` |
| F7-D1 | Mensaje de Horma: lo decide Mar al cerrar este paso, con la calidad ya medida |
| F9-D7 | Marca de «generado con IA»: solo si la asesoría legal confirma que obliga |

## Preguntas a Mar (26-nov)
- **Contacto en el PDF.** Dato traído: el perfil no guarda correo ni teléfono; los CV y cartas salen solo con el
  nombre. RadarJobs y Kitsuno quitan el contacto antes del modelo. → **D-039: en Perfil y fuera de la IA.** Correo
  (prellenado con el de Google), teléfono, ciudad y LinkedIn opcional; el código los pone en el PDF.
- **Experiencias con tareas y logros.** Dato traído: cada experiencia tiene un solo texto, «descripción». → **D-040:
  el perfil no cambia.** El redactor distingue en la descripción las tareas de los logros y une cada tarea con el
  logro que la respalda, porque una tarea suele apoyarse en logros (Mar).
- **Quién hace de IA de selección.** Dato traído: el `matcher` solo lee un perfil, no un CV, y lo rehace el paso 2;
  las IA de cribado reales comparan el CV con 4-6 criterios y citan la evidencia. → **D-041: agente pequeño nuevo,
  `lector-ia`,** con su propio eval (~0,005 USD por candidatura).
- **Qué ve ella del panel y con qué umbral.** Dato traído: una nota única, como Jobscan, empuja a rellenar palabras
  clave (señal de IA para el 39 % de RR. HH., F2). → **D-042: tres líneas en la candidatura.** Solo frena la descarga
  si el PDF se lee mal. Umbral: programa 100 %, IA ≥ 0,90, persona ≥ 0,90.

## Supuestos (Opus; pendientes de la firma de Mar)
- **S1 · Deriva de verbos y cargos:** dos listas cerradas en código. Verbos por rango («participé», «colaboré»,
  «ayudé» < «gestioné», «coordiné», «organicé» < «dirigí», «lideré», «supervisé»); palabras de cargo («jefe/a»,
  «responsable», «director/a», «coordinador/a», «encargado/a», «gerente», «supervisor/a», «senior», «lead», «head»,
  «manager»). Una línea no puede subir de rango ni traer un cargo que su cita no tenga.
- **S2 · Falsos «Dato dudoso»:** cada línea admite hasta tres citas literales cuando junta frases distintas de las
  fuentes. Se descarta citar por número de línea (F1): ahorra salida, pero cambia más piezas; va a mejoras futuras.
- **S3 · Mínimos que no se fuerzan:** del CV (C9 a C16) solo son error los máximos y lo mecánico: resumen de más de
  80 palabras, más de 5 viñetas en un puesto, viñeta de más de 30 palabras, un verbo inicial repetido más de 2 veces
  en un puesto, copia de la oferta. Los mínimos (resumen de 40 palabras, 2 viñetas) y C13 a C15 son sugerencias para
  la vuelta: forzarlos invita a rellenar o a inventar.
- **S4 · Anticopia:** 6 o más palabras seguidas iguales a la oferta, sin contar el título del puesto ni el nombre de
  la empresa, que deben salir tal cual.
- **S5 · Longitud de la carta:** 120-250 palabras en 3-4 párrafos (propuesta de F2, K1; las guías dan 200-350). Mar
  puede cambiarla al firmar.
- **S6 · Tú o usted:** el código mira si la oferta tutea («te ofrecemos», «únete», «buscas») y lo pasa al redactor; si
  no tutea, decide el registro del sector, como hoy. La guía de estilo de la usuaria manda. En la carta, «vosotros» y
  «ustedes» no se mezclan.
- **S7 · El lector IA lee solo el CV y la oferta,** como una IA de cribado real. Si un criterio no tiene prueba en el
  CV, el código mira si las fuentes lo respaldan (como `medir_ats`): si sí, va a la vuelta; si no, es un hueco.
- **S8 · Relectura tras la vuelta:** el lector IA y el juez vuelven a leer solo el documento rehecho, para que lo que
  ella ve sea del texto final. Cambia P12 de la spec 003 («tras la vuelta no se vuelve a juzgar»). Coste: de
  0,12-0,18 a unos 0,14-0,22 USD por candidatura ([plan](./plan.md), Costes).
- **S9 · Tras editar:** la línea del programa se recalcula (código). Las de IA y persona dicen «Leído antes de tus
  cambios»; no hay botón para volver a leer.
- **S10 · PDF que se lee mal:** se comprueba al aprobar una candidatura y al descargar «Tu CV completo». Si falla,
  no se descarga, se dice qué falla y salta la alerta de la administradora: es un fallo de Horma, no de ella.
- **S11 · Eliminatorios:** los tres de F2 (permiso de trabajo o residencia, titulación e idioma con nivel) y cualquier
  requisito que la oferta llame «imprescindible», «obligatorio» o «indispensable». Salen también en el detalle de la
  oferta, junto a las condiciones (RF-12.25), para no gastar en una candidatura que se va a descartar.
- **S12 · Diseños:** tres (el actual, «Sobrio», y dos más). Se eligen junto a «Aprobar y descargar» y a «Descargar
  PDF», no en `/cv-base` (auditoría del 22-nov), y Horma recuerda el último. Tipografías con licencia OFL,
  incluidas en el repo.
- **S13 · Fecha de la carta:** ciudad y fecha larga («Madrid, 26 de noviembre de 2026»). MM-AAAA (RF-10.14j) vale
  para los datos del perfil, no para la fecha de una carta.
- **S14 · Editor:** sin librerías (RES-01, frontend plano): botones propios y conversión a Markdown por dentro, así
  trazas, avisos y PDF no cambian.
- **S15 · Recortes del extractor:** prompt y una métrica en el eval `perfil`; el esquema no cambia (D-040).
- **S16 · Cobertura de palabras del eval `cv`:** se sigue midiendo, sin umbral (hoy 0,75), por F2-D3.
- **S17 · Requisitos genéricos que no son hueco:** lista cerrada en código («manejo de ordenador», «informática a
  nivel usuario», «conocimientos básicos de informática», «internet y correo electrónico»).

## Fuera de alcance
- Marca de «generado con IA» en el PDF (F9-D7): espera a la asesoría legal (DEP-04).
- Quitar el nombre antes del modelo: paso 4, spec 015 (F7-D7). El contacto nuevo nunca llega al modelo (D-039).
- Formato de fecha MM-AAAA: no cambia hasta la prueba propia del PDF (DEP-05). Si la prueba dice otra cosa, se
  anota como D-NNN y cambia esta spec antes de construir.
- Tú o usted como ajuste en «Configuración» (F2-D8): `docs/mejoras-futuras.md`.
- Separar tareas y logros en el perfil (D-040). Pedir cifras y alcance: entrevista, paso 6 (F2-D7).
- Volver a leer con IA tras editar (S9). Citar por número de línea (S2).
- CV para otros países (F2, apartado 5).
