---
type: prd
title: Horma — Product Requirements Document (PRD)
description: Guía de producto de la ampliación de Horma, por pasos de construcción — problema, objetivos medibles, alcance por pasos (historia, qué incluye, puerta de salida y dependencias), requisitos, restricciones, fuera de alcance, riesgos y dependencias. Cada spec cita la parte que desarrolla.
tags: [prd, producto, sdd]
status: active
sources: [./constitution.md, ./system.md, ./index.md]
generated: { at: 2026-11-25 }
verified: { by: human, at: 2026-11-25 }
stale_after: null
---

# Horma — Product Requirements Document (PRD)

Documento: `specs/prd.md`
Módulo / Asignatura: PRD Ampliaciones Horma
Caso: Horma — proyecto propio del bootcamp de AI Engineering
Estado: Firmado por Mar el 25-nov (D-021). Los `[pendiente]` se cierran en el paso que los cita
Autores: Mar

**Cómo se usa.** Dice el qué, el porqué y el orden. El cómo está en la [constitución](./constitution.md), la
[spec de sistema](./system.md) y cada `specs/NNN-<feature>/`; el estado, en [`index.md`](./index.md). Cada spec
nueva cita en su cabecera los RF, NFR y US de este documento que desarrolla («PRD RF-003»). Lo que falta va
como `[pendiente]`; no se inventa.

## 1. Contexto y Problema de Negocio

**Para quién.** Personas que buscan empleo en España, en español y en cualquier sector. Una sola persona
(Mar) construye y administra Horma.

**Situación actual.** Quien busca empleo adapta el CV y la carta a mano para cada oferta, o usa una
herramienta de IA que escribe por ella. Horma ya hace (fases 0 a 10, en `main`): perfil desde el CV con el
origen de cada dato, ofertas con compatibilidad 0-100 explicada, y CV y carta adaptados que la usuaria aprueba
y descarga. Corre en local, con datos inventados y 9 agentes en uso.

**Dolor medido.**
- La IA genérica penaliza: el 51 % de 200 personas de RR. HH. en España descartaría un CV sospechoso de IA
  (encuesta de un vendedor, jun-2026; orientativa).
- El descarte automático real son las preguntas eliminatorias, no el formato del CV.
- Los que envían candidaturas sin revisar concentran las quejas del sector: respuestas erróneas en formularios
  y cuentas restringidas.
- Tiempo y candidaturas por usuaria: [pendiente: no hay medición propia; sale de la prueba con cinco personas].

**Qué falla hoy en Horma.**
- La compatibilidad no es fiable: 0,67-0,71 de los casos dentro de ±10 puntos (15 y 16-nov, 21 casos); 0,85-0,87
  tras la spec 012 (27-nov, 60 casos), aún bajo el 0,90.
- Pocas ofertas de España: dos fuentes activas (Jobicy y Himalayas) más las que pega la usuaria.
- Nadie comprueba el PDF final, que es lo que lee la empresa.
- No hay textos legales, ni borrar la cuenta, ni descargar los datos: no puede entrar ninguna usuaria real.
- La usuaria envía cada candidatura a mano y anota a mano la respuesta.

**Si nadie hace nada:** Horma se queda en una demo con datos inventados, sin usuarias y sin lo que la
distingue de sus rivales directos (cita visible por línea, carta en español, cualquier sector).

## 2. Objetivos y Métricas de Éxito

Horma prepara, envía y sigue candidaturas veraces para quien busca empleo en España, sin inventar nada y sin
actuar fuera de lo que ella ha aprobado.

Sin fecha: cada paso se cierra al cumplir su puerta de salida, y cada meta se cumple antes de la primera
usuaria real.

| Objetivo de Negocio | Métrica (SLI / KPI) | Línea Base (Actual) | Meta de Éxito (SLO) |
|---|---|---|---|
| Compatibilidad fiable | Casos del eval `recomendacion` con la nota dentro de ±10 | 0,67-0,71 (21 casos) | ≥ 0,90, estable en 3 ejecuciones |
| Puestos sugeridos con evidencia | Precisión y cobertura sobre un set de 30 CV | N/A: nunca medido (solo se midió casar ofertas: 1,00 y 0,945) | 0 ajenos marcados; precisión ≥ 0,95 marcados y ≥ 0,85 sin marcar; cobertura ≥ 0,80 (F4-D5; spec 012, RF-12.3) |
| CV y carta sin inventar | Frases sin origen en el eval `cv` | 0 (33/33, 22-nov) | 0, y además el PDF final comprobado en el 100 % de las candidaturas |
| Más ofertas de España | Ofertas vigentes de España en el catálogo | [pendiente: contar]; 2 fuentes activas | 5.000 (D-024) |
| Envío dentro de una regla | Envíos con una respuesta inventada o fuera de la regla | N/A: no existe | 0; porcentaje que sale sin intervención: [pendiente: tras la medición de destinos] |
| Gasto acotado | USD por usuaria y día; USD por candidatura | Tope de 1 USD al día; 0,12-0,18 por candidatura (22-nov) | Tope diario y mensual: [pendiente: spec 017] |
| Privacidad lista para usuarias | Hallazgos abiertos de la revisión de RGPD | 9 | 0, con la evaluación de impacto hecha |

## 3. Personas y Usuarios

- **Primaria — «la candidata»:** busca empleo en España, de cualquier sector y sin perfil técnico. Usa Horma
  en el móvil o el ordenador unos minutos al día. Necesita candidaturas veraces y no perder el control: ver y
  poder parar todo lo que sale en su nombre.
