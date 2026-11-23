---
type: tasks
title: simplificacion — Desglose de tareas
description: Tareas pequeñas y comprobables de la simplificación, por bloques S1-S10. Cada una empieza con un test que falla; las de pantalla se comprueban a 1280 y 390 px, en claro y en oscuro.
tags: [tareas, simplificacion, frontend, flujos, costes, arquitectura]
status: active
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-21 }
verified: { by: human, at: 2026-11-21 }
stale_after: null
---

# simplificacion — Tareas

El estado de cada bloque está en [specs/index.md](../index.md); aquí solo van las casillas.

## Forma de trabajo
- **Modelo:** aclaraciones, spec, plan y tareas, con Opus; la construcción, con Sonnet. Un fallo de eval poco
  claro se analiza con Opus.
- **Ramas:** una por bloque (`simplificacion-s1` … `simplificacion-s10`); S2-S5 se fusionaron en un solo PR.
  Dentro de un bloque, todas las tareas seguidas.
- **Números:** en S8 no siguen el orden porque las tareas se añadieron durante la prueba; no se renumeran para no
  romper las referencias de los commits.
- **Gasto:** solo T09 (eval `cv`), T19 (evals `ofertas` y `red-teaming`) y las pruebas manuales llaman al modelo
  real: se avisa antes con la estimación.
- **Tests:** `UV_NO_SYNC=1 uv run pytest`.

### S0 · Spec
- [x] T01 — Aclaraciones y spec 010 aprobadas. *(firmadas por Mar el 21-nov)*
- [x] T02 — Plan y tareas aprobados. *(firmados por Mar el 21-nov)*
  - **Test:** Mar los lee y los firma (`verified`).

### S1 · Palabras y menú (RF-10.1, 10.2, 10.6, 10.7)
- [x] T03 — `textos.js` y test de palabras prohibidas.
  - **Test:** el test estático falla hoy («nota», «CV base», «Apify», «Mar»…) y pasa al final del bloque;
    `estadoVisible` da los seis estados de RF-10.7.
- [x] T04 — Menú de tres pestañas y Admin con `comun.js`.
  - **Test:** tres pestañas (más Admin solo para administradoras); `ingesta.js` y `costes.js` sin copias de
    utilidades.
- [x] T05 — Landing con Google directo y redirecciones.
  - **Test:** `/entrar`, `/recomendadas`, `/anadir-oferta` → 308; `/` con sesión → `/ofertas` (o `/perfil`
    sin perfil); «Cómo empezar» en tres pasos y sin «CV base».
- [x] T06 — Ofertas: renombrado, ventana «Añadir oferta» y aviso sin perfil.
  - **Test:** `/ofertas#anadir` abre la ventana; una oferta pegada aparece con «Añadida por ti»; sin perfil se
    ve el texto de RF-10.6c.
  - **Navegador:** Ofertas y la ventana a 1280 y 390 px, en claro y en oscuro.
- [x] T07 — Textos de la usuaria: compatibilidad, estado único, sin textos internos.
  - **Test:** el test de T03 en verde; Candidaturas y el detalle enseñan el estado visible.
  - **Navegador:** Candidaturas y Candidatura a 1280 y 390 px, en claro y en oscuro.
- [x] T08 — Cierre de S1: prueba manual de Mar y PR. *(firmada por Mar el 21-nov)*

### S2 · Candidatura sin CV base (RF-10.3)
- [x] T09 — Flujo y redactor sin CV base; eval `cv`. *(eval real en umbral el 21-nov: 31 casos; cobertura ATS 0,81)*
  - **Qué se hace:** `elegir` sin CV base; fuentes solo el maestro; `redactor_cv` con `longitud` y condensación;
    el worker pasa `longitud_cv`; casos nuevos en `evals/cv`; avisar del gasto antes (~0,5-1 USD).
  - **Test (simulado):** el flujo redacta con solo el maestro; `comprobar` acepta frases del maestro y rechaza
    una inventada. **Real:** eval `cv` en umbral.
- [x] T10 — Servicio y candidaturas antiguas.
  - **Test:** `crear` sin CV base no da 409; una candidatura con `cv_base_id` recalcula avisos con él.
