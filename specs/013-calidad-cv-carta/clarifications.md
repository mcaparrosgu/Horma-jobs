---
type: clarifications
title: calidad-cv-carta — Aclaraciones
description: Decisiones que sostienen la spec 013 (paso 3 del PRD) — las ya tomadas en F2, F7 y F9, las cuatro que Mar cerró el 26-nov (D-039 a D-042), sus cambios al firmar (D-054 a D-059), la síntesis de las guías de cartas y los supuestos de Opus, firmados.
tags: [clarify, cv, carta, pdf, panel, eliminatorios]
status: active
sources: [../prd.md, ../003-candidatura/clarifications.md, ../010-simplificacion/spec.md, ../012-matcher-puestos/spec.md]
generated: { at: 2026-11-26 }
verified: { by: human, at: 2026-11-26 }
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
| F2-D5 | Carta con rúbrica nueva; sin agente nuevo: `redactor-carta` ya es uno aparte. Saludo con el nombre de la empresa. Cambiada en el saludo por D-057 |
| F2-D6 | La carta usa la papelería del CV |
| F2-D7 | Viñetas con verbo, qué y alcance o resultado; cifra solo si está en el perfil |
| F2-D8 | Tú o usted, espejo de la oferta; la guía de estilo de la usuaria manda |
| F2-D9 | Eliminatorias a la vista, sin modelo, desde los huecos |
| F7-D3 | Puerta de hechos sin modelo antes del PDF (cifras, cargos, deriva de verbos), tras ver qué cubre `verificar_trazabilidad`. Cambiada por D-054: sin listas de verbos ni de cargos |
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

## Cambios de Mar al firmar (26-nov)
- **D-054 · Sin regla de deriva (RF-13.1).** «Si fuese por mí, esta regla la quitaríamos»: un nivel medio de inglés
  es un B2, y liderar un equipo sin el cargo ni el sueldo también cuenta. Se quitan las listas de verbos y de cargos.
  Siguen la traza de cifras, fechas y nombres, el cargo de cada puesto y el juez: lo que la descripción no cuenta,
  Horma no lo puede saber, así que ella lo escribe en Perfil.
- **D-055 · Ideas para medir logros (RF-13.4b).** A muchas personas les cuesta pensar en logros medibles: el aviso
  «Sin cifras» da preguntas generales y lo que suele medirse en su puesto.
- **D-056 · Carta según las mejores guías (RF-13.8).** Síntesis de 15 guías de referencia, más abajo; sus reglas
  entran en el prompt y en las comprobaciones de código, sin saltarse las de Horma.
- **D-057 · Saludo (RF-13.10).** A la persona de selección si la oferta da su nombre; si no, «Hola, equipo de
  selección de <empresa>:».
- **D-058 · Eliminatorios que avisan y no frenan (RF-13.22).** Ella puede aprobar y enviar la candidatura igual.
- **D-059 · Firma.** Aclaraciones, spec, plan y tareas, firmados con estos cambios.
- **D-060 · «Sr.» o «Sra.» en el saludo (RF-13.10; Mar, tras la firma).** «Hola, Sra. Laura García:». Solo cuando la
  oferta deja claro cuál es; el nombre solo no lo dice (Andrea, Alex, Noa o Cruz), y equivocarse en el saludo es lo
  primero que lee la persona de selección.

## Supuestos (Opus; firmados por Mar el 26-nov)
- **S1 · Niveles de idioma:** tabla cerrada en código. «Básico» = A1 o A2; «medio» o «intermedio» = B1 o B2;
  «intermedio alto» = B2; «avanzado» o «alto» = C1; «bilingüe» o «nativo» = C2 o nativo. Fuera de la tabla, el nivel
  sale con las palabras del perfil. *(Sustituye a las listas de verbos y cargos, quitadas por D-054.)*
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
  oferta, junto a las condiciones (RF-12.25), para no gastar en una candidatura que se va a descartar. Avisan y no
  frenan (D-058).
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
- **S18 · Ideas para medir logros (D-055):** botón «Ideas para medirlo» en cada experiencia del aviso «Sin
  cifras». Las preguntas generales están en código y salen al momento (0 USD): personas atendidas, volumen, tiempo,
  renovaciones o ascensos, personas formadas, qué mejoró. Las del puesto las da `ideas-logros` (modelo pequeño,
  ~0,001 USD por experiencia): recibe solo el cargo, el sector y la descripción, sin nombre ni contacto, y devuelve
  de 3 a 5 preguntas. Se guardan por experiencia; si ella cambia el puesto o la descripción, se piden de nuevo. Las
  ideas no son fuente: ni el redactor ni el juez las ven.