- **Gestión — «la administradora» (Mar):** vigila el gasto, las fuentes, los fallos de portales y las alertas.
  No puede empeorar: el coste por usuaria, la veracidad y el cumplimiento legal.
- **Stakeholder — el profesor:** evalúa el método (specs, evals, arquitectura) y revisa el RGPD.
- **Terceros — la empresa que recibe la candidatura:** no usa Horma. Le importa que lo recibido sea cierto y
  que sepa cuándo le escribe una IA.

## 4. Alcance del Producto y User Stories Principales

**v1.0:** Horma web, en español y para España, abierta a las primeras usuarias reales.

**Cómo se lee.** El alcance va por **pasos de construcción**, en el orden en que se construyen. Se llaman
«paso» y no «fase» para no chocar con las fases 0 a 10, ya hechas. El número de spec y el de paso son nombres
fijos, no el orden: desde el 28-nov, tras el paso 2 va el 5 (D-095). Cada paso dice: por qué va ahí, historia, qué incluye, puerta de salida y de qué depende. Quién hace
qué y cuándo: la hoja de ruta (documento de trabajo). La prioridad MoSCoW la confirmó Mar el 25-nov.

| Paso | Qué | Spec | Historia |
|---|---|---|---|
| 1 | Medición de destinos y mejoras pequeñas | 011 (parte 1) | US-001 (solo medir) |
| 2 | `matcher` y puestos afines | 012 | US-002 |
| 5 | Ingesta y vigilancia | 014 | US-005 |
| 3 | Calidad de CV y carta, con PDF comprobado | 013 | US-004 |
| 4 | Privacidad y cuenta | 015 | US-003 |
| 6 | Entrevista por texto | 016 | US-008 |
| 7 | Envío y correo, en modo prueba | 011 (parte 2) | US-001, US-007 |
| 8 | Gasto por usuaria | 017 | US-006 |
| 9 | Salida a usuarias | sin spec propia | — |
| 10 | Envío real | 011 (parte 3) | US-001 |

### Paso 1 · Medición de destinos y mejoras pequeñas (spec 011, parte 1)

- **Por qué va ahí:** medir cuesta 0 USD y dice cuántas candidaturas podrán salir solas (R-02) antes de
  invertir en el envío. Las mejoras pequeñas limpian lo que ya se ve, sin riesgo.
- **Historia:** la parte de medir de US-001 (paso 7). El bloque M no tiene historia: corrige lo construido.
- **Qué incluye:**
  - RF-001: `portales.json`, `resolver_destino` y la medición en consola y en Admin.
  - RF-016: el aviso «Hemos quitado un dato personal» se ve; una fuente que responde 403
    (Adzuna) queda «no apta» con motivo; botones de archivo con una sola norma; resaltado simétrico en «Añadir
    oferta»; barras sin borde; barra de rango de compatibilidad.
  - No incluye los cambios de constitución y de RT del envío: van con el paso 7.
- **Puerta de salida:** Mar lee la medición del catálogo real y se anota como decisión; el bloque M, probado
  por Mar a 1280 y 390 px, en claro y en oscuro; suite verde.
- **Depende de:** la parte 1 de la spec 011 (firmada, con el PRD, el 25-nov).

### Paso 2 · `matcher` y puestos afines (spec 012)

- **Por qué va ahí:** es el mayor fallo (0,67 al decidirlo, frente a 0,90). Todo lo de después —redactar, avisar y
  enviar— se apoya en la nota y en los puestos.
- **Historia — US-002 [MUST HAVE / Riesgo Alto]: Compatibilidad y puestos en los que puedo confiar.**
  Como candidata, quiero que la nota y los puestos sugeridos salgan de lo que he hecho de verdad, para no
  perder tiempo ni enviar candidaturas a puestos ajenos.

  Scenario: Puesto sin evidencia
  Given mi CV solo nombra «Excel» como habilidad
  When Horma sugiere puestos
  Then «Controller financiero» no llega marcado
  And cada puesto marcado cita el puesto que ya he tenido

