---
type: plan
title: simplificacion — Plan técnico
description: Archivos y cambios que cubren la spec 010 por bloques (S1-S10) — textos y menú, candidatura sin CV base, avance y subida directa, Perfil en una pantalla con PDF del CV completo, analizador-oferta y presupuesto diario único con caché de la compatibilidad, orden interno y las correcciones tras la prueba.
tags: [plan, simplificacion, frontend, flujos, agentes, costes, arquitectura, migracion]
status: active
sources: [./spec.md, ./clarifications.md, ../system.md, ../008-portada-ofertas/plan.md, ../009-cv-maestro-entrevista/plan.md]
generated: { by: claude-code, at: 2026-11-21 }
verified: { by: human, at: 2026-11-21 }
stale_after: null
---

# simplificacion — Plan

Rutas relativas a `horma/`. Las líneas citadas son de `main` en `382f935`.

## Arquitectura
- **Un agente nuevo:** `analizador-oferta` (S5), que sustituye a tres. **Dos aparcados:**
  `clasificador-respuesta` y `generador-cv-base` (S6). Activos: de 13 a 9 (11 si S5 se revierte).
- **Cambia un prompt:** `redactor-cv` (S2), que ya no recibe CV base y condensa lo que no encaja.
- Las reglas de RT-01, RT-02, RT-12 y RT-13 no cambian. Se añade un contrato (S6): `web.routers` no importa
  `web.repositories` ni `web.queue`.

| Requisito | Dónde |
|---|---|
| RF-10.1 | `routers/paginas.py:33-47`, `routers/auth.py:34`; `static/index.html`; `static/comun.js:6-12` |
| RF-10.1e | `routers/paginas.py` (redirecciones 308) |
| RF-10.2 | `static/textos.js` nuevo; todos los `static/*.js`; `static/*.html` |
| RF-10.3 | `flows/candidatura.py:114-187`; `tools/elegir_cv_base.py`; `services/candidaturas.py:85-86,139-149`; `queue/worker.py:346-348`; `agents/redactor_cv/prompt.md` |
| RF-10.4 | `tools/generar_pdf.py:24`; `routers/perfil.py` (`GET /api/perfil/cv.pdf`) |
| RF-10.5 | `static/perfil.html`, `static/perfil.js`; `services/cv.py:19` |
| RF-10.6 | `static/recomendadas.*` → `static/ofertas.*`; `static/anadir-oferta.*` → ventana en `ofertas.js` |
| RF-10.7 | `textos.js` (`estadoVisible(estado, preparacion)`); `candidatura.js`, `candidaturas.js`, `ofertas.js` |
| RF-10.8 | Desde S7: `barraAvance()` en la pantalla de cada tarea (`perfil.js` con `/api/tareas/activas?tipo=perfilar`); sin indicador en la cabecera |
| RF-10.9 | `services/presupuesto.py` nuevo; `repositories/tareas.py:50` (`gasto_hoy`); `config.py` |
| RF-10.10 | `agents/analizador_oferta/` nuevo; `flows/procesar_oferta.py`; migración `0022` (`matches.huella_perfil`) |
| RF-10.18 | `routers/cv.py` (`POST /api/cv/lote`); `services/cv.py` (`subir_lote`); `static/perfil.html`, `perfil.js`, `textos.js` |
| RF-10.11 | `services/*`; `routers/*`; `queue/worker.py` (tabla `ENCADENADOS`); `.importlinter`; `config.py:17-18,67` |

## S1 · Palabras y menú (RF-10.1, 10.2, 10.6, 10.7)
- **`static/textos.js`** (nuevo, se carga antes que `comun.js` en todas las páginas, también en Admin):
  `ESTADOS_VISIBLES`, `estadoVisible(estado, preparacion)` (tabla de RF-10.7), `MOTIVOS_CIERRE`,
  `MOTIVOS_PREGUNTA`, textos de avisos y ayudas. Sustituye a `recomendadas.js:14`, `candidatura.js:6`,
  `candidaturas.js:2,5,15-16`, `perfil.js:29,265` y `recomendadas.js:18`. `TEXTO_SUELTAS` sale también de
  `routers/recomendaciones.py:90` (la API devuelve un código; el texto lo pone la pantalla).
