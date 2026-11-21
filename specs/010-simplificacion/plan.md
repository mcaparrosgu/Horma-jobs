---
type: plan
title: simplificacion — Plan técnico
description: Archivos y cambios que cubren la spec 010 por bloques (S1-S6) — textos y menú, candidatura sin CV base, avance en la cabecera y subida directa, Perfil en una pantalla con PDF del CV completo, analizador-oferta y presupuesto diario único con caché de la compatibilidad, y orden interno.
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
| RF-10.8 | `static/comun.js` (cabecera); `routers/tareas.py:20` (`/api/tareas/activas` sin `tipo`) |
| RF-10.9 | `services/presupuesto.py` nuevo; `repositories/tareas.py:50` (`gasto_hoy`); `config.py` |
| RF-10.10 | `agents/analizador_oferta/` nuevo; `flows/procesar_oferta.py`; migración `0022` (`matches.huella_perfil`) |
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
- **Por resolver:** junta `preguntas_pendientes` y `GET /api/perfil/avisos`. «Está bien así» =
  `PUT /api/perfil/avisos/visto` (y, en una pregunta, la respuesta «Nada que añadir» que ya existe). La tarjeta
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
- **Qué buscas (RF-10.6e):** `#grupo-excluidos` pasa detrás de «Condiciones» en `ofertas.html`; «Puestos
  sugeridos» a todo el ancho (`.grupos-dos` en `estilo.css`).
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
  estirar y enlace de vuelta a 44 px. Comprobado en el navegador a 1280 y 390 px, en claro y en oscuro.

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