- **Qué incluye** (RF-006, RF-007):
  - Puestos afines según el informe F4 (F4-D1 a D9, decididas). Primero se mide con un set de 30 CV (F4-D5);
    junior sin experiencia: puestos por titulación, marcados (F4-D7); set de la 9a repasado y con ~50
    sinónimos (F4-D9).
  - Sinónimos de puestos (F4-D6): la cobertura bajó a 0,58, se midieron tres vías y entran una tabla en código y
    las formas que da el modelo pequeño (D-053, D-061; 0,68 en puestos nuevos). Embeddings y ESCO, descartados
    por lo medido.
  - Medir mejor: eval `recomendacion` de 21 a unos 60 casos (más sectores, notas intermedias, perfiles casi
    vacíos, ofertas incompletas y correcciones importadas), 3 ejecuciones por caso y el orden de la lista
    además del ±10. Los tramos de la nota ya están en el prompt, sin medir.
  - Explicaciones fiables: el `matcher` cita fragmentos literales y un verificador en código comprueba que
    existen; no nombra las instrucciones embebidas de una oferta. Revisor, solo en el eval: cada rechazo se
    juzga dos veces más y cuenta si lo confirman 2 de 3; Mar revisa los confirmados (D-098).
  - Equidad: el clasificador y el `matcher` leen una copia del perfil sin nombre y con los puestos en «/a»
    (D-043 a D-047; spec 012, RF-12.30); en edad, nacionalidad y huecos, pares con la nota igual (±3).
  - Robustez: ofertas en otro idioma, muy largas, con inyección o sin datos; fallos parciales. Falla con
    aviso, nunca con una nota inventada. Ignorar el texto invisible en `convertir_cv`.
  - Familia de cada oferta (F4-D3: los puestos genéricos casan solo con ofertas de su familia).
  - Correcciones de la usuaria: su nota manda en su lista y ve el motivo que escribió; Mar las revisa antes de
    cada medición del eval (D-027).
  - Punto 3 · Condiciones: fuera de la nota, como LinkedIn, Indeed y Jobright. Una línea junto al veredicto dice
    la condición que falta o no se cumple y, a igual nota, va antes la que cumple todo (D-026).
  - Veredicto en palabras junto a la nota, puesto por código y por franjas (F7-D5): «Muy compatible»,
    «Compatible», «Poco compatible», «No te la recomendamos». La frase de la nota por franjas (70-100, 50-69,
    30-49, 0-29) la pone el código, con la nota ya acotada (D-080).
  - Nota acotada por código (D-080): el `matcher` marca cada requisito de la oferta (cubierto, a medias o no) y
    su relación con el puesto, sigue dando la nota y el código le pone suelos y topes.
  - Tener más de lo que pide la oferta no resta; se avisa junto al veredicto: «Pide menos de lo que tienes»
    (D-081).
  - Otro oficio (D-084 y D-085): cumplir lo pedido desde otro oficio deja la nota entre 30 y 55; lo afín no se
    acota, y una oferta que casa con un puesto marcado por ella en «Qué buscas» no cuenta como otro oficio.
  - Ahorro: puntuar con el modelo pequeño si pasa el eval (F1-E6) [pendiente: se decide con la medición].
- **Puerta de salida:** eval `recomendacion` ≥ 0,90 dentro de ±10, estable en 3 ejecuciones (NFR-02) y de
  vuelta en `evals-reales`; 100 % sin rasgos personales ni diferencias por pares; 100 % de explicaciones con
  citas verificadas; revisor con al menos el 95 % sin rechazo confirmado por pasada y 0 graves (D-098); set de
  30 CV en sus umbrales (sección 2); ningún puesto marcado sin evidencia; revisión de Mar sobre 20
  recomendaciones.
- **Depende de:** el paso 1. Gasto real: ~5-7,3 USD en todo el paso, en varias veces (set de 30 CV y evals;
  detalle en el plan de la spec 012), cada vez con el OK de Mar. Corregir la nota (T14a a T14h) añade hasta
  3,9 USD y puede superar esa cifra; su ejecución completa vale como la de la puerta si pasa todo (D-086).
  Cerrarla por etapas (D-100) tiene un tope de 2,6 USD: la pasada 1 y, solo si pasa, la 2 y la 3.

### Paso 5 · Ingesta y vigilancia (spec 014)

- **Por qué va ahí:** justo después del paso 2 (D-095): más ofertas solo sirven cuando ya se puntúan bien. Espera a la investigación
  del banco de ofertas (DEP-01), entregada el 25-nov; faltan su ampliación sobre ingesta robusta (F10, D-097) y la
  prueba práctica.
- **Historia — US-005 [MUST HAVE / Riesgo Medio]: Más ofertas de España y vigentes.**
  Como candidata, quiero ver muchas ofertas de España que sigan abiertas, para tener donde elegir.

  Scenario: Oferta cerrada
  Given una oferta del catálogo ya no está publicada
  When Horma va a puntuarla o a redactar su candidatura
  Then lo comprueba antes, no gasta en ella y la retira

- **Qué incluye** (RF-010, RF-011):
  - Ingesta programada, sin la administradora. El programador de tareas se crea aquí y lo reutiliza el paso 7.
  - Ritmo y buenas prácticas (bloque A; se construye en este paso, no antes): el ingestor cumple RT-15 a RT-19 de `system.md`
    (pausa por dominio, `Retry-After` y reintentos con espera, extracción incremental, sin datos personales
    de terceros). El estado incremental y el ritmo por dominio se guardan en Postgres, a través de la API.
  - Comprobar con código que la oferta sigue abierta antes de puntuarla, redactar o enviar (F7-D4).
  - Cómo ampliar las ofertas (F7-D2, decidida el 25-nov): solo vías gratuitas, es decir, feeds documentados de
    ATS y datos abiertos públicos. La compra de ofertas queda para el futuro.
  - Webs de empleo españolas con Playwright (D-096): solo las que pasen el análisis previo; primero se mide en la
    prueba práctica cuántas ofertas nuevas aportan. Sin proxies, disfraces ni saltar bloqueos.
  - Workday (D-020): por el sitemap y el marcado `JobPosting` del tablón público de cada empresa y por sus
    webs de empleo propias. Nunca por su API interna.
  - Fuentes nuevas (punto 14; D-025): Feina Activa, Lanbide, ECyL (si se confirma su conjunto de datos) y,
    al final, Manfred, además de los ATS de F1. Solo con permiso escrito del portal: Welcome to the Jungle,
    Turijobs, Infoempleo y Tecnoempleo. InfoJobs no: su API es solo para empresas constituidas (D-067). Fuera: Jooble, Adzuna, Careerjet y EURES; SEPE, en vigilancia.
    Ninguna se activa sin calificación apta. Con ella, cada fuente entra como cambio pequeño: conector, test
    y una línea en las tareas de la 014. Punto 8: todas las empresas de Greenhouse y, después, Lever.
  - Vigía semanal de portales nuevos; clasificar solas las fuentes que no están en Horma.
  - Enseñar el texto de la oferta según las condiciones de cada fuente.
  - Corrección: Admin › Fuentes enseña «sin límite» en arbeitnow.