- **Menú:** `comun.js:6-12` con tres pestañas. `ingesta.js` y `costes.js` cargan `comun.js` y borran sus copias
  de `$`, `csrf`, `nodo`, `avisar`, `api`, `fecha`, `/api/yo` y salir (`ingesta.js:2-45,305-312`;
  `costes.js:2-9,93-97`).
- **Landing:** `index.html` con «Continuar con Google» (`/auth/google`) en la cabecera y al final; «Cómo
  empezar» en tres pasos. `/entrar` → 308 a `/`. El callback (`auth.py:34`) sigue yendo a `/`, que redirige.
- **Ofertas:** `recomendadas.html/js` se renombran a `ofertas.html/js`; ruta `/ofertas`. La ventana «Añadir
  oferta» usa el componente «Ventana» de la guía (RF-8.3d) con el formulario de `anadir-oferta.html`, que se
  borra. `/recomendadas` y `/anadir-oferta` → 308 (la segunda a `/ofertas#anadir`, que abre la ventana).
- **Sin perfil:** `recomendadas.js:497-501` trata `sin_perfil`: estado vacío con el texto de RF-10.6c y botón a
  `/perfil`. La API ya devuelve el motivo (`routers/recomendaciones.py:68-69`).
- **Textos internos:** fuera «Mar la revisará» (`recomendadas.js:120`), «Apify» (`anadir-oferta.html:32`), «el
  auditor» (`anadir-oferta.js:31`, `recomendadas.js:376,379`: «Señales de fraude»), «tope de coste»
  (`recomendadas.js:471`: la API manda `motivo="presupuesto"` y la pantalla lo traduce). «nota» y
  «puntuación» → «compatibilidad» (unas 50 apariciones en `recomendadas.*` y `anadir-oferta.js`). «hueco» de la
  candidatura (`candidatura.js`) → texto de RF-10.2c.
- **CV base en S1:** solo se quita la pestaña; la pantalla sigue accesible por URL hasta S2 (sin enlaces).
- **Test estático** `tests/test_textos_usuaria.py`: recorre `static/*.html|js` de usuaria y falla si aparece
  una palabra prohibida de RF-10.2b/2d fuera de `textos.js` y de rutas de la API.

## S2 · Candidatura sin CV base (RF-10.3)
- **Flujo:** `elegir` (`flows/candidatura.py:114-122`) deja de llamar a `elegir_cv_base` cuando no hay CV base:
  `cv_base_contenido = None`. Con el ajuste `HORMA_CV_BASE_RESPALDO` (por defecto `false`, RF-10.3d) se usa un
  CV base si existe. Fuentes de `comprobar` (:158) y juez (:187): solo `cv_maestro` cuando no hay CV base.
- **Redactor:** `redactor_cv/schemas.py` con `cv_base: str | None` y `longitud: "mantener" | "sintetizar" |
  None`. Prompt: sin CV base, parte del CV maestro; condensa en una línea (puesto · empresa · fechas) la
  experiencia que no encaja con la oferta; con «mantener», no condensa. El worker pasa `longitud_cv` de
  `ajustes_perfil` (hoy no lo lee nadie: `routers/perfil.py:80`).
- **Servicio:** `services/candidaturas.py:85-86` deja de exigir CV base (solo perfil). `:139-149` recalcula avisos
  con el maestro y, si la candidatura tiene `cv_base_id`, también con él (RF-10.3f).
- **Worker:** `worker.py:346-348` carga los CV base solo si el respaldo está activo.
- **Eval `cv`:** casos sin CV base (los 23 actuales con `cv_base` vacío) más 3 de condensación (experiencia de
  otro sector → una línea) y 2 de longitud. Umbral de hoy. **Se avisa del gasto antes (~0,5-1 USD).**
- **Si pasa:** se borran la pantalla `/cv-base` (`cv-base.html/js`, 308 a `/perfil`), los endpoints de
  `routers/cv.py:117-218` y la tarea del worker (en S6). Las tablas se quedan.
- **Si no pasa:** `HORMA_CV_BASE_RESPALDO=true`, la pantalla se queda escondida y se apunta en la spec.

