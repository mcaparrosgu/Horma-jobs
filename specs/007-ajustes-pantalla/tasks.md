---
type: tasks
title: ajustes-pantalla — Desglose de tareas
description: Tareas pequeñas y comprobables de la fase 7. Cada una empieza con un test que falla; las de pantalla se comprueban a 1280 y 390 px, en claro y en oscuro.
tags: [tareas, frontend, extractor, matcher]
status: active
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-20 }
verified: { by: human, at: 2026-11-20 }
stale_after: null
---

# ajustes-pantalla — Tareas

## Forma de trabajo
- **Modelo:** la spec, con Opus; la construcción (B-F), con Sonnet.
- **Rama:** `fase7-construccion` desde `main`, con todos los bloques seguidos. El PR se abre al terminar E.
- **Gasto:** solo T12 y T17 llaman al modelo, y con el OK previo de Mar.
- **Tests:** `UV_NO_SYNC=1 uv run pytest`.

### Bloque A · Spec
- [x] T01 — Spec 007 escrita y aprobada. *(firmada por Mar el 20-nov)*
  - **Test:** Mar la lee y la firma (`verified`).

### Bloque B · Solo remoto (RF-7.1)
- [x] T02 — Columna y esquema `modalidad`.
  - **Qué se hace:** migración 0019; `OfertaExtraida.modalidad`; `remoto` derivado; repositorios.
  - **Test:** la migración crea la columna con su `CHECK`; `remoto` se deriva; la oferta se guarda y se
    lee con modalidad.
- [x] T03 — Extractor y evals.
  - **Qué se hace:** regla de `modalidad` en el prompt; origen (RT-08); 4 casos nuevos en `evals/ofertas`.
  - **Test:** evals de `ofertas` en simulado, en verde; el origen de la modalidad se comprueba.
- [x] T04 — Filtro estricto y pantalla.
  - **Qué se hace:** `buscar_ofertas`; `evaluar_condiciones`; ayuda de la casilla (RF-7.1d); modalidad en
    Recomendadas (RF-7.1e).
  - **Test:** híbrida fuera, remota dentro, sin dato fuera; con «Solo remoto» las propias también se filtran; RF-7.1f: todos los filtros y el rango valen igual para las propias.

### Bloque C · Ofertas propias sin fecha (RF-7.2)
- [x] T05 — Sin `sin_fecha` en las propias y «No consta fecha de publicación».
  - **Test:** flujo simulado con una propia y otra de catálogo; estáticos sin `creada_en` como «Publicado».

### Bloque D · Segunda persona (RF-7.3)
- [x] T06 — Prompt del `matcher` y comprobación en `evals.py`.
  - **Test:** el comprobador suspende «Lucía tiene…» y aprueba «Tienes…»; evals de `recomendacion` en
    simulado, en verde.

### Bloque E · Pantallas (RF-7.4-7.7)
- [x] T07 — Nombres enteros de idiomas y países.
  - **Test:** `nombrePais` y `nombreIdioma`, solo en `comun.js`; sin códigos a la vista en el navegador.
- [x] T08 — Perfil por bloques, en el orden de P3, con el texto de P4.
  - **Test:** orden y texto en `perfil.html`; Pendientes abierto solo si hay alguna.
- [x] T09 — Estilo compacto (RF-7.5c).
  - **Test:** con una guía de 12 + 12 rasgos se ven 5 + 5, y «Ver detalle» enseña todos con sus citas.
- [x] T10 — Ingesta: buscador y filtro.
  - **Test:** las 5 opciones del filtro; la búsqueda ignora tildes; «Ninguna fuente coincide».
- [x] T11 — Pestaña «Admin».
  - **Test:** sin `admin`, nada de Admin, Ingesta ni Costes en el menú; con `admin`, «Admin» la última y
    las subpestañas en Ingesta y Costes. El 403 del servidor sigue igual.

### Bloque F · Cierre
- [x] T12 — Evals reales de `ofertas` y `recomendacion`. *(20-nov: `ofertas` APROBADO, 29/29, 0,28 USD; `recomendacion` 0,26 USD con `segunda_persona`, `sin_rasgos` y `condiciones` al 100 %, y `nota` 0,67, el pendiente del plan del `matcher` de la spec 002, igual que el 15-nov)*
  - **Qué se hace:** medir el coste, pedir el OK de Mar y lanzar una pasada de cada set.
  - **Test:** las dos en su umbral (`evals/umbrales.json`).
- [x] T13 — Coherencia: `specs/index.md`, README y `system.md` si cambia algún RT.
### Bloque G · Correcciones de la prueba manual (P9-P13)
*(spec, plan y tareas del bloque firmados por Mar el 20-nov)*
Con Sonnet, todas seguidas, en la misma rama. Solo T17 llama al modelo, con el OK previo de Mar.
- [ ] T15 — «Volver a analizar» activo y edición guardada (RF-7.5f).
  - **Qué se hace:** reproducir en el navegador (consola y red del `PUT` y del `GET /api/estilo`); corregir la causa.
  - **Test:** falla antes del arreglo; tras guardar una guía, `origen` es «usuaria» y el botón no queda `disabled`.
- [ ] T16 — Rasgos cortos del analizador de estilo (RF-7.5e).
  - **Qué se hace:** regla de 8 palabras por rasgo y viñetas en una frase corta en el prompt; criterio de
    longitud en el set `estilo` de `evals.py`, sin bajar el umbral.
  - **Test:** el comprobador suspende un rasgo de 9 palabras y aprueba uno de 8; evals de `estilo` en simulado, en verde.
- [ ] T17 — Evals reales de `estilo`.
  - **Qué se hace:** medir el coste, pedir el OK de Mar y lanzar una pasada.
  - **Test:** en su umbral (`evals/umbrales.json`).
- [ ] T18 — Estilo en párrafo corto (RF-7.5c).
  - **Test:** con una guía de 12 + 12 rasgos se ven 5 + 5 separados por comas, y no hay «Ver detalle».
- [ ] T19 — Desplegables de Mi perfil (RF-7.5d).
  - **Test:** las cuatro secciones son `details` cerrados con su número; las demás no; tras guardar, una
    abierta sigue abierta.
- [ ] T20 — Condiciones simétricas (RF-7.1d) y totales de Costes (RF-7.8).
  - **Test:** cada casilla de Condiciones dentro de `.casilla-con-ayuda` con su ayuda; `tabla()` con dos
    filas pinta «Total» con las sumas y las medias ponderadas; sin filas, sin «Total».
  - **Navegador:** Perfil, Preferencias y Costes a 1280 y 390 px, en claro y en oscuro.
- [ ] T21 — Prueba manual del bloque G.
  - **Qué se hace:** añadir a `docs/plan-pruebas-007.md` solo los pasos de P9-P13; Mar los recorre y firma.

- [x] T14 — Prueba manual de Mar. *(hecha el 20-nov; de ella salieron P9-P14)*
  - **Test:** Mar recorre los criterios de aceptación de la spec y firma.