- **Puerta de salida:** la ingesta corre sola 7 días seguidos, sin la administradora; 5.000 ofertas vigentes de
  España en el catálogo (D-024); una oferta cerrada se retira sin gastar (test); tests de RT-15 a RT-19 en verde.
- **Depende de:** DEP-01 (F5) y el paso 2.

### Paso 3 · Calidad de CV y carta, con PDF comprobado (spec 013)

- **Por qué va ahí:** lo que lee la empresa tiene que ser bueno y estar comprobado antes de que Horma pueda
  enviarlo. Va tras el paso 5 (D-095) y necesita el 2 porque el aviso de eliminatorios se apoya en la compatibilidad.
- **Historia — US-004 [MUST HAVE / Riesgo Medio]: Un CV y una carta que pasan a quien los lee.**
  Como candidata, quiero que mi CV y mi carta pasen el ATS, la IA de selección y a la recruiter sin inventar
  nada, para llegar a la entrevista.

  Scenario: PDF comprobado
  Given Horma ha redactado mi CV para una oferta
  When genera el PDF
  Then comprueba en el propio PDF el orden de lectura, las tildes y el contacto
  And me avisa si la oferta pide algo eliminatorio que no consta en mi perfil

- **Qué incluye** (RF-008, RF-009):
  - Rúbricas y ejemplos del informe F2 (F2-D1 a D9) en `redactor-cv`, `redactor-carta` y `juez-candidatura`,
    con evals. Sin agente solo para la carta: `redactor-carta` ya lo es (F2-D5).
  - Panel de tres lectores (ATS, IA de selección y recruiter), sin inventar: **primordial para Mar.** La IA de
    selección es un agente pequeño nuevo, `lector-ia` (D-041); ella ve tres líneas en la candidatura (D-042).
  - Comprobación del PDF final y puerta de hechos sin modelo antes del PDF: cifras, fechas y nombres (F7-D3). Sin
    listas de verbos ni de cargos: se puede decir con más fuerza lo que la descripción respalda, como liderar sin
    el cargo o un «nivel medio» como B2 (D-054).
  - Contacto (correo, teléfono, ciudad y LinkedIn) en Perfil; lo pone el código en el PDF y nunca llega al modelo
    (D-039).
  - CV: experiencias con tareas y logros (el perfil no cambia: el redactor los distingue, D-040); ideas para
    medir los logros en el aviso «Sin cifras», con un agente pequeño nuevo, `ideas-logros` (D-055); mejor
    redacción; diseños aptos para ATS, elegibles.
  - Carta: mejor redacción y diseño; tono formal o informal según la oferta; carta honesta y simple como seña
    de Horma; reglas de las mejores guías de cartas (D-056); saludo a la persona de selección si la oferta da su
    nombre, con «Sr.» o «Sra.» si la oferta lo deja claro, y, si no, al equipo de selección de la empresa (D-057 y
    D-060).
  - Requisitos eliminatorios: avisan y no frenan; ella puede enviar la candidatura igual (D-058).
  - Editor tipo procesador de texto (negrita, listas, títulos), sin Markdown a la vista.
  - Del cruce del 22-nov: falsos «Dato dudoso», recortes del extractor (eval `perfil`) y «manejo de
    ordenador» como hueco (F2-D3).
  - Landing: solo promete lo que ya funciona. El mensaje de Horma (F7-D1) pasa al paso 9 (D-066).
  - Marca de «generado con IA» en el PDF (F9-D7): [pendiente: solo si la asesoría legal confirma que obliga].
  - Las fechas MM-AAAA no cambian: en la prueba propia del PDF (DEP-05, 26-nov), guion y barra dieron lo mismo.
- **Puerta de salida:** eval `cv` con 0 frases sin origen (NFR-01); el PDF, comprobado en el 100 % de las
  candidaturas; eval `perfil` en su umbral; panel de lectores: programas 100 %, IA ≥ 0,90 y persona ≥ 0,90
  (D-042; spec 013, RF-13.32).
- **Depende de:** el paso 2 y DEP-05. Gasto real: ~3,6-5,2 USD en todo el paso, en varias veces (evals `cv`,
  `perfil`, `ofertas`, `lector-ia` e `ideas-logros`; detalle en el plan de la spec 013), cada vez con el OK de Mar.

### Paso 4 · Privacidad y cuenta (spec 015)

- **Por qué va ahí:** sin base legal no puede entrar ninguna usuaria (R-04). Además crea la pantalla
  «Configuración» y los consentimientos, que reutilizan la entrevista (paso 6) y el envío (paso 7).
- **Historia — US-003 [MUST HAVE / Riesgo Alto]: Mis datos, bajo mi control.**
  Como candidata, quiero saber qué hace Horma con mis datos y poder borrarlos o llevármelos, para usarla con
  confianza.

  Scenario: Borrar la cuenta
  Given tengo perfil, candidaturas y documentos subidos
  When pulso «Borrar mi cuenta» en Configuración y lo confirmo
  Then no queda ningún dato mío, salvo lo mínimo bloqueado que exige la ley
  And mi nombre, correo y teléfono nunca han llegado al modelo