## S3 · Avance en la cabecera y subida directa (RF-10.8, RF-10.5 subida)
> El indicador de la cabecera se retiró en S7 (RF-10.8 reescrito): ver «Avance» en S7.

- **API:** `GET /api/tareas/activas` sin `tipo` devuelve las tareas en marcha de la usuaria con `tipo`,
  `progreso` y la URL de su pantalla (`perfil`, `ofertas`, `candidaturas/{id}`).
- **Cabecera:** `comun.js` añade el indicador «Indicador de avance» (nuevo en la guía): frase + %, enlace a la
  pantalla, `role="status"`. Sondea cada 3 s solo mientras haya tareas; al terminar, desaparece. Las recargas
  propias (`perfil.js:367,632`, `candidaturas.js:47`, `anadir-oferta.js:54,85`) pasan a `seguirTarea`
  (`comun.js:194`).
- **Subida:** `perfil.html:27-45`: sin botón «Subir CV» ni casilla; el `change` del `input[type=file]` sube con
  `clase=fuente`. «Carta» se sube desde «Documentos subidos» (S4).

## S4 · Perfil en una pantalla (RF-10.4, RF-10.5)
- **Pantalla:** `perfil.html` con los cinco bloques de RF-10.5b, dos columnas a 1280 px (rejilla de la guía).
  Sin perfil, solo «Sube tu CV».
- **Por resolver:** junta `preguntas_pendientes` y `GET /api/perfil/avisos`. «Dar por visto» (en S4 se llamó
  «Está bien así»; S7 recuperó el nombre) = `PUT /api/perfil/avisos/visto` (y, en una pregunta, la respuesta «Nada que añadir» que ya existe). La tarjeta
  `#maestro-longitud` (`perfil.js:321-340`) se borra; queda la del aviso `largo` (`:281-284`).
- **Tu CV completo:** «Ver» abre el CV maestro en la Ventana (`cvBonito`); «Descargar PDF» llama a
  `GET /api/perfil/cv.pdf`, que usa `generar_pdf(perfiles.cv_maestro)`. RLS por sesión; sin perfil, 404.
- **Documentos subidos:** la lista de hoy («Tus CV») con «Subir» (clases «CV» y «Carta»). `services/cv.py:19`:
  `CLASES = ("fuente", "carta")`; un `estetico` nuevo da 422. Los antiguos se listan como «Documento».
- **Cómo escribes:** el bloque de estilo de hoy, plegado.

## S5 · Ahorro (RF-10.9, RF-10.10, RF-10.11c)
- **`analizador-oferta`** (`agents/analizador_oferta/`, modelo pequeño): `SalidaAnalizador` = `OfertaExtraida` +
  `Taxonomia` + `generica`, `fraude`, `senales_fraude`, `dominio_empresa` (los campos de
  `auditor_oferta/schemas.py:18-30`). Prompt = los tres de hoy, fundidos, con las mismas reglas de citas.
- **Flujo:** `procesar_oferta` = analizar → verificar_origen → comprobar_empresa → componer (las comprobaciones
  de código de `:43-102` no cambian). Ajuste `HORMA_OFERTA_UN_AGENTE` (por defecto `true` si pasa el eval);
  con `false`, el flujo de hoy, que se conserva.
- **Evals:** `ofertas` (29 casos) y `red-teaming` con `analizador-oferta`. **Se avisa del gasto antes (~1-2 USD).**
- **Presupuesto:** `services/presupuesto.py` con `restante_hoy(usuaria) -> float` (1 USD − `gasto_hoy` de todos
  los tipos de la usuaria, día de Madrid) y `encolar(usuaria, tipo, carga)`, único punto de encolado (S6 lo
  hace obligatorio). Sin presupuesto → `SinPresupuesto` (429 con `motivo="presupuesto"`). Cada tarea lleva
  `tope = min(tope_tipo, restante)`. Se borran `tope_gasto_diario_puntuar` y `max_sueltas_dia`.
- **Ofertas propias sin presupuesto (RF-10.9e):** la oferta se guarda en `pendiente` (estado que ya existe,
  migración `0001`) sin tarea; el worker, en su comprobación periódica, encola las propias pendientes sin tarea
  de cada usuaria que vuelva a tener presupuesto.
