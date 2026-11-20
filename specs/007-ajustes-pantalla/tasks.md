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
- **Gasto:** solo T12 llama al modelo, y con el OK previo de Mar.
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
- [ ] T14 — Prueba manual de Mar.
  - **Test:** Mar recorre los criterios de aceptación de la spec y firma.