- **Qué incluye** (RF-012, RF-013; informe F9):
  - Quitar nombre, correo y teléfono antes del modelo, en la puerta única (RT nuevo).
  - Política de privacidad, avisos y consentimientos (F9, apartado 11); página de subencargados y «no
    entrenamos».
  - Borrar la cuenta, descargar los datos y plazos de conservación (F9-D8).
  - Arreglos de F9 (apartado 3): borrar un CV borra lo derivado (RF-10.14); RLS en los puntos de control de
    LangGraph y en `llm_llamadas`; filtro del art. 9 antes del modelo; plazos y limpieza de registros;
    `exportar` y `--traza` sin datos reales; Anthropic y Google en `revision-lineas-rojas.md`.
  - Pantalla «Configuración», abierta desde el nombre en la cabecera: consentimientos, borrar y descargar. Los
    ajustes del envío se añaden en el paso 7. Solo preferencias de comodidad, nunca salvaguardas.
- **Puerta de salida:** los 9 hallazgos de F9, a 0; borrar y descargar, probados por Mar; test de que ningún
  prompt lleva contacto (NFR-04).
- **Depende de:** el paso 3. La evaluación de impacto (DEP-03) y la asesoría legal (DEP-04) no bloquean
  construir: bloquean el paso 9.

### Paso 6 · Entrevista por texto (spec 016; sustituye a la parte 9b de la 009)

- **Por qué va ahí:** usa los consentimientos del paso 4 y deja lista la tabla de respuestas que comparte con
  el envío (paso 7). Es de riesgo bajo.
- **Historia — US-008 [SHOULD HAVE / Riesgo Bajo]: Entrevista por texto.**
  Como candidata, quiero responder por escrito o dictando a preguntas de recruiter, para resolver huecos de mi
  perfil y que mis CV y cartas suenen a mí.
- **Qué incluye** (RF-014):
  - Una sola spec con texto, dictado y un agente (`entrevistador`). Sustituye a la 9b, retirada de la spec
    009; parte de RF-10.12 y RF-10.12b.
  - Tras el CV maestro: resuelve huecos, guarda respuestas con origen y capta el estilo. Pregunta cifras y
    alcance (F2-D7). Una sola tabla de respuestas, compartida con el paso 7.
  - Preguntas escritas desde la oferta y el CV; nunca copiloto en vivo (F7-D10).
  - Dictado con un botón de micrófono: primero en el dispositivo; si no se puede, en la nube y con aviso
    previo (F9-D6).
- **Puerta de salida:** [pendiente: al aprobar el catálogo de preguntas]; eval del agente en su umbral; las
  respuestas se usan como fuente con origen. Coste por entrevista: [pendiente: sin medir].
- **Depende de:** el paso 4.

### Paso 7 · Envío y correo, en modo prueba (spec 011, parte 2)

- **Por qué va ahí:** es lo más arriesgado y lo único que no se deshace (R-01). Se construye cuando lo que
  envía —nota, puestos, CV, carta y datos— ya es fiable, y siempre en modo prueba.
- **Historia — US-001 [SHOULD HAVE / Riesgo Alto]: Horma envía por mí dentro de mi regla.**
  Como candidata, quiero que Horma envíe las candidaturas que cumplen una regla que he visto y confirmado, para
  no rellenar cada formulario a mano.

  Scenario: Envío en la tanda
  Given he activado «Enviar candidaturas por mí» con compatibilidad mínima 75 y tope de 3 al día
  And una oferta cumple mi regla y su candidatura no tiene avisos
  When llega la hora de la tanda y no he pulsado «Parar»
  Then Horma la envía y la veo en «Enviadas» con cada respuesta y su origen
  And nunca salen más de 3 en el día

  Scenario: Falta un dato
  Given el formulario tiene una pregunta obligatoria sin respuesta con origen
  When Horma prepara el envío
  Then se para, me lo pregunta en «Pendientes de ti» y no envía nada hasta que respondo

- **Historia — US-007 [SHOULD HAVE / Riesgo Medio]: Horma sigue las respuestas.**
  Como candidata, quiero que Horma lea las respuestas de las empresas y actualice mis candidaturas, para no
  anotarlas a mano.
- **Qué incluye** (RF-002 a RF-005). Se especifica al llegar el paso, como parte 2 de la spec 011. Insumos:
  el informe F3 y la spec del 23-nov, archivada, cuyas decisiones (P1-P14) siguen valiendo.
  - Regla de envío, ajustes del envío en «Configuración» y puestos de envío, que se activan, desactivan y
    eliminan (F4-D8: solo los de nivel 1 o marcados por ella).
  - Formulario y respuestas con origen; bandeja «Pendientes de ti». Permiso de trabajo y datos que solo ella
    puede dar: se usan en ese envío y se borran, salvo que ella active guardarlos; el modelo nunca los ve
    (F9-D3). ⚠️ Cambia la constitución y RT-09.
  - Flujo, puerta de envío, registro a la vista y portal de mentira; canal de navegador con pasos fijos.
  - Dirección de Horma con copia a su correo y seguimiento de respuestas (F3-D6); «Deshacer».
  - Tanda con aviso la víspera, «Parar», «Parar todo» y vigilancia de portales con pausa automática.
  - De F9: la casilla de privacidad, solo como acuse (F9-D2); sin portal fijo, se elige tras medir (F9-D4).
  - El envío guarda su estado en un solo sitio: lo confirma el plan de la parte 2.
  - Pasan a otros pasos: Configuración y consentimientos (paso 4), programador de tareas y «la oferta sigue
    abierta» (paso 5), tabla de respuestas (paso 6).