- **Caché de compatibilidad:** migración `0022` añade `matches.huella_perfil text` (hash de experiencia,
  formación, habilidades, idiomas y titular, `tools/huella_perfil.py`). Puntuar excluye las ofertas que ya
  tienen un match con la huella vigente (`worker.py:257`, `routers/recomendaciones.py:79`); el listado
  (`repositories/matches.py:39-46`) toma ese match como vigente, sin «desfasado». Relleno: las filas de hoy
  calculan su huella desde su `perfil_version`.
- **`clasificar_perfil`:** `services/perfil.py:82` lo encola solo si cambia la huella de experiencia,
  formación o titular.
- **Precios:** `config.py:17-18` con la tarifa oficial de Anthropic y la fecha de consulta en el comentario.

## S6 · Orden interno (RF-10.11)
- **Encolar:** los routers que encolan (`cv.py:130,145`, `ofertas.py:73`, `recomendaciones.py:85,109`) pasan
  por servicios. `preferencias.py` y `recomendaciones.py` ganan servicio; el SQL en línea
  (`recomendaciones.py:195`) va a un repositorio. Los routers de `cv`, `estilo`, `ofertas`, `paginas`,
  `perfil`, `tareas` dejan de importar repositorios.
- **Contrato** en `.importlinter`: `horma.web.routers` no importa `horma.web.repositories` ni
  `horma.web.queue`.
- **Encadenados:** `worker.py:107,118,169-170,191` pasan a una tabla `ENCADENADOS = {tipo: [siguientes]}` con
  sus condiciones, leída en un solo sitio.
- **Aparcar:** `clasificador-respuesta` y `generador-cv-base` salen de `agents/registry.py` y
  `flows/registry.py` activos a un `APARCADOS` (la consola los avisa); sus sets salen de `ci.yml:61,123` y de
  `umbrales.json`. Se borra `extraer_oferta` (`worker.py:4,409`) y la tarea `generar_cv_base`
  (`worker.py:197-245,411-412`).
- **LangGraph:** `config.py:67` → `"langgraph"`. La suite de flujos sigue parametrizada con las dos.
- **`system.md`:** agentes activos y aparcados, fase 010 en la tabla de fases, `langgraph` por defecto, 10
  módulos de esquemas con tablas en SQL, herramientas con red (`descargar`, `leer_pagina`, `dominio`),
  alertas a 5 USD y 50 %, regla «solo los servicios encolan».

## S7 · Correcciones tras la prueba (RF-10.3g, 10.4d, 10.5c, 10.6e, 10.8, 10.13, RF-6.4b)
- **«Avisos» en Perfil (RF-10.5c):** se recupera el desplegable de `4fc7024^:static/perfil.html` dentro de «Por
  resolver»; `perfil.js` (`avisoFila`, `cargarAvisos`) vuelve a «Dar por visto» (texto en `textos.js`). Backend
  igual (`PUT /api/perfil/avisos/visto`).
- **Avisos agrupados (RF-10.13):** `Aviso` (`schemas/candidatura.py`) gana `tipo` (`no_consta | revisa |
  dudoso`, por defecto `revisa` para las antiguas); lo rellenan `componer` (`flows/candidatura.py`) y el
  recálculo al editar (`services/candidaturas.py`). Los huecos de `ausentes_sin_origen` se juntan en uno.
  `revisaEsto()` (`candidatura.js`) pinta los tres grupos y no pinta el panel vacío. En Perfil,
  `tools/avisos_perfil.py` agrupa las claves con prefijo (`sin_cifras:`, `sin_descripcion:`, `sin_contacto:`)
  y «Dar por visto» del grupo marca todas sus claves.
- **Avance (RF-10.8):** fuera el indicador de `comun.js` y `.indicador-avance` de `estilo.css`; Perfil usa
  `barraAvance()` mientras se lee el CV, con `/api/tareas/activas?tipo=perfilar`. Si nadie usa
  `/api/tareas/activas` sin `tipo`, se quita esa variante.