- [x] T11 — Quitar `/cv-base` (si T09 pasa) o dejar el respaldo (si no).
  - **Test:** `/cv-base` → 308 a `/perfil`; los endpoints de CV base dan 404; las tablas siguen.
- [x] T12 — Cierre de S2: prueba manual de Mar (usuaria nueva: sube CV y prepara candidatura) y PR. *(PR #29; prueba hecha por Mar el 21-nov)*

### S3 · Avance y subida (RF-10.8, RF-10.5 subida)
- [x] T13 — Indicador de avance en la guía y en la cabecera. *(retirado en S7, T32: el avance va en su pantalla)*
  - **Test:** `/api/tareas/activas` sin `tipo` da las tareas de la usuaria con su URL; otra usuaria no las ve;
    el indicador desaparece al terminar.
  - **Navegador:** cabecera con indicador a 1280 y 390 px, en claro y en oscuro.
- [x] T14 — Subida al elegir el archivo. *(«Carta» no se sube hasta S4)*
  - **Test:** el `change` sube con `clase=fuente`; no hay botón «Subir CV» en el estado vacío.
- [x] T15 — Cierre de S3: prueba manual de Mar y PR. *(PR #29; prueba hecha por Mar el 21-nov)*

### S4 · Perfil en una pantalla (RF-10.4, RF-10.5)
- [x] T16 — `GET /api/perfil/cv.pdf`.
  - **Test:** da `application/pdf` con el nombre y una experiencia del perfil; otra usuaria o sin perfil, 404.
- [x] T17 — Perfil: estado vacío, cinco bloques, «Por resolver», una sola elección de longitud, clases «CV» y
  «Carta». *(Perfil revisado de nuevo en S7, T36)*
  - **Test:** orden de RF-10.5b; cada elemento de «Por resolver» con dos acciones; `estetico` nuevo → 422; un
    estético antiguo se lista.
  - **Navegador:** Perfil vacío y lleno a 1280 y 390 px, en claro y en oscuro.
- [x] T18 — Cierre de S4: prueba manual de Mar y PR. *(PR #29; prueba hecha por Mar el 21-nov)*

### S5 · Ahorro (RF-10.9, RF-10.10, RF-10.11c)
- [x] T19 — `analizador-oferta` y `procesar_oferta` con una llamada; evals. *(21-nov: prompt afinado; evals reales `ofertas` 8 de 8 y `red-teaming` sin fallos nuevos; ajuste en `true`)*
  - **Qué se hace:** agente nuevo (RT-01), flujo con el ajuste `HORMA_OFERTA_UN_AGENTE`; avisar del gasto antes
    (~1-2 USD).
  - **Test (simulado):** una llamada con el ajuste activo, tres sin él. **Real:** `ofertas` y `red-teaming` en
    umbral; si no, el ajuste queda en `false` y se apunta.
- [x] T20 — Presupuesto diario único.
  - **Test:** con 1 USD gastado, ningún tipo se encola (429 `presupuesto`); el tope de cada tarea es el
    restante; una oferta propia queda pendiente y se procesa cuando vuelve a haber presupuesto.
- [x] T21 — Caché de la compatibilidad (migración `0022`) y `clasificar_perfil` solo si hace falta.
  - **Test:** editar el resumen no vuelve a puntuar ni a clasificar; editar una experiencia sí; el relleno da
    huella a las filas de hoy.
- [x] T22 — Precios oficiales del modelo.
  - **Test:** `config.py` sin «ESTIMADOS» y con la fecha de consulta.
- [x] T23 — Cierre de S5: prueba manual de Mar (Admin › Costes: una oferta = una llamada) y PR. *(pasos en el plan de pruebas manual, retirado; navegador de S3-S5 comprobado por Claude el 21-nov)*

### S6 · Orden interno (RF-10.11)
- [x] T24 — Solo los servicios encolan; routers sin repositorios; contrato de import-linter.
  - **Test:** `lint-imports` falla hoy y pasa al final; la suite sigue verde.
- [x] T25 — Tabla `ENCADENADOS` en el worker.
  - **Test:** los encadenados de hoy siguen pasando (perfilar → estilo y puntuar_propias; procesar_oferta →
    puntuar_propias; clasificar_perfil → puntuar_propias).
- [x] T26 — Aparcar `clasificador-respuesta` y `generador-cv-base`; borrar `extraer_oferta`; `langgraph` por
  defecto.
  - **Test:** no se pueden encolar desde la web; la CI no corre sus sets; sin `HORMA_FLOW_IMPL`, `candidatura`
    usa LangGraph.
- [x] T27 — Coherencia: `system.md`, `specs/index.md`, README; en las specs 002, 003, 005, 008 y 009, los
  requisitos de «Requisitos que sustituye» marcados como sustituidos por la 010.
- [x] T28 — Cierre de S6: suite verde y PR. *(PR #30, fusionado el 22-nov)*

### S7 · Correcciones tras la prueba (RF-10.3g, 10.4d, 10.5c, 10.6e, 10.8, 10.13, RF-6.4b)
Rama `simplificacion-s7`, sobre `simplificacion-s6`. Sale de la prueba 2.3 de Mar (21-nov).
- [x] T29 — Spec, plan y tareas de S7. *(Opus; firmadas por Mar el 21-nov)*
- [x] T30 — «Por resolver» con el desplegable «Avisos»: «Corregir»/«Añadir» y «Dar por visto».
  - **Test:** Perfil tiene `details` «Avisos» dentro de «Por resolver»; ningún texto dice «Está bien así».
- [x] T31 — Avisos agrupados en tres grupos, en la candidatura y en Perfil.
  - **Test:** 20 requisitos ausentes dan 1 aviso «No consta»; 4 experiencias sin cifras, 1 aviso con 4; «Dar por
    visto» del grupo marca las 4; una candidatura antigua sin `tipo` se ve en «Revisa»; sin avisos, no hay panel.
  - **Navegador:** Candidatura y Perfil a 1280 y 390 px, en claro y en oscuro.
- [x] T32 — Una sola barra: fuera el indicador de la cabecera; barra con % en Perfil al leer el CV.
  - **Test:** ninguna página pinta `.indicador-avance`; Perfil usa `barraAvance` con `tipo=perfilar`.
- [x] T33 — Términos excluidos al final de «Qué buscas».
  - **Test:** en `ofertas.html`, `grupo-excluidos` va después de «Condiciones» y antes de «Guardar y buscar».
- [x] T34 — Diseño sobrio del PDF (CV y carta) y la carta como párrafos en «Ver».
  - **Test:** el PDF se abre; su texto extraído trae nombre, secciones y fechas en orden; la carta sin
    negritas; los PDF guardados de candidaturas antiguas se siguen sirviendo. Mar ve una muestra.
- [x] T35 — Carta que suena humana. *Gasta: avisar antes (~0,7-1,2 USD).*
  - **Qué se hace:** diagnóstico de la carta de la 2.3 (sin gasto); prompt reescrito con ejemplo; casos de carta
    en `evals/cv`.
  - **Test (simulado):** el prompt trae la estructura de RF-10.3g y el ejemplo cumple `verificar_trazabilidad`.
    **Real:** eval `cv` en umbral y una candidatura que Mar lee.
- [x] T36 — Repaso de simetría de todas las pantallas de la usuaria (lista del plan, S7).
  - **Navegador:** Perfil (vacío, leyendo, lleno), Ofertas, Candidaturas y Candidatura a 1280 y 390 px, en claro
    y en oscuro, mirando a propósito alineación y alturas.
  - **Hecho (22-nov), a 1280 px y en oscuro:** Ofertas (fila Puestos · Sector · Condiciones, casillas cuadradas), Perfil
    (columna derecha: Subir archivo, Tu CV completo, Por resolver, Documentos subidos, Cómo escribes), Candidaturas
    (seis columnas en una fila) y Candidatura. **390 px:** no se pudo comprobar (la ventana de Chrome no baja de ancho); queda para el repaso página por página de Mar.
  - **Cambios pedidos por Mar en el repaso:** se retira «Área» de Ofertas (se vacía al guardar y el CV ya no la
    rellena); «Subir archivo» con formatos y peso; barras en verde lima; «Nombre» editable en Perfil (sale en «Tu CV
    completo» y su PDF; el extractor lo pide); PDF de candidatura como `cv-puesto-empresa.pdf` y
    `carta-puesto-empresa.pdf`; «No consta en tu CV» en una línea corta con la lista completa desplegable.
- [x] T37 — Cierre de S7: plan de pruebas, coherencia (spec, `index.md`, README) y prueba de Mar. *(cerrada por
  Mar el 22-nov; PR #31, fusionado el 22-nov)*
  - **T35 en real:** eval `cv`, 31 casos (1,60 USD, parado por tope) y los casos 32 y 33 de carta en verde (0,25 USD).

### S8 · Correcciones de la pasada del 22-nov (RF-10.14 a 10.14r, RF-5.3i, 10.4e, 10.6i, 10.8c, 10.16, 10.17)
Rama `simplificacion-s8`. Sale de la pasada completa de Mar (22-nov, apuntes C1-G1) y de su repetición (H-P).
Construye Sonnet, todo el bloque seguido; se para solo antes de gastar (T50).
- [x] T38 — Spec, plan y tareas de S8. *(Opus; firmadas por Mar el 22-nov)*
- [x] T39 — Puestos con género (RF-10.14p).
  - **Test:** «Jefe de sala» casa con «Jefe/a de sala», «Jefa de sala» y «Jefe(a) de sala», y no con «Jefe de
    cocina»; «Auxiliar administrativo/a» casa con «Auxiliar administrativa»; `contar_por_puesto` cuenta igual;
    la migración recalcula `titulo_norm`.
- [x] T40 — Lista vacía con motivo (RF-10.14q) e ingesta atascada (RF-10.14r).
  - **Test:** con puestos marcados y ninguna oferta, Ofertas enseña el texto de RF-10.14q; una ejecución «en
    curso» de hace 31 min se cierra como error al reclamar otra; una de hace 5 min, no.
- [x] T41 — `perfilar` conserva lo que escribió la usuaria (riesgo del plan, base de T42).
  - **Test:** un perfil con una experiencia y una habilidad de origen `usuaria`, al subir otro CV, las mantiene
    en la versión nueva.
- [x] T42 — Borrar un CV rehace el perfil (RF-10.14).
  - **Test:** con dos CV, borrar uno encola `perfilar` solo con el otro y la versión nueva no tiene datos con su
    `cv_id`; borrar el último deja Perfil en «Sube tu CV» y las candidaturas siguen abriéndose; sin presupuesto,
    el CV se borra y el perfil se rehace al día siguiente; la confirmación trae el texto nuevo.
- [x] T43 — Detectar CV o carta (RF-10.14b).
  - **Test:** los dos CV y la carta de `pruebas-manuales/pasada-22nov/` se clasifican bien (sin modelo); un texto
    ambiguo da «duda»; cambiar la clase de carta a CV encola `perfilar`. Sin selector de clase en «Subir archivo».
- [x] T44 — Un resumen y un titular por CV (RF-10.14d). *Gasta si cambia el prompt: avisar antes (eval `cv`).*
  - **Test (simulado):** con dos CV, el perfil guarda los dos resúmenes con su origen; «Sin resumen» solo sale si
    ninguno tiene; «Tu CV completo» usa el del CV más reciente; el redactor recibe los dos. **Real:** eval `cv` en
    umbral, si se tocó el prompt.
- [x] T45 — Ver DOCX y respuesta con lo que cambió (RF-10.14c, 10.14e).
  - **Test:** «Ver» de un DOCX devuelve su texto y el aviso; «Descargar original», el archivo con su tipo; otra
    usuaria, 404. Guardar una respuesta devuelve el campo y el valor nuevos.
- [x] T46 — Perfil: sin versión, Formación con cursos, nombre, hueco y fechas (RF-10.14f-j).
  - **Test:** ninguna página pinta «versión»; Formación tiene «Cursos y certificados»; el hueco pregunta
    «¿Fue un empleo u otra cosa?»; las fechas se ven y se escriben como MM-AAAA y se guardan como hoy.
- [x] T47 — «Corregir» por experiencia en «Sin cifras», con ejemplos (RF-10.14k).
  - **Test:** un aviso con tres experiencias trae tres «Corregir»; cada uno abre la caja «Modificar» de la suya.
- [x] T48 — Cómo escribes y ayudas «?» (RF-10.14l, 10.14m).
  - **Test:** «Usas» y «Evitas» en `<ul>`; «Evitas» vacío con su texto; etiqueta según el origen; el componente
    «Explicación plegable» en la guía y en las cuatro pantallas; textos de C2 y C8 en `textos.js`.
- [x] T49 — Un solo mensaje a la vez y PDF sin páginas sueltas (RF-10.14n, 10.14o).
  - **Test:** al subir un CV, Perfil no pinta a la vez la barra y «CV subido…»; el PDF del CV completo de la pasada
    no tiene ninguna página con menos de tres líneas.
  - **Navegador (T46-T49):** Perfil, Ofertas, Candidaturas y Candidatura a 1280 px, en claro y en oscuro; 390 px si
    la herramienta lo permite (si no, se dice).

#### Correcciones de la prueba H-I (22-nov)
- [x] T54 — Barras que se rellenan en lima y conservan su punto al repintar (RF-10.8c).
- [x] T55 — Filtro por vocabulario de empleo: la receta se rechaza sin analizarla (RF-5.3i).
  - **Test:** `test_texto_largo_sin_vocabulario_de_empleo_se_rechaza`; las 177 ofertas guardadas y los casos de evals pasan.
- [x] T56 — `/ofertas#anadir` abre la ventana también desde Ofertas (RF-10.6i). **Navegador:** comprobado.
- [x] T57 — «Información adicional» y avisos de formato en llano (RF-10.16); migraciones 0026 (recompone maestros) y
  0028 (reescribe avisos guardados).
- [x] T58 — PDF `cv_nombre_puesto_empresa.pdf` (RF-10.4e).
- [x] T59 — «Estado» y «Me han contratado» con su Ventana (RF-10.17); migración 0027.
  - Pendiente: comprobación visual a 1280 y 390 px, claro y oscuro, en la prueba de cierre (T50).

#### Correcciones de la pasada J-P (22-nov)
Recorrida por Claude en el navegador y la consola; K1, O4, P1, P2, P5 y N4 repetidas después y correctas.
- [x] T60 — «No consta en tu CV» solo con lo que falta (RF-10.13). La causa era `medir_ats`, no el redactor: exigía
  todas las palabras de una frase de requisito. Ahora una palabra clave corta exige todas (nivel de idioma igual o
  mayor; las cifras y «o superior/similar» no cuentan; «A o B» y «A; se valorará B» se respaldan con uno de los dos; «formación» no cuenta como palabra pedida) y una frase de 4 o más palabras la juzga el redactor.
  - **Test:** `test_s8_t60_huecos_falsos.py` (los 4 requisitos de Irene ya no son hueco; «Excel avanzado» e «Inglés C1» sí).
- [x] T61 — El nombre que editó ella manda sobre el del CV al rehacer el perfil (RF-10.5f, RF-10.14).
  - **Test:** `test_s8_t41_conserva_lo_de_la_usuaria.py`.
- [x] T62 — Eliminar una carta o el último CV lo dice en su idioma (RF-10.14): diálogo, etiqueta y aviso.
  - **Test:** `test_s8_t42_borrar_cv_rehace_perfil.py`. **Navegador:** en la prueba de cierre (T50).

#### Correcciones finales (cruce del 22-nov con los informes de investigación)
Lo demás de la pasada no se arregla aquí: los falsos «Dato dudoso», los recortes del extractor y «manejo de
ordenador» como hueco van a la fase 13; el coste de editar el perfil, a la 12; «sin límite» en Admin, a la 14; los
avisos de presupuesto, a la gestión del gasto. Ver [index.md](../index.md#lo-que-viene).
- [x] T63 — «Valenciano» en el CV maestro y en las ofertas.
  - **Qué se hace:** `componer_cv_maestro` escribe «Valenciano» si el idioma es `ca` y su `origen.fragmento` dice
    «valenci»; si no, «Catalán». `normalizar_oferta` añade «valenciano valencià» a `ca`.
  - **Test:** `ca` con fragmento «Valenciano: C1» da «Valenciano C1» en el maestro; con «Catalán: B2», «Catalán
    B2»; una oferta que pide valenciano no sale en «No consta» si el perfil tiene `ca`.
- [x] T64 — «No consta» sin duplicados ni texto interno (RF-10.13).
  - **Qué se hace:** en `flows/candidatura.py`, los huecos del redactor y los de `medir_ats` se comparan por una
    clave normalizada (sin paréntesis, sin tildes, en minúsculas) y por inclusión; de los huecos del redactor se
    quita el paréntesis con texto interno (p. ej., «según la taxonomía»).
  - **Test:** «PMS (…según la taxonomía…)» y «pms» dan un solo «PMS»; ningún hueco contiene «taxonomía».
- [x] T65 — Barra y Perfil sin parpadeo (RF-10.8c, RF-10.14n).
  - **Qué se hace:** `perfil.js` conserva el nodo de la barra al repintar mientras la tarea siga activa (como T54)
    y no pinta «Sube tu CV» hasta tener la respuesta de `/api/perfil`.
  - **Test:** estático: la barra se crea una vez y se reutiliza; el estado vacío solo se pinta tras la respuesta.
    **Navegador:** subir un CV y ver la barra continua hasta «Listo», a 1280 y 390 px, en claro y en oscuro.
- [x] T66 — Saludos de la carta con la puntuación correcta (RF-3.6, lista cerrada).
  - **Qué se hace:** la lista de `verificar_trazabilidad.py`, el prompt de `redactor_carta` (lista y ejemplo) y los
    casos de `evals/cv` usan coma tras «Hola» y dos puntos al final: «Hola, equipo:», «Estimado equipo de
    selección:», «Estimados señores:», «Buenos días:». La comprobación sigue aceptando las formas antiguas, para no
    avisar en cartas ya guardadas. Despedidas, sin cambios. El nombre de la empresa en el saludo, en la fase 13.
  - **Test:** el prompt y sus ejemplos solo traen formas nuevas; una carta con «Hola, equipo:» pasa la comprobación.
    **Real:** el eval `cv` de T50.
- [x] T67 — El eval simulado informa 0 USD.
  - **Test:** `horma eval correr ofertas --simulado` da coste 0.
- [x] T50 — Cierre de S8 (22-nov: Q1-Q10 pasan por DOM/API; falta solo lo visual a 1280/390 px y claro/oscuro, y el PR). *Gasta: avisar antes.*
  - **Qué se hace:** eval `cv` real (hecho el 22-nov: 33/33, 1,74 USD, aprobado; cierra T44 y T66); prueba de cierre de Mar en
    `docs/plan-pruebas-manuales.md` (subir y borrar CV, T59, T62-T66; ~0,3-0,6 USD); presupuesto diario de vuelta
    a 1 USD; suite verde; `index.md` al día; PR.

### S9 · «Corregir explicación» amplía la información (RF-10.15) — firmada el 22-nov
Rama `simplificacion-s9`, desde `simplificacion-s8` (S8 aún sin fusionar). Tests en
`tests/test_s9_t51_t53_informacion_nueva.py`. **T68 (23-nov):** migración `0029` aplicada, suite verde con base de datos (1565 pasan, 7 saltados) y R1-R9 pasan por
DOM/API (R6 costó 0,231 USD). Falta lo visual de R3-R5 y R10 (Mar), su firma y el PR.
- [x] T51 — Campo «Información nueva sobre ti» y ayuda (RF-10.15, 10.15e).
  - **Test:** `POST /api/matches/{id}/correccion` guarda `informacion`; sin ella sigue valiendo; otra usuaria, 404.
- [x] T52 — La información llega a las candidaturas nuevas como una fuente más, sin tocar los prompts (RF-10.15b).
  - **Test (simulado):** el redactor, el juez y la trazabilidad la reciben en una candidatura nueva y no en una ya
    preparada; una frase con un dato que no está ni en el perfil ni en la información da error de trazabilidad.
- [x] T53 — Preguntar y revisar en Perfil (RF-10.15c-d).
  - **Test:** «No» no toca `por_resolver`; «Sí» añade la propuesta; el perfil no cambia de versión hasta
    confirmarla; confirmar aplica «desfasadas». **Navegador:** Ofertas y Perfil a 1280 y 390 px, claro y oscuro.
- [ ] T68 — Cierre de S9: hecho lo automático (arriba); falta lo visual de Mar (R3-R5, R10), `index.md` y PR.

### S10 · Subir varios documentos a la vez (RF-10.18) — sin spec
Rama `simplificacion-s10`. Con S10 se cierra la fase 10.
- [ ] T69 — Aclaraciones, spec, plan y tareas de S10. *(Opus; firma de Mar)*