- **Puerta de salida:** recorrido completo de Mar en modo prueba; evals `formulario` (0 respuestas inventadas)
  y `respuestas`, con las adversarias al 100 %; 0 peticiones a un portal real (NFR-05).
- **Depende de:** los pasos 1 a 6 y DEP-06 (dominio y correo, antes de construir el buzón).

### Paso 8 · Gasto por usuaria (spec 017; sustituye a RF-8.5 y RF-10.9d)

- **Por qué va ahí:** los topes se fijan cuando ya se conoce el consumo real de todas las funciones.
- **Historia — US-006 [MUST HAVE / Riesgo Medio]: Sé cuánto me queda.**
  Como candidata, quiero ver cuánto puedo usar Horma este mes y que me avise antes del límite, para que no se
  pare sin aviso. Escenario: [pendiente: tras el informe de gasto].
- **Qué incluye** (RF-015; punto 12, obligatorio para Mar):
  - Hoy es provisional: 1 USD al día por usuaria (RF-10.9) y las reglas de cuándo se puntúa (RF-8.5).
  - Por decidir, con el informe (F1, apartado 12: E1 a E5 y E13 a E15): topes por plan, qué pasa al llegar
    al tope, avisos, unidades que la usuaria entienda y cómo encaja con la alerta de la administradora (más de
    5 USD al día).
  - Avisos de presupuesto pendientes de la pasada (L2 y L3).
  - Supuesto sin medir: 0,50 USD al día ≈ 150 ofertas puntuadas.
- **Puerta de salida:** [pendiente: informe de gasto]; test del worker con tope bajo; la usuaria ve su consumo
  y recibe el aviso antes del límite (NFR-06).
- **Depende de:** DEP-02 (límites de gasto en la competencia y precio) y el paso 2.

### Paso 9 · Salida a usuarias (sin spec propia)

- **Por qué va ahí:** es la comprobación de que todo lo construido aguanta a personas reales.
- **Historia:** ninguna nueva; valida las ocho.
- **Qué incluye:**
  - Punto 6 · `evals-reales` otra vez en la CI para los PR a `main`, como check obligatorio. Con él, punto 9:
    la medición final de la fase 5 (~1,8 USD), solo si Mar la pide.
  - Red-teaming (PR #8, aparcado: se rehace en una rama nueva desde `main`). Umbral: [pendiente: 100 % o ~95 %
    con el modelo real; consulta al profesor].
  - Mensaje de Horma en la landing (F7-D1): [pendiente: lo decide Mar mientras se construye el paso 8, D-066].
    Propuesta de partida: «CV y carta con cita, en español y para cualquier sector».
  - Prueba con cinco personas y repaso de Mar a 390 px.
  - Límites de ritmo: hoy viven en la memoria de un proceso; con varios, pasan a Postgres (NFR-07).
- **Puerta de salida:** `evals-reales` en verde y obligatorio; red-teaming en su umbral (NFR-03); prueba con
  cinco personas hecha; evaluación de impacto hecha.
- **Depende de:** los pasos 2 a 8, DEP-03, DEP-04 y DEP-08.

### Paso 10 · Envío real (spec 011, parte 3)

- **Por qué va ahí:** un envío real no se deshace. Va el último, con todo probado y la parte legal cerrada.
- **Historia:** US-001, fuera del modo prueba.
- **Qué incluye:** ensayo real con Mar y escribir a empresas por correo, diciendo que lo
  envía un agente de IA (RES-05).
- **Puerta de salida:** [pendiente: se fija al especificar la parte 3 de la 011].
- **Depende de:** el paso 9, DEP-03, DEP-04 y DEP-07 (portal elegido y sus condiciones, leídas).

## 5. Requisitos del Sistema (FR & NFR)

### 5.1 Requisitos Funcionales (FR)

| ID | El sistema debe… | Spec | Paso |
|---|---|---|---|
| RF-001 | medir, sin enviar nada, a qué portal lleva cada oferta y cuántas exigen cuenta | 011 | 1 |
| RF-002 | enviar una candidatura solo con la aprobación de la usuaria o dentro de una regla que ella ha confirmado y puede parar | 011 | 7 |
| RF-003 | pararse y preguntar cuando falte un dato, aparezca un captcha o haya una duda; nunca adivinar | 011 | 7 |
| RF-004 | dejar cada envío registrado y a la vista: documentos, respuestas con su origen, resultado y coste | 011 | 7 |
| RF-005 | leer las respuestas de las empresas, casarlas con su candidatura y actualizar el estado, con «Deshacer» | 011 | 7 |
| RF-006 | sugerir puestos por niveles de evidencia y marcar solo los que la persona ya ha ejercido | 012 | 2 |
| RF-007 | acompañar la nota de compatibilidad con un veredicto en palabras y citas comprobadas | 012 | 2 |
| RF-008 | comprobar el PDF final y revisar CV y carta con tres lectores (ATS, IA de selección y recruiter) | 013 | 3 |
| RF-009 | avisar de los requisitos eliminatorios que no constan en el perfil | 013 | 3 |
| RF-010 | ingerir ofertas de forma programada, sin la administradora, y solo de fuentes calificadas como aptas, cumpliendo RT-15 a RT-19 | 014 | 5 |
| RF-011 | comprobar que una oferta sigue abierta antes de puntuarla, redactar o enviar | 014 | 5 |
| RF-012 | ofrecer una pantalla «Configuración» con los ajustes de la usuaria, sus consentimientos, borrar la cuenta y descargar sus datos | 015 | 4 |
| RF-013 | mostrar los textos legales y pedir cada consentimiento antes de tratar el dato | 015 | 4 |
| RF-014 | hacer una entrevista por texto, con dictado en el dispositivo, y usar las respuestas como fuente con origen | 016 | 6 |
| RF-015 | enseñar a la usuaria su consumo en unidades que entienda y avisarla antes del límite | 017 | 8 |
| RF-016 | mostrar el aviso de dato personal retirado, calificar como «no apta» una fuente que responde 403 y unificar los controles de Ofertas y Perfil (botones de archivo, resaltado, barras y rango de compatibilidad) | 011 | 1 |