- **Qué buscas (RF-10.6e):** `#grupo-excluidos` pasa detrás de «Condiciones» en `ofertas.html`.
- **PDF (RF-10.4d):** `tools/generar_pdf.py` (fpdf2) con Familjen Grotesk y DM Mono en TTF en
  `assets/fuentes/` (OFL) y DejaVu de respaldo; parámetro `tipo="cv"|"carta"` desde `services/perfil.py`,
  `flows/candidatura.py`, `services/candidaturas.py` y `cli.py`. En «Ver», la carta se pinta como párrafos
  (`candidatura.js`), no con `cvBonito`.
- **Carta (RF-10.3g):** diagnóstico de la carta de la prueba 2.3; `agents/redactor_carta/prompt.md` reescrito
  con la estructura de RF-10.3g y un ejemplo inventado que cumple la traza; casos nuevos de carta en
  `evals/cv/casos/`. RT-08 y `verificar_trazabilidad` no cambian.
- **Simetría (RF-6.4b):** h2 dentro de `.panel` sin margen superior; un solo estilo de tarjeta en la columna
  derecha de Perfil; tablero de Candidaturas sin columna huérfana a 1280 px; «Condiciones» y `.grupos` de
  Ofertas con la misma línea base; «Sube tu CV» y `#subir-doc` alineados; botones de la candidatura sin
  estirar y enlace de vuelta a 44 px. Comprobado a 1280 px, en claro y en oscuro; 390 px, pendiente (T36).
- **Repaso del 22-nov (RF-10.4e, 10.5b, 10.5f, 10.6f):**
  - Sin «Área»: `repositories/perfiles.py` (`GRUPOS_DEL_CV` sin `familias`) y `ofertas.js` (vacía `familias` al
    guardar); Puestos · Sector · Condiciones en una fila (`ofertas.html`, `estilo.css`).
  - Nombre editable: campo `nombre` en `services/perfil.py`, `perfil.html/js`; `extractor_perfil/prompt.md` lo pide.
  - Descargas: `nombre_descarga()` en `services/candidaturas.py` (`cv-puesto-empresa.pdf`), usada por
    `_descarga()` de `routers/candidaturas.py` en `Content-Disposition`.
  - Perfil en el orden de RF-10.5b (`perfil.html`); barras en lima (`--bar-fill` en `tokens.css`).

## S8 · Correcciones de la pasada del 22-nov (RF-10.14 a 10.14r)
Diagnóstico hecho con Opus sobre los datos de la pasada (usuaria 100, perfiles v1-v7).
- **Puestos con género (RF-10.14p):** `tools/normalizar_titulo.py` hoy da «jefe a de sala» para «Jefe/a de sala»
  y no une «jefa» con «jefe». Quitar las marcas de género (`/a`, `/as`, `(a)`, `/o`) al normalizar, y en
  `buscar_ofertas.frases()` y `repositories/ofertas.contar_por_puesto()` buscar también la variante femenina de
  cada puesto (reglas cortas de terminación: `-o/-a`, `-e/-a` en «jefe», `-or/-ora`). `ofertas.titulo_norm` está
  guardado: migración que lo recalcule.
- **Resumen y titular por CV (RF-10.14d):** hoy `flows/perfilar.py` (`_UNICOS`) descarta el resumen combinado
  porque su cita no está en un solo CV. `schemas/perfil.py` gana `resumenes` y `titulares` (lista con origen por
  `cv_id`), y `resumen`/`titular` se quedan como el del CV más reciente (compatibilidad con lo que ya los lee:
  `componer_cv_maestro`, `avisos_perfil`, `puestos_del_perfil`, `huella_perfil`). `extractor_perfil/prompt.md`
  devuelve uno por CV. `redactor_cv` recibe todos y elige: si cambia su prompt, eval `cv` (avisar del gasto).
- **Rehacer al borrar (RF-10.14):** `services/cv.eliminar()` encola `perfilar` con los CV que quedan, o deja a la
  usuaria sin perfil vigente si no queda ninguno, sin borrar versiones a las que apunten candidaturas o
  compatibilidades. **Riesgo encontrado:** hoy `perfilar` no conserva lo que la usuaria escribió (origen
  `usuaria`, `services/perfil.py:39`); al rehacer (y también al subir un CV nuevo) hay que llevar esos datos a la
  versión nueva. Test para los dos casos.
