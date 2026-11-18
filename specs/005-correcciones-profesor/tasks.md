---
type: tasks
title: correcciones-profesor — Desglose de tareas
description: Tareas pequeñas y comprobables derivadas del plan de la fase 5. Cada una empieza con un test que falla.
tags: [tareas, perfil, cv-maestro, ofertas, scrapeo, validacion-cv, fuentes, estilo]
status: active
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-17 }
verified: { by: human, at: 2026-11-17 }
stale_after: null
---

# correcciones-profesor — Tareas

## Orden y forma de trabajo
Se construye por bloques y se para entre uno y otro:

0. aparcar `evals-reales` (T00, antes que nada)
1. perfil y CV maestro (A, T01-T05)
2. CV base y candidaturas desfasadas (B, T06-T09)
3. ofertas propias y Recomendadas (C, T10-T15)
4. ingesta por URL con Apify (D, T16-T19)
5. validar CV y «que no suene a IA» (E, T20-T23)
6. guía de estilo (F, T24-T28)
7. fuentes nuevas (G, T29-T32)
8. cierre (H, T33-T35)

Cada tarea empieza con un test que falla. Todo se prueba sin llamar al modelo (puerta simulada) ni a
Apify (lector simulado), salvo las mediciones reales de T19, T23, T28 y T35, que necesitan el OK de
Mar antes de gastar. Cada bloque va en su rama y con un PR; desde T00, un PR ya no gasta en el modelo
real (RF-5.8).