### 5.2 Requisitos No Funcionales (NFR) y Criterios de Evaluación (Evals)

| ID | Atributo (arc42) | Fit Criterion / Enunciado Verificable | Método de Verificación / Eval |
|---|---|---|---|
| NFR-01 | Veracidad | 0 frases de CV o carta sin origen; 0 respuestas de formulario inventadas | Evals `cv` y `formulario`; `verificar_trazabilidad` |
| NFR-02 | Calidad de la recomendación | ≥ 90 % de los casos con la nota dentro de ±10, en 3 ejecuciones seguidas | Eval `recomendacion` con el modelo real |
| NFR-03 | Seguridad | 100 % de instrucciones embebidas sin efecto en ofertas, CV, formularios y correos | Casos adversarios de cada eval; `red-teaming` |
| NFR-04 | Privacidad | Ningún prompt lleva contacto, edad, nacionalidad ni datos del art. 9; cada usuaria solo lee lo suyo. El clasificador y el `matcher` leen una copia sin nombre ni género (spec 012, RF-12.30) | Tests de la puerta única, de la copia y de RLS |
| NFR-05 | Control de la usuaria | «Parar todo» corta antes del envío siguiente; fuera del modo real, 0 peticiones a un portal de verdad | Tests de la tanda y del guardia de red |
| NFR-06 | Coste | ≤ 1 USD por usuaria y día y ≤ 1 USD por candidatura; tope mensual: [pendiente: spec 017] | Tabla `llm_llamadas`; test del worker con tope bajo |
| NFR-07 | Volumen | 5 usuarias a la vez y 5.000 ofertas vigentes en el catálogo, sin errores ni tareas perdidas. La cifra de ofertas queda confirmada tras la investigación del banco de ofertas (D-024): 5.000 vigentes de España. Hoy sin medir; los límites de ritmo viven en la memoria de un solo proceso (el de la ingesta lo resuelve RT-16, paso 5) | Prueba de carga sencilla en el paso 9 |
| NFR-08 | Latencia | [pendiente: se mide en el paso 9]. Todo lo lento corre en la cola, con su avance a la vista | [pendiente: se mide en el paso 9] |
| NFR-09 | Usabilidad | Cada pantalla, correcta a 1280 y 390 px, en claro y oscuro; zonas táctiles de 44 px; sin jerga | Revisión en navegador por tarea; test de palabras prohibidas |
| NFR-10 | Mantenibilidad | Agentes sin estado; una sola puerta al modelo; los routers solo llaman a servicios | `import-linter` en la CI |

## 6. Restricciones Técnicas y de Negocio (RES)

- RES-01 (Arquitectura): Python, monolito con API, worker y Postgres, frontend plano con tokens; sin RAG
  (fuente: constitución, Mar).
- RES-02 (Arquitectura): agentes sin estado ni E/S; el modelo solo se llama por `horma.llm`; la composición vive
  en los flujos (fuente: `system.md`, RT-01, RT-02, RT-12, RT-13).
- RES-03 (Legal): las líneas rojas de la constitución, completas. Entre ellas: nunca LinkedIn ni Indeed, nunca
  eludir un captcha y ninguna candidatura sin aprobación (fuente: Mar).
- RES-04 (RGPD): datos de prueba inventados hasta cerrar la spec 015 y la evaluación de impacto (fuente:
  constitución; revisión de RGPD).
- RES-05 (Reglamento de IA): un mensaje escrito por un agente a una persona dice que es una IA y en nombre de
  quién (fuente: art. 50.1).
- RES-06 (Presupuesto): 1 USD al día por usuaria; el gasto real en evals necesita estimación y el OK de Mar
  (fuente: Mar).
- RES-07 (Despliegue): local con Docker Compose; una sola construcción a la vez (fuente: profesor, 17-nov; Mar).
- RES-08 (Identidad): Google OAuth, sin contraseña propia (fuente: constitución).
- RES-09 (Repositorio): `main` protegida y todo por PR; el repo no guarda datos de personas ni documentos de
  trabajo (fuente: `AGENTS.md`).

## 7. Fuera de Alcance (Exclusiones Explícitas del Sistema)

Revisada el 25-nov-2026 (Mar): la agregación de ofertas públicas pasa a alcance activo.

### 7.1 En alcance: agregación de ofertas públicas

Horma ingiere, agrega y normaliza ofertas públicas de empleo de múltiples portales, ATS y fuentes
estructuradas, como un indexador de ofertas públicas.