- **S19 · Persona de selección (D-057 y D-060):** `extractor-oferta` gana `persona_seleccion` (nombre tal cual, o
  nada) y `tratamiento_seleccion` («Sr.», «Sra.» o nada). El tratamiento sale solo si la oferta lo deja claro: lo
  escribe («Sra. García», «D.ª Laura García») o habla de esa persona con una palabra con género («nuestra técnica de
  selección, Laura García»). Nunca se deduce del nombre. El código da el nombre por bueno solo si está literal en el
  texto de la oferta. Las ofertas guardadas antes no lo tienen y
  usan el saludo al equipo; no se reprocesan.

## Guías de la carta (D-056; síntesis del 26-nov)
Se leyeron 15 fuentes (lista abajo); The Muse, Randstad y Ask a Manager no se dejaron leer. ★ = coinciden 5 o más.
Los ejemplos son patrones con frases inventadas: no se copia texto de las guías.

**Lo que entra en `redactor-carta`**
- ★ Estructura: saludo, apertura, cuerpo, cierre con el siguiente paso y despedida; 3-4 párrafos y una página como
  máximo. Una idea o un requisito por párrafo.
- ★ Apertura con el puesto (y su referencia, si la tiene) y por qué interesa, con algo concreto y no con elogios.
- ★ Cuerpo: los requisitos más importantes de la oferta, cada uno con un ejemplo concreto (dónde y con qué
  resultado); cifras si las hay; una historia breve mejor que una lista; lo que aporta, no lo que recibe.
- ★ Cierre: interés y petición de entrevista; agradecer la lectura cabe en la despedida («Gracias por tu tiempo»).
- ★ Saludo a la persona si la oferta da su nombre (11 fuentes), escrito tal cual; nunca un genérico vacío.
- ★ Nada de repetir el CV, de carta genérica ni de faltas.
- Tono breve, directo y natural; sin jerga, sin nada negativo sobre una misma y sin abusar del «yo».
- Seguir las instrucciones de la oferta (referencia, asunto). Lo que la IA escribe debe poder defenderse en la
  entrevista (Harvard): refuerza «no inventar».

**Patrones** (frases inventadas)
1. Puesto y un hecho que lo une: «El puesto de Analista de Datos pide automatizar informes con Python; en mi último
   trabajo automaticé 12 informes semanales.»
2. Lo que atrae de la oferta, con un hecho: «Me interesa que la atención sea en tres idiomas: llevo 4 años atendiendo
   en español, inglés y francés.»
3. Requisito, prueba y resultado: «La oferta pide SQL. Diseñé una base de datos de más de 30 tablas para los pedidos
   de mi equipo. Hoy la usan 15 personas a diario.»
4. Lo que falta y lo más cercano: «No he trabajado con Salesforce. He gestionado 400 cuentas en HubSpot durante 2
   años.»
5. Cierre: «Quiero aprender a llevar un proyecto de datos de principio a fin, y este puesto me lo permite. Me
   gustaría contarlo en una entrevista.»

**Choques con las reglas de Horma, y cómo se resuelven**
- **Fórmulas rancias** de los modelos españoles: van a la lista negra (K12): «me dirijo a usted», «me es grato»,
  «a la espera de sus noticias», «se despide atentamente», «quedo a su disposición», «espero tener la oportunidad»,
  «profesional proactivo», «empresa líder», «mi perfil encaja perfectamente», «mis habilidades encajarían»,
  «pasión», «entusiasmo». Riesgo: abundan en la web y el modelo tiende a usarlas; por eso las comprueba el código.
- **Abrir presentándose** (MIT, Michael Page, Yale): la primera frase es puesto y hecho; quién es se deduce del hecho.
- **Callar lo que falta** (Hays, Sevilla, UC3M): es el choque más serio. Se dice una vez, sin disculpa, solo si la
  oferta lo pide, y seguido de lo más cercano que sí tiene (patrón 4; Hays sí avala explicar cómo se cubre).
- **Entusiasmo y adjetivos:** la motivación se demuestra con un hecho, no se declara.
- **Halagos e investigar la empresa** (Hays, MIT): sin halagos; solo lo que dice la oferta, porque el agente no
  investiga y lo de fuera sería inventado.
- **Palabras clave de la oferta:** solo con un dato del perfil detrás, y sin copiar 6 palabras seguidas (S4).
- **Saludo formal** («Estimada Sra. López»): Horma usa «Hola, Sra. Laura García:» por decisión de Mar (D-057 y
  D-060), con dos puntos (norma de la RAE).