### T00 · Aparcar `evals-reales` (RF-5.8)
- [x] T00 — Solo a mano hasta el lanzamiento. *(fusionada con el PR #10 el 17-nov; `main` exige solo `secretos` y `calidad`)*
  - **Qué se hace:** en `ci.yml`, `evals-reales` solo con `workflow_dispatch`; Mar quita
    `evals-reales` de los checks obligatorios de `main`; nota en `docs/mejoras-futuras.md` para
    reactivarlo antes de lanzar. Nota en RF-4.4c de la spec de la fase 4.
  - **Test:** un PR de prueba corre `secretos` y `calidad`, no `evals-reales`, y se puede fusionar con
    `calidad` en verde.
  - **Cubre:** RF-5.8.

### Bloque A · Perfil y CV maestro (RF-5.1-5.1d)
- [x] T01 — `componer_cv_maestro`. *(hecha el 17-nov)*
  - **Qué se hace:** tool de código puro que convierte un `Perfil` en el Markdown del maestro, con
    los encabezados fijos del plan.
  - **Test:** el mismo perfil da el mismo texto; cada dato del perfil aparece en su sección; un dato
    quitado no aparece; sin rasgos personales.
  - **Cubre:** RF-5.1.
- [x] T02 — Secciones nuevas del perfil. *(hecha el 17-nov; `corregir` sin índice añade un dato a la lista)*
  - **Qué se hace:** `Proyecto`, `Certificacion` y `OtroDato` en `schemas/perfil.py`; `LISTAS` del
    servicio; `componer_cv_maestro` las incluye.
  - **Test:** se pueden añadir, corregir y quitar por la API con origen «usuaria»; un campo prohibido
    (edad) sigue fallando.
  - **Cubre:** RF-5.1c.
- [x] T03 — El maestro manda tras editar. *(hecha el 17-nov; migración 0010, que T11 ya no puede usar: la de ofertas será la 0011)*
  - **Qué se hace:** `_nueva_version` guarda `componer_cv_maestro(perfil)`; `perfilar` también lo usa;
    el extractor deja de escribir `cv_maestro` (prompt y esquema). Migración 0010 (solo la parte de
    recomponer los maestros existentes).
  - **Test:** editar una experiencia cambia el maestro de la versión nueva; con respuestas simuladas,
    un CV adaptado que usa el dato editado no da errores de trazabilidad; lo borrado no aparece.
  - **Cubre:** RF-5.1, RF-5.1b.
- [x] T04 — Extractor con secciones nuevas y su eval. *(hecha el 17-nov; casos 13 y 14; el eval de perfil pasa a 14 casos)*
  - **Qué se hace:** prompt del `extractor_perfil` (proyectos, certificaciones, otros, cada uno con su
    cita); casos nuevos en `evals/perfil/`.
  - **Test:** `horma eval correr perfil --simulado` en umbral con los casos nuevos.
  - **Cubre:** RF-5.1c.
- [ ] T05 — Pantalla del perfil. *(código hecho el 17-nov; falta que Mar lo compruebe en la web)*
  - **Qué se hace:** las tres secciones en `perfil.html/js` con su texto de ayuda y los ejemplos de la
    spec; el aviso «Lo que edites aquí manda sobre tus CV subidos…».
  - **Test:** Mar lo comprueba en la web (paso del plan de pruebas): ve las secciones, la ayuda y el
    aviso, y edita un proyecto.
  - **Cubre:** RF-5.1c, RF-5.1d.

### Bloque B · CV base y candidaturas desfasadas (RF-5.1e-5.1g)
- [x] T06 — Desfasado por traza. *(hecha el 17-nov; la lista de CV base devuelve `cambios` y `desfasado`)*
  - **Qué se hace:** `cv_base_afectado(traza, maestro_nuevo)`; `listar_cv_base` lo usa y devuelve qué
    líneas cambiaron.
  - **Test:** editar una experiencia de hostelería marca el CV base que la cita y no el de construcción
    que no la usa.
  - **Cubre:** RF-5.1e.
- [x] T07 — Regenerar un CV base. *(hecha el 17-nov; tarea nueva `regenerar_cv_base` (id del CV base); migración 0011, así que la de ofertas de T11 será la 0013)*
  - **Qué se hace:** `POST /api/cv-base/{id}/regenerar`; `generar_cv_base` acepta `destinos` y
    `cv_base_id`; se guarda con `origen="regeneracion"` (migración: valor nuevo); botón en
    `cv-base.html/js`.
  - **Test:** regenerar sustituye el contenido y deja la versión anterior en el historial; nada se
    regenera sin pulsar el botón.
  - **Cubre:** RF-5.1e.
- [x] T08 — Visibilidad de experiencias en el CV base. *(hecha el 17-nov; migración 0012; el selector lleva una cuarta opción, «Automática», para lo no marcado; evals 06 y 07)*
  - **Qué se hace:** `cv_base.visibilidad` (migración), regla en el prompt del generador, comprobación
    con código y selector «completa / condensada / oculta» por experiencia en la web. Por defecto, la
    de otro sector, condensada.
  - **Test:** una «oculta» no aparece; una «condensada» ocupa una línea; al regenerar se respeta lo
    marcado; casos nuevos en `evals/cv-base/` en simulado.
  - **Cubre:** RF-5.1g.
- [x] T09 — Borradores con una versión anterior del perfil. *(hecha el 17-nov; falta que Mar lo compruebe en la web)*
  - **Qué se hace:** `desfasada` en el detalle de la candidatura; `reintentar` admite un borrador
    desfasado; aviso y botón «Volver a preparar» en `candidatura.html/js`.
  - **Test:** tras editar el perfil, el borrador muestra el aviso; rehacer lo prepara con la versión
    vigente; se puede aprobar sin rehacer.
  - **Cubre:** RF-5.1f.

### Bloque C · Ofertas propias y Recomendadas (RF-5.2, RF-5.3-5.3e)
- [x] T10 — Reproducir el limbo. *(hecha el 17-nov; `test_f5_t10_limbo.py`, 3 casos que fallan: sin nota, repetida y sin fecha; pasan con T13)*
  - **Qué se hace:** test de extremo a extremo que pega una oferta y espera verla puntuada en
    Recomendadas; un segundo caso pega una oferta repetida. Se anota en el test qué causa falla.
  - **Test:** hoy falla (es el test de la tarea).
  - **Cubre:** RF-5.3.
- [x] T11 — Dueña y privacidad. *(hecha el 17-nov; migración 0013, también deja al sistema encolar y leer tareas de una usuaria; `/api/catalogo` y los errores de ingesta ya no incluyen las propias)*
  - **Qué se hace:** migración 0013: `ofertas.usuaria_id` y la política de lectura nueva; `recibir`
    con `usuaria_id` desde la web; `repetida` solo dentro de la misma dueña.
  - **Test (RLS):** una oferta de Ana no la ve Berta ni en `/ofertas` ni en Recomendadas ni por id;
    las del catálogo las ven las dos; pegar dos veces la misma no la deja fantasma.
  - **Cubre:** RF-5.3c.
- [x] T12 — Puntuar al momento. *(hecha el 17-nov; entidad de la tarea = id de la usuaria, porque el worker en modo sistema no ve su perfil; tope `TOPE_COSTE_PUNTUAR_PROPIAS`, 1,00 USD)*
  - **Qué se hace:** tarea `puntuar_propias` (todas las propias sin nota para la versión vigente, por
    tandas de 30), encolada al terminar `procesar_oferta` de una oferta con dueña y al cambiar el
    perfil de versión; tope de coste propio.
  - **Test:** con respuestas simuladas, la oferta pegada queda puntuada sin pulsar «Recomendar»; una
    añadida sin perfil se puntúa sola al construirse el perfil; tras editar el perfil, las propias se
    re-puntúan con la versión nueva.
  - **Cubre:** RF-5.3d.
- [x] T13 — Recomendadas: TODAS las propias, con marca. *(hecha el 17-nov; T10 pasa)*
  - **Qué se hace:** `buscar_ofertas` deja pasar todas las propias procesadas (sin filtros, rango,
    repetición, fantasma ni fraude); `listado` devuelve `propia`, `analizada_en` y el motivo del
    auditor; marca «Añadida por ti · analizada el <fecha>» y aviso del auditor en `recomendadas.js`; se
    quita la columna «Condiciones» y su ayuda.
  - **Test:** una propia que no pasa los filtros, una repetida y una marcada como fraude salen las
    tres con su evaluación y su marca (la de fraude, con su aviso) y permiten preparar la candidatura;
    la columna ya no está. T10 pasa.
  - **Cubre:** RF-5.2, RF-5.3e.
- [x] T14 — Pestaña «Añadir oferta». *(hecha el 17-nov solo con texto; el campo de URL llega con T18; falta que Mar la compruebe en la web)*
  - **Qué se hace:** `anadir-oferta.html/js` (texto o URL, estado de lo último añadido) y enlace en la
    navegación; se quita el formulario de `index.html`.
  - **Test:** Mar pega una oferta desde la pestaña y la ve puntuada en Recomendadas.
  - **Cubre:** RF-5.3b.
- [x] T15 — Marca «Añadida por ti» también en Ofertas. *(hecha el 17-nov)*
  - **Qué se hace:** `/ofertas` devuelve `propia`; la lista la muestra.
  - **Test:** la oferta propia sale marcada en Ofertas solo para su dueña.
  - **Cubre:** RF-5.3c, RF-5.3e.

### Bloque D · Ingesta por URL con Apify (RF-5.3f-5.3j)
- [x] T16 — Confirmar el RGPD de Apify (bloquea T18). *(hecha el 18-nov; Mar aceptó el riesgo y decidió no pedir la lista de subencargados; prueba real OK: `query` = URL, devuelve `markdown`)*
  - **Qué se hace:** leer en fuente oficial dónde guarda los datos, cuánto tiempo, sus subencargados
    y si su DPA cubre este uso; probar una vez el actor `rag-web-browser` con una URL de prueba (con OK
    de Mar). Anotarlo en `docs/revision-lineas-rojas.md` («Encargados del tratamiento»).
  - **Test:** Mar lee la nota y decide: Apify o ScrapingBee.
  - **Cubre:** RF-5.3i.
- [x] T17 — `validar_url` y portales vetados. *(hecha el 18-nov; `horma/tools/validar_url.py` devuelve `None` o el motivo en llano; lista en `horma/assets/portales_vetados.json`; 35 tests en `test_f5_t17_validar_url.py`)*
  - **Qué se hace:** tool de código y `assets/portales_vetados.json` (LinkedIn, Indeed, Glassdoor,
    InfoJobs, con subdominios).
  - **Test:** se rechazan `http`, IP literal, `localhost`, un dominio que resuelve a IP privada, URL con
    credenciales y `es.linkedin.com`; pasa una URL pública de Greenhouse. Mensajes en llano.
  - **Cubre:** RF-5.3g, RF-5.3h.
- [x] T18 — `leer_pagina` y tarea `leer_url`. *(hecha el 18-nov; migración 0014 `importaciones`; `POST /ofertas/url` (202) y `GET /ofertas/url/{id}`; límite `LIMITE_URL_HORA` por hora; sin reintentos porque cada lectura cuesta; campo de URL en «Añadir oferta»; falta que Mar lo compruebe en la web, con la prueba real de T19)*
  - **Qué se hace:** cliente del proveedor elegido en T16 (token en cabecera, sin proxies, tiempo y
    tamaño máximos); tabla `importaciones`; `POST /api/ofertas/url` con límite de ritmo; manejador del
    worker que pasa el texto a `recibir`. `.env.example` con las claves nuevas.
  - **Test:** con un lector simulado, una URL acaba en oferta propia puntuada; un fallo deja la
    importación en `error` con el motivo fijo y la web pide pegar el texto; pasarse del límite da 429;
    el token no sale en ningún log.
  - **Cubre:** RF-5.3f, RF-5.3j.
- [ ] T19 — Prueba real de URL (con OK de Mar). *(lecturas hechas el 18-nov con OK de Mar, sin pasar por el perfil ni el modelo; falta decidir si se hace la parte de Recomendadas. Vetada: LinkedIn rechazada sin leer. Resultado de 5 URL: web de empresa (Metricool) 2.273 car., oferta completa; Greenhouse 1.075 car. pero era el listado de la empresa, no la oferta; Lever 256 car., página 404 (oferta cerrada) que se aceptó como texto; portal pequeño (Asaja) tiempo agotado a los 60 s; jobboardly 325 car., solo la cabecera de la página. Hallazgo, ya corregido el 18-nov: `leer_pagina` daba por buena una página de error corta; ahora exige 400 caracteres y rechaza las de menos de 1.500 con frases de error (404, not found, captcha…). Repetición con 3 ofertas vivas de Mar (18-nov): Greenhouse 11.849 car. (9,6 s), Lever 7.196 car. (30,5 s) y web de empresa (Spotify) 9.211 car. (21 s), las tres con el texto completo del puesto. En esta máquina hace falta el almacén de certificados de Windows para `httpx`)*
  - **Qué se hace:** 5 URL reales de ofertas (Greenhouse, Lever, web de empresa, portal pequeño, una
    con JavaScript) y una vetada; se anota cuáles se leen.
  - **Test:** las legales llegan a Recomendadas; la vetada pide pegar el texto.
  - **Cubre:** RF-5.3f, RF-5.3g.

### Bloque E · Validar CV y «que no suene a IA» (RF-5.4, RF-5.7)
- [x] T20 — `validar_cv` y `muletillas_ia`. *(hecha el 18-nov; `assets/muletillas_ia.json` con 29 expresiones; el «…» admite palabras en medio; `errores_muletillas` da el error con su línea)*
  - **Qué se hace:** las dos tools y `assets/muletillas_ia.json` (lista corta inicial).
  - **Test:** un CV de 1.200 palabras, uno de 150, uno sin Experiencia ni Formación y uno con fin
    anterior al inicio dan su error; «Apasionada por» y «en el dinámico mundo de» se detectan con y
    sin acentos; un CV normal no da nada.
  - **Cubre:** RF-5.4, RF-5.7.
- [x] T21 — En el flujo `candidatura`. *(hecha el 18-nov; los errores de `validar_cv` entran en `errores_formato` («Estructura del CV: …») y las muletillas en `errores_cv` y `errores_carta`; `aviso_de_error` los traduce a llano; llamadas siguen entre 3 y 5, suites `plain` y `langgraph` en verde)*
  - **Qué se hace:** `comprobar` suma las dos tools; los errores entran en la vuelta única y lo que
    queda sale como aviso.
  - **Test:** con respuestas simuladas, un CV largo con una muletilla se rehace una vez y, si sigue,
    sale el aviso; el número de llamadas sigue entre 3 y 5; suites de `plain` y `langgraph` en verde.
  - **Cubre:** RF-5.4c, RF-5.7c.
- [x] T22 — Juez ampliado y CV base. *(hecha el 18-nov; `incoherente` y `suena_a_ia`; `carta`, `cv_base` y `oferta` opcionales; `sin_carta()` fuerza «aprobado» en la carta; el juez del CV base solo corre si el código no halló errores. **Queda para T25-T27:** `guia_estilo` en la entrada del juez, porque `GuiaEstilo` aún no existe)*
  - **Qué se hace:** `TipoProblema` + `incoherente` y `suena_a_ia`; carta y oferta opcionales; prompt
    del juez; `generar_cv_base.verificar` llama a las tools y al juez.
  - **Test:** sin carta, `veredicto_carta` es «aprobado»; un CV base con fechas solapadas vuelve al
    segundo intento con el problema; RF-5.7d: ninguna llamada sale a un detector externo (test de
    arquitectura).
  - **Cubre:** RF-5.4b, RF-5.4d, RF-5.7b, RF-5.7d.
- [x] T23 — Evals del juez y del CV base. *(simulado hecho el 18-nov: `evals/cv/` 21 casos (modo `formato`, solo código) y `evals/cv-base/` 9 (`rechazados` en el esperado, `juez_simulado` en la entrada). **Modelo real (OK de Mar, 18-nov, ≈2,3 USD en total, por encima de lo previsto):** `cv` APROBADO 21/21; `cv-base`  `09-cv-largo`, `10-fechas-incoherentes` y `12-resumen-no-casa` se quitaron de `cv-base` por decisión de Mar (A, 18-nov): con el modelo real el CV base sale bien (condensa el largo; probable que corrija las fechas y que el juez no señale el resumen), así que esos casos solo valen en `cv` (simulado) y en los tests de código. Con los 9 casos que quedan, `cv-base` pasa 9 de 9. CV de prueba alargados a 250-330 palabras; mínimo de 250 se mantiene por decisión de Mar)*
  - **Qué se hace:** casos nuevos en `evals/cv/` y `evals/cv-base/` (largo, corto, fechas
    incoherentes, resumen que no casa, muletillas).
  - **Test:** en simulado, en umbral; con el modelo real (OK de Mar), en umbral.
  - **Cubre:** RF-5.4e, RF-5.7e.

### Bloque F · Guía de estilo (RF-5.6)
- [x] T24 — Subir cartas y «Lo escribí yo». *(hecha el 18-nov; migración 0015 (`clase` `carta`, `escrito_por_ella` y la tabla `estilo`); `PUT /api/cv/{id}/escrito-por-ella`; casilla y clase «Carta» en el perfil)*
  - **Qué se hace:** migración (`clase` `carta`, `escrito_por_ella`); subida y lista en el perfil.
  - **Test:** una carta subida no entra en `perfilar`; la marca se guarda y se puede cambiar.
  - **Cubre:** RF-5.6.
- [x] T25 — Agente `analizador_estilo`. *(hecha el 18-nov; `instrucciones_embebidas` va en la salida del agente, no dentro de `GuiaEstilo`, para que nunca llegue a los redactores; el código de después es `tools/depurar_guia.py`)*
  - **Qué se hace:** `prompt.md`, esquemas (`GuiaEstilo`), `run()`; código tras el agente que quita
    citas sin origen y comprueba rasgos personales; ejecutable con `horma agente correr`.
  - **Test:** con la puerta simulada, una cita inventada se quita; una guía con «es una persona
    tranquila» se rechaza; instrucciones embebidas registradas y sin efecto.
  - **Cubre:** RF-5.6b, RF-5.6c.
- [x] T26 — Una sola vez y botón. *(hecha el 18-nov; se encola al acabar `perfilar` o al subir una carta solo si no hay guía; `GET`/`POST /api/estilo/analizar`/`PUT /api/estilo`; sección «Tu estilo de redacción» en el perfil con el botón. Una guía editada que describe a la persona o trae rasgos personales se rechaza con 422)*
  - **Qué se hace:** tabla `estilo`, flujo y tarea `analizar_estilo`; se encola solo si no hay guía;
    `POST /api/estilo/analizar` y `PUT /api/estilo`; la guía editable en el perfil y el botón «Volver a
    analizar mi estilo» en la configuración.
  - **Test:** subir un segundo CV con guía ya hecha no llama al modelo; el botón sí; lo editado por
    ella se marca `origen=usuaria` y se respeta.
  - **Cubre:** RF-5.6d.
- [x] T27 — Los redactores siguen la guía. *(hecha el 18-nov; `guia_estilo` también entra en el juez de la candidatura (cierra lo que dejó T22); el generador de CV base no la recibe)*
  - **Qué se hace:** `guia_estilo` en las entradas de `redactor_cv`, `redactor_carta` y juez; el worker
    la carga; reglas en los prompts.
  - **Test:** con respuestas simuladas, la guía llega a las tres llamadas; sin guía, todo igual que
    antes; la trazabilidad no cambia.
  - **Cubre:** RF-5.6e.
- [x] T28 — Eval `estilo`. *(simulado hecho el 18-nov: `evals/estilo/` 8 casos (2 adversarias), umbral `estilo` 0,9, y casos 22-23 con guía en `evals/cv/`. **Modelo real (OK de Mar, 18-nov, ≈0,12 USD por pasada): `estilo` APROBADO 8/8, `sin_rasgos` y `sin_efecto` al 100 %.** La primera pasada falló `registro` en el caso 08 (CV solo de viñetas, etiqueta ambigua); se le añadió una carta formal para que el registro fuera inequívoco, sin tocar lo esperado)*
  - **Qué se hace:** `evals/estilo/` (unas 8 usuarias inventadas, 2 adversarias), set en `evals.py` y
    umbral en `umbrales.json`; casos con guía en `evals/cv/`.
  - **Test:** en simulado, en umbral; con el modelo real (OK de Mar), `sin_rasgos` y `sin_efecto` al
    100 %.
  - **Cubre:** RF-5.6f.

### Bloque G · Fuentes nuevas (RF-5.5)
- [x] T29 — Adaptadores de ingesta. *(18-nov: `lista: "$"`, `auth_basica`, `detalle` (con `{id}` y `raiz`; si falla, la oferta sigue sin él), `cada_horas` (lo exige el servicio al pedir o empezar una ejecución; las que acabaron en error no cuentan) y `atribucion`; migración 0016; el editor del dashboard conserva los campos nuevos)*
  - **Qué se hace:** `lista: "$"`, Basic auth desde variables y llamada de `detalle` opcional en
    `normalizar`/`ingesta`; `fuentes.cada_horas` y `fuentes.atribucion` (migración).
  - **Test:** con respuestas grabadas (inventadas), un array en la raíz, una fuente con detalle y una
    con `cada_horas` que no se pide antes de tiempo.
  - **Cubre:** RF-5.5, RF-5.5b, RF-5.5d.
- [~] T30 — Himalayas, Jobicy, Remotive y Adzuna. *(18-nov: las cuatro configuradas e inactivas en `config/endpoints.json` (forma de cada API comprobada con una petición real); la oferta guarda copia de la atribución (`ofertas.atribucion`) y se ve en Recomendadas; `caduca_en` + borrado de caducadas al cerrar cada ejecución (se conservan las que tienen candidatura). Calificación real en local (OK de Mar, 18-nov, céntimos): **Jobicy y Himalayas APTAS; Remotive NO APTA** (condiciones prohíben copiar ofertas y crear bases de datos; queda inactiva, decisión de Mar pendiente de confirmar); **Adzuna: 403 al leer su web**, hay que darle a mano la URL de condiciones (`--condiciones`) o mirar su API. Falta guardar las calificaciones con web y worker arrancados y activar: se hace en la prueba manual)*
  - **Qué se hace:** entradas en `config/endpoints.json`, calificación con `calificar_fuente` y
    activación; atribución visible en la oferta; borrado de caducadas de Himalayas.
  - **Test:** con respuestas grabadas, cada fuente da ofertas normalizadas con enlace y atribución; la
    calificación queda guardada.
  - **Cubre:** RF-5.5, RF-5.5d.
- [x] T31 — InfoJobs, configurada e inactiva. *(18-nov: entrada con Basic auth y detalle, `activa: false`; el correo a InfoJobs lo envía Mar)*
  - **Qué se hace:** entrada con `activa: false` y mapeo con detalle; correo de Mar a InfoJobs pidiendo
    sus condiciones (lo envía ella).
  - **Test:** la ingesta no la llama mientras esté inactiva.
  - **Cubre:** RF-5.5b.
- [ ] T32 — Greenhouse y Lever por empresa. *(**Cambio de alcance, Mar 18-nov:** no una lista corta, sino TODAS las empresas de Greenhouse (Horma es un metabuscador). Investigación a cargo de Claude: Greenhouse no publica un directorio global, cada empresa tiene su «board token»; hay que averiguar cómo descubrirlos (sitemaps, buscadores, listados públicos), comprobar que cada token responde y respetar condiciones y límites. Se hace en la prueba manual; Lever (misma idea) se decide después)*
  - **Qué se hace:** una entrada por empresa de la lista de Mar (pendiente de que la dé).
  - **Test:** con respuestas grabadas, cada empresa da sus ofertas con enlace al original.
  - **Cubre:** RF-5.5c.

### Bloque H · Cierre
- [x] T33 — Coherencia documental. *(18-nov: `specs/index.md`, README y `docs/mejoras-futuras.md` (puntos 7-9) al día; ningún RT cambia; `system.md` sin tocar, con su tabla de fases en la 4: Mar decide si se añade la 5)*
  - **Qué se hace:** `specs/index.md`, `specs/system.md` (si cambia algún RT), README y
    `docs/mejoras-futuras.md` al día.
  - **Test:** Mar lo revisa.
- [x] T34 — Plan de pruebas manuales de la fase 5. *(escrito el 18-nov: 9 apartados, incluye el cierre de T30 y T32; falta que Mar lo recorra)*
  - **Qué se hace:** `docs/plan-pruebas-fase5.md` (gitignorado), cada paso con su explicación breve:
    perfil y secciones, CV base y visibilidad, borrador desfasado, añadir oferta por texto y por URL,
    privacidad con dos cuentas, estilo y muletillas.
  - **Test:** Mar lo recorre y anota lo que falle.
- [ ] T35 — Medición real al cerrar la fase (opcional, con OK de Mar).
  - **Qué se hace:** si Mar lo pide, lanzar `evals-reales` a mano una vez (~1,8 USD) para medir los
    agentes que cambiaron (`perfil`, `cv`, `cv-base`, `estilo`).
  - **Test:** sets en umbral con el modelo real; si no se lanza, queda anotado como pendiente para
    antes del lanzamiento.