- **Vías:** conectores, API, feeds, sitemaps, marcado `JobPosting` y API de índices públicos de ofertas.
- **Herramientas:** `httpx` por defecto; Apify, Zyte, Crawlee, Scrapy y Firecrawl cuando hagan falta.
- **Condiciones, siempre:** ritmo limitado por dominio, espera con `Retry-After` y reintentos, extracción
  incremental y ningún dato personal de terceros (RT-15 a RT-19 de `system.md`); sin cuentas ni contraseñas;
  cada fuente, con calificación apta.
- **Límite que no cambia:** las líneas rojas de la constitución (RES-03). Nunca LinkedIn ni Indeed, tampoco
  cuando una oferta suya llega a través de un índice o de un tercero.
- De momento, solo vías gratuitas (F7-D2).

### 7.2 Exclusiones que se mantienen

1. **No hay lado empresas ni recruiters.** Abrirlo convertiría a Horma en sistema de alto riesgo.
2. **No usa LinkedIn ni Indeed,** ni como fuente ni para enviar. InfoJobs y Welcome to the Jungle sí están en
   alcance, como fuente (7.1) y para enviar, con las mismas reglas que cualquier portal (puntos 3 y 4). InfoJobs,
   como fuente, solo por su API, que es para empresas constituidas (D-067).
3. **No resuelve captchas, no rota IP, no disfraza el navegador, no crea cuentas y no entra en áreas privadas.**
4. **No guarda contraseñas de portales.** Los portales con cuenta quedan como «Envíala tú».
5. **No envía en Greenhouse ni por la API de Recruitee.**
6. **No conecta el buzón de la usuaria** (Gmail, Outlook): solo lee la dirección de Horma que ella activa.
7. **No es copiloto de entrevista en vivo,** ni hace entrevista por voz ni valora las respuestas.

### 7.3 Diferido (en `docs/mejoras-futuras.md`)

No son exclusiones de principio: no entran ahora.

- Servidor MCP, extensión de navegador y aplicación nativa.
- Fuera de España y otros idiomas.
- Embeddings y taxonomías externas.
- Precio y planes de pago: esperan a su estudio de mercado.
- Alojamiento en la UE y despliegue fuera de local.
- Compra de ofertas a proveedores.

Entrar en alcance desde 7.2 o 7.3 exige cambiar este PRD.

## 8. Gestión de Riesgos y Mitigación

| Riesgo Identificado | Impacto | Probabilidad | Estrategia de Mitigación |
|---|---|---|---|
| R-01: Un envío erróneo no se deshace | Alto | Media | Regla confirmada, tanda con aviso, tope diario, modo prueba y PDF comprobado antes del modo real (NFR-01, NFR-05) |
| R-02: Pocas candidaturas salen solas (captchas, cuentas) | Alto | Alta | Medirlo antes de construir (RF-001); lo no automático queda preparado como «Envíala tú» |
| R-03: Un puesto ajeno acaba en una candidatura enviada | Alto | Media | Puerta de puestos por evidencia antes del envío (RF-006, NFR-02) |
| R-04: Entra una usuaria real sin base legal | Alto | Baja | La spec 015 y la evaluación de impacto bloquean el alta (RES-04) |
| R-05: La usuaria no se fía del envío y no lo activa | Medio | Media | Registro a la vista, «Parar todo» y prueba con cinco personas |
| R-06: Ofertas caducadas o fantasma | Medio | Alta | Comprobar que siguen abiertas (RF-011) |
| R-07: Una fuente o un portal cambia sus condiciones o su formulario | Medio | Alta | Calificación de fuentes; vigilancia diaria con pausa automática |
| R-08: El coste por usuaria supera lo que pagaría | Medio | Media | Topes (NFR-06), puntuar con el modelo pequeño si pasa el eval y estudio de precio |
| R-09: La asesoría legal la da un agente, que no firma | Medio | Media | Consulta humana corta para lo irreversible antes de la primera usuaria: [pendiente: decide Mar] |

## 9. Dependencias Críticas

- DEP-01: investigación del banco de ofertas (Fable: F5, entregada, y su ampliación F10, D-097) y prueba práctica de ingesta (Sonnet); desbloquean el paso 5 y RF-010.
- DEP-02: investigación de los límites de gasto en la competencia (entregada el 25-nov) y estudio de precio,
  pendiente (Fable); desbloquean el paso 8 y NFR-06.
- DEP-03: evaluación de impacto en Gestiona RGPD (Mar), mientras se construye el paso 8 (D-066); desbloquea los
  pasos 9 y 10.
- DEP-04: asesoría legal (agente de abogacía, que se crea mientras se construye el paso 8, D-066); cierra la casilla de privacidad, la marca de
  «generado con IA» y el modo real.
- DEP-05: prueba propia del PDF en cuatro formularios reales (Mar, 30 min): hecha (26-nov); ya no frena el paso 3.
- DEP-06: dominio y correo entrante (Mar, ~10-15 € al año); desbloquea RF-005 y da la dirección de contacto del `User-Agent` del ingestor (RT-15).
- DEP-07: condiciones de uso del primer portal real, leídas (Teamtailor o Personio); desbloquean el paso 10.
- DEP-08: el profesor revisa el RGPD y este PRD.

**Control de Trazabilidad:** este PRD mapea contra RF-001 a RF-016, NFR-01 a NFR-10, RES-01 a RES-09 y las
historias US-001 a US-008. Cada requisito de una spec (RF-N.x) cita el suyo. Las decisiones que lo sostienen y
las que cambiaron están en el registro de decisiones de `docs/hoja-de-ruta.md` (documento de trabajo).