**Fuentes**
1. Universidad de Sevilla, «La carta de presentación». https://fisica.us.es/sites/fisica/files/users/user381/CARTA-PRESENTACION.pdf
2. UC3M, «Carta de presentación. Tips para destacar» (2026). https://www.uc3m.es/empleoyaccesoalmercadolaboral/media/empleoyaccesoalmercadolaboral/doc/archivo/doc_carta/carta-de-presentacion.pdf
3. Lanbide, «Carta de presentación». https://www.lanbide.euskadi.eus/informacion/carta-de-presentacion/weblan00-orientacion/es/
4. SEPE, «La carta de presentación, una herramienta para presentar nuestra candidatura» (2017). https://www.sepe.es/HomeSepe/que-es-el-sepe/comunicacion-institucional/noticias/detalle-noticia?folder=%2FSEPE%2F2017%2FNoviembre%2F&detail=carta-presentacion
5. EURES, «Want to improve your odds of getting hired? Get your cover letter right» (2025). https://eures.europa.eu/want-improve-your-odds-getting-hired-get-your-cover-letter-right-2025-09-19_en
6. InfoJobs, tres artículos (2021-2026). https://orientacion-laboral.infojobs.net/que-debe-incluir-y-que-no-una-carta-de-presentacion/ · https://orientacion-laboral.infojobs.net/5-consejos-crear-carta-presentacion-perfecta/ · https://orientacion-laboral.infojobs.net/la-carta-de-presentacion-como-herramienta-de-storytelling/
7. Michael Page España, dos artículos (2016). https://www.michaelpage.es/advice/candidatos/prepara-tu-cv/c%C3%B3mo-redactar-una-carta-de-presentaci%C3%B3n · https://www.michaelpage.es/advice/candidatos/prepara-tu-cv/la-importancia-de-una-carta-de-presentaci%C3%B3n
8. Hays España, dos artículos. https://www.hays.es/consejos-de-carrera/articulo/tips-para-redactar-una-buena-carta-de-presentacion · https://www.hays.es/consejos-de-carrera/articulo/debo-presentarme-a-un-trabajo-si-no-cumplo-todos-los-requisitos
9. Adecco España, «Cómo usar la IA para que tu carta de presentación suene natural» (2026). https://www.adecco.com/es-es/encuentra-trabajo/orientacion-laboral/carta-de-presentacion
10. Harvard FAS, Mignone Center for Career Success: guía del CV (Cover Letter Tips) y «AI for Resumes and Cover Letters». https://careerservices.fas.harvard.edu/resources/create-a-strong-resume/ · https://careerservices.fas.harvard.edu/ai-resumes-and-cover-letters/
11. MIT CAPD, «How to write an effective cover letter». https://capd.mit.edu/resources/how-to-write-an-effective-cover-letter/
12. Yale SOM, «Your Cover Letter» (2022). https://som.yale.edu/sites/default/files/2022-01/Your%20Cover%20Letter%20Guide.pdf
13. Indeed Career Guide, «How to Write a Cover Letter» (2026). https://www.indeed.com/career-advice/resumes-cover-letters/how-to-write-a-cover-letter
14. Purdue OWL, «Quick Content Tips for Cover Letters». https://owl.purdue.edu/owl/job_search_writing/job_search_letters/cover_letters_1_quick_tips/quick_content_tips.html
15. Harvard Business Review, «Cover Letters Still Matter. Write One That Works.» (2025; solo la parte abierta). https://hbr.org/tip/2025/04/cover-letters-still-matter-write-one-that-works

## Fuera de alcance
- Marca de «generado con IA» en el PDF (F9-D7): espera a la asesoría legal (DEP-04).
- Quitar el nombre antes del modelo: paso 4, spec 015 (F7-D7). El contacto nuevo nunca llega al modelo (D-039).
- Formato de fecha MM-AAAA: no cambia. Prueba propia del PDF (DEP-05, 26-nov): guion y barra dan lo mismo.
  SuccessFactors lee todo bien; Workday falla en las fechas con los dos y mete las certificaciones en formación;
  Greenhouse y Teamtailor no rellenan solos.
- Tú o usted como ajuste en «Configuración» (F2-D8): `docs/mejoras-futuras.md`.
- Separar tareas y logros en el perfil (D-040). Preguntar cifras y alcance en una entrevista: paso 6 (F2-D7); aquí,
  solo las ideas del aviso «Sin cifras» (D-055).
- Volver a leer con IA tras editar (S9). Citar por número de línea (S2).
- CV para otros países (F2, apartado 5).