- **CV o carta (RF-10.14b):** `tools/clasificar_documento.py`, código puro sobre el texto extraído (secciones y
  fechas frente a saludo, párrafos y despedida), con «duda» si no está claro. Lo usa la subida en
  `services/cv.py`; la clase se puede cambiar después (endpoint de cambiar clase; si pasa a CV, encola
  `perfilar`).
- **DOCX (RF-10.14c):** «Ver» sirve `cv_archivos.texto`; «Descargar original», el archivo con su tipo.
- **Respuesta en Por resolver (RF-10.14e):** el servicio que guarda la respuesta devuelve qué campo cambió;
  `perfil.js` lo enseña. En la pasada se guardó bien («Excel básico» en Habilidades); lo que seguía diciendo
  «avanzado» era el curso en Certificaciones.
- **Perfil (RF-10.14f-k):** `perfil.js` sin `#version` y con el mensaje nuevo (hoy, líneas 117 y 409);
  certificaciones dentro de Formación; etiqueta del nombre; «Añadir» del hueco con la pregunta; fechas: se
  guardan como hoy (AAAA-MM) y se convierten a MM-AAAA al pintar y al leer lo que escribe; «Corregir» por
  experiencia en el aviso agrupado «Sin cifras» (`tools/avisos_perfil.py` ya trae los elementos).
- **Cómo escribes (RF-10.14l):** listas en `perfil.js`; texto vacío de «Evitas»; etiqueta según `estilo.origen`.
- **Ayuda «?» (RF-10.14m):** el componente de `ofertas.js` (`ayuda()`) pasa a `comun.js` y a la guía como
  «Explicación plegable»; se usa en Perfil, Ofertas, Candidaturas y Candidatura. Textos en `textos.js`.
- **Mensajes (RF-10.14n):** `perfil.js` pinta a la vez la barra (l. 393) y «CV subido; se está construyendo…»
  (l. 557); se deja solo la barra. Revisar Ofertas y Candidatura.
- **PDF (RF-10.14o):** `tools/generar_pdf.py`: no empezar sección si no caben título y dos líneas; no dejar una
  línea sola. Test con el CV completo de la pasada (3 páginas, dos casi vacías).
- **Lista vacía (RF-10.14q):** `ofertas.js`, cuando `todas` está vacío y hay puestos marcados.
- **Ingesta atascada (RF-10.14r):** al reclamar una ejecución, `repositories/ingesta.py` cierra como error las que
  lleven más de 30 min en curso (la 7, de Himalayas, lleva así desde el 22-nov a las 8:21).
- **Correcciones finales (T63-T67, cruce del 22-nov):** «Valenciano» desde `origen.fragmento` en
  `componer_cv_maestro` y sinónimos en `normalizar_oferta`; huecos sin duplicados ni texto interno en
  `flows/candidatura.py`; barra y estado vacío sin parpadeo en `perfil.js`; saludos «Hola, equipo:» en la lista de
  `verificar_trazabilidad.py`, el prompt de `redactor_carta` y `evals/cv` (las formas antiguas se siguen aceptando
  al comprobar); coste 0 en el eval simulado. El eval `cv` real de T50 cubre T44 y T66.

## S9 · «Corregir explicación» amplía la información (RF-10.15 a 10.15e) — firmada el 22-nov
- **Guardar (RF-10.15):** `Correccion` (`routers/recomendaciones.py`) gana `informacion` (opcional, máx. 1000);
  va dentro del JSON de `matches.correccion`, sin migración. `ofertas.js` añade el campo y el texto de ayuda
  (RF-10.15e, en `textos.js`).
- **Usar en candidaturas nuevas (RF-10.15b):** `services/candidaturas.crear` lee `informacion` de la corrección de
  esa oferta y el flujo `candidatura` la añade a las fuentes como una sección más al final del CV maestro
  («Información que añadiste para esta oferta», origen «usuaria»). La reciben `redactor_cv`, `redactor_carta`, el
  juez y la trazabilidad, que impide ampliarla: cada dato tiene que estar en las fuentes. **Los prompts no cambian**
  (decisión del 22-nov): sin eval. No se guarda en el perfil. Las candidaturas existentes no se recalculan.
- **Preguntar y revisar (RF-10.15c-d):** tras enviar, `ofertas.js` pregunta; «Sí, revisarla» llama a un endpoint
  nuevo que añade la propuesta a `por_resolver` del perfil vigente (sin versión nueva, sin modelo). Perfil la
  enseña en «Por resolver» con el flujo de `services/perfil.responder` (editar, colocar o descartar); solo al
  confirmar se crea la versión y se aplican las «desfasadas».
- **Decidido al construir:**
  - La información viaja con la candidatura: migración `0029` (`candidaturas.informacion`), que se rellena al
    crearla. Así una ya preparada no cambia, «Volver a preparar» usa la misma y, al editarla, los avisos se
    recalculan con las mismas fuentes. Se toma de la última corrección de esa oferta, aunque la compatibilidad se
    haya recalculado después.
  - La sección se añade con `maestro_con_informacion()` (`flows/candidatura.py`), no al CV maestro guardado.
  - La propuesta es un pendiente más de `perfiles.preguntas_pendientes` (`campo` = `propuesta`, texto en
    `opciones`), sin cambiar el esquema que ve el modelo. Endpoint: `POST /api/matches/{id}/informacion/perfil`.
    Se confirma con `POST /api/perfil/respuestas` más `campo` (experiencias, habilidades, formacion u otros);
    descartarla la quita sin crear versión. Al rehacer el perfil (subir o borrar un CV) las propuestas se conservan.
  - El motivo de la corrección sigue siendo obligatorio. La ayuda dice «el equipo de Horma», no «Mar» (RF-10.2d).
- **Tests:** la información llega al redactor en una candidatura nueva y no en una anterior; «No» no toca
  `por_resolver`; «Sí» añade la propuesta y el perfil no cambia de versión hasta confirmarla.

## S10 · Subir varios documentos a la vez (RF-10.18 a 10.18i) — firmada el 23-nov
Sin agente, sin prompt y sin migración. Opción más simple descartada: subir los archivos uno a uno desde la
pantalla con el `POST /api/cv` de hoy; rehace el perfil una vez por archivo (hasta 5 × 0,50 USD de tope).
- **API:** `POST /api/cv/lote` (`routers/cv.py`), con `archivos: list[UploadFile]` y `clases` opcional (una por
  archivo, solo en la respuesta a la pregunta). Más de 5 → 422 con el texto de RF-10.18b, sin guardar nada. Cuenta
  como una subida para `limite_subida_cv`. Las dos pantallas usan solo este endpoint; `POST /api/cv` se quita si
  nadie más lo llama.
- **Servicio:** `services/cv.subir_lote()` reutiliza por archivo las comprobaciones de `subir()` (`_tipo`, peso,
  `convertir_cv`, `clasificar_documento`) y recoge cada `ArchivoRechazado` como fallido en vez de cortar. Devuelve
  `{subidos, repetidos, fallidos, dudosos, perfil: "en_marcha" | "aplazado" | "pendiente_de_respuesta" | null}`.
  Un nombre ya usado por otro documento distinto sigue la regla de hoy (`NombreRepetido`) y va a `fallidos`.
- **Repetidos (RF-10.18d):** por contenido. Dentro del lote, por `sha256`; contra los ya subidos, se comparan
  los de igual `tamano` leyendo su archivo. Sin columna nueva.
- **Un solo `perfilar` (RF-10.18f):** todos los archivos se guardan en una transacción y, si hay algún CV nuevo,
  un único `perfiles.nueva_version` + `presupuesto.encolar("perfilar")` al final. Las cartas llaman una vez a
  `servicio_estilo.encolar_si_no_hay_guia`.
- **Sin presupuesto (RF-10.18g):** como `_rehacer_perfil`: se captura `SinPresupuesto`, la versión queda reservada
  y la recoge `rehacer_aplazados` (ya existe). Cambia lo de hoy: `subir()` borraba el archivo y daba 429.
- **Dudosos (RF-10.18e):** como hoy, un dudoso no se guarda: la pantalla conserva el archivo, pinta una sola
  pregunta (`#pregunta-clase` con un `select` «CV / Carta» por archivo y «Continuar») y vuelve a llamar al lote con
  `clases`. Con dudosos pendientes, la primera llamada guarda los claros y **no** encola; el `perfilar` único sale
  de la segunda llamada, que también se hace al cerrar la pregunta (sin los dudosos). Si ella se va de la página
  sin responder, los claros quedan guardados y su perfil por rehacer: usar la versión reservada que recoge
  `rehacer_aplazados`, sin que llegue a rehacerse dos veces. Detalle a decidir al construir, tras leer
  `perfiles_aplazados()`.
- **Pantalla:** `perfil.html`: `multiple` en `#archivo` y `#archivo-doc` y «hasta 5 archivos» en los dos textos.
  `perfil.js`: `subirDocumento` envía `entrada.files` entero; comprueba el máximo antes de enviar; un solo mensaje
  de resultado (RF-10.18i); la barra de `barraAvance()` se crea al empezar con «Leyendo N archivos» y se conserva
  el nodo (como T65) durante la subida, la pregunta y el `perfilar`. Textos en `textos.js`. Sin componente nuevo
  en la guía: `select` y Ventana ya están.
- **Tests:** lote mixto (dos CV, carta, repetido, formato malo) → tres filas, una tarea `perfilar`; 6 archivos →
  nada guardado; repetido de uno ya subido; dudoso → una pregunta y `perfilar` solo tras la respuesta; sin
  presupuesto → filas guardadas, versión aplazada y `rehacer_aplazados` la encola; otra usuaria no ve nada (RLS).
- **Riesgo (bajo):** 5 CV más los ya subidos en un solo `perfilar` pueden acercarse al tope de 0,50 USD; se mide en
  la prueba de cierre y, si no cabe, se trae a Mar antes de tocar el tope.

## Datos
- Migración `0022_simplificacion.py` (S5): `matches.huella_perfil` con relleno e índice
  `(usuaria_id, oferta_id, huella_perfil)`. Sin borrar tablas ni columnas.

## Tests
- Estáticos: palabras prohibidas; tres pestañas; `textos.js` cargado en todas las páginas; Admin sin copias de
  utilidades.
- Rutas: redirecciones de RF-10.1e; `/` con y sin sesión.
- Candidatura: sin CV base, `crear` no da 409; el flujo redacta con solo el maestro; una antigua con
  `cv_base_id` recalcula avisos con él.
- PDF: `GET /api/perfil/cv.pdf` da `application/pdf`; otra usuaria, 404.
- Presupuesto: con 1 USD gastado, ningún servicio encola y da 429; el tope de la tarea es el restante; una
  oferta propia queda pendiente y se procesa al día siguiente.
- Caché: editar el resumen no cambia la huella ni vuelve a puntuar; editar una experiencia sí.
- Arquitectura: contrato nuevo de import-linter; `analizador-oferta` cumple RT-01.
- Flujos: `procesar_oferta` con una llamada (simulado); con `HORMA_OFERTA_UN_AGENTE=false`, tres.
- Navegador: cada bloque con pantallas, a 1280 y 390 px, en claro y en oscuro.

## Riesgos
- **S2 (medio):** calidad del CV sin CV base. Puerta: eval `cv`; respaldo con el ajuste.
- **S5 (medio):** precisión por campo con un solo agente. Puerta: evals `ofertas` y `red-teaming`; vuelta
  atrás con el ajuste.
- **S1 (bajo):** renombrar `/recomendadas` rompe marcadores; las redirecciones lo cubren.

## Coste
- S2: eval `cv` real, ~0,5-1 USD. S5: evals `ofertas` y `red-teaming`, ~1-2 USD. Prueba manual de cada bloque:
  céntimos (un CV y una candidatura). Se avisa siempre antes.
- S7: eval `cv` real (~0,5-1 USD) y una candidatura de prueba (~0,2 USD), los dos en T35.
- S8: prueba manual (subir y borrar CV, ~0,3-0,6 USD). Si cambia el prompt de `redactor-cv` o `extractor-perfil`,
  eval `cv` real (la última vez, ~1,9 USD): se avisa antes.
- S10: construir, 0 (tests simulados). Prueba manual, ~0,1-0,3 USD (un lote = un `perfilar`). Sin eval.
