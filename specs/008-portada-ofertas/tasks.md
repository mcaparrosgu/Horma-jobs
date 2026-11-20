---
type: tasks
title: portada-ofertas — Desglose de tareas
description: Tareas pequeñas y comprobables de la fase 8. Cada una empieza con un test que falla; las de pantalla se comprueban a 1280 y 390 px, en claro y en oscuro.
tags: [tareas, frontend, worker, flujos]
status: active
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-20 }
verified: { by: human, at: 2026-11-20 }
stale_after: null
---

# portada-ofertas — Tareas

## Forma de trabajo
- **Modelo:** la spec, con Opus; la construcción (B-E), con Sonnet.
- **Rama:** `fase8-construccion` desde `main` (o desde `fase8-spec` si aún no está fusionada), con todos los
  bloques seguidos. El PR se abre al terminar E.
- **Gasto:** ninguna tarea llama al modelo real. La prueba manual (T21) sí: se avisa antes.
- **Tests:** `UV_NO_SYNC=1 uv run pytest`.

### Bloque A · Spec
- [x] T01 — Aclaraciones y spec 008 escritas y aprobadas. *(firmadas por Mar el 20-nov)*
- [x] T02 — Plan y tareas aprobados. *(firmados por Mar el 20-nov)*
  - **Test:** Mar los lee y los firma (`verified`).

### Bloque B · Datos y API (RF-8.2c, RF-8.3, RF-8.6, RF-8.7)
- [x] T03 — Migración 0020: `tareas.progreso`, `tareas.actualizada_en`, índice y tabla `descartes`.
  - **Test:** columnas con su `CHECK`; índice; RLS de `descartes` (una usuaria no lee ni borra los de otra).
- [x] T04 — Repositorio y API de tareas.
  - **Qué se hace:** `gasto_hoy`, `ultima`, `sueltas_hoy`, `activas`, `avanzar`; `GET /api/tareas/activas` y
    `GET /api/tareas/{id}`.
  - **Test:** el progreso nunca baja; el día se corta a medianoche de Madrid; una usuaria no ve tareas ajenas.
- [x] T05 — Ofertas: catálogo solo para Admin, propias aparte y original.
  - **Qué se hace:** `exigir_admin` en `GET /ofertas` y `/ofertas/total`; `GET /api/ofertas/propias`;
    `GET /api/ofertas/{id}/original`.
  - **Test:** 403 sin `admin`; propias solo las suyas; original con el texto completo; propia ajena → 404;
    una URL que no es `http(s)` no sale.
- [x] T06 — Descartes y estado de candidatura en el listado.
  - **Qué se hace:** `PUT` / `DELETE /api/descartes/{oferta_id}`; `matches.listado` con `candidatura` y
    `descartada`; `GET /api/recomendaciones` sin rango ni orden.
  - **Test:** 409 con candidatura abierta; se descarta y se recupera; el listado trae el estado de la abierta o,
    si no la hay, el de la última cerrada.

### Bloque C · Landing, entrada y Admin (RF-8.1, RF-8.2)
- [x] T07 — Guía: «Ventana» y «Barra de avance».
  - **Qué se hace:** filas nuevas en la tabla de RF-6.4 (spec 006); `dialog.ventana` (sale del `visor` de
    Perfil, que pasa a usarla) y `.barra-avance` en `estilo.css`, con tokens.
  - **Test:** estáticos: las dos clases existen con tokens y Perfil usa `ventana`.
- [x] T08 — Landing y `/entrar`.
  - **Qué se hace:** `index.html` con el texto de RF-8.1b; `entrar.html`; redirecciones de `/` y `/entrar`.
  - **Test:** sin sesión, landing con «Crear cuenta» y «Entrar» hacia `/entrar`; con sesión, a Recomendadas o a
    Perfil sin perfil; sin «match», «ATS» ni «trazabilidad».
  - **Navegador:** landing y `/entrar` a 1280 y 390 px, en claro y en oscuro.
- [x] T09 — Pestañas sin Preferencias.
  - **Qué se hace:** `PESTANAS`; marca → `/recomendadas`; `/preferencias` → `/recomendadas#que-buscas`; rejilla
    móvil según el número de pestañas.
  - **Test:** `PESTANAS` con cinco; la redirección; ninguna pantalla enlaza a `/preferencias`.
- [x] T10 — Admin › Catálogo.
  - **Qué se hace:** `catalogo.html` / `.js` (lo de `app.js`) en `/catalogo` con `exigir_admin`; subpestañas
    Ingesta · Catálogo · Costes; se borra `app.js`.
  - **Test:** `/catalogo` → 403 sin `admin`; las tres subpestañas en las tres pantallas.
  - **Navegador:** Catálogo a 1280 y 390 px, en claro y en oscuro.

### Bloque D · Recomendadas (RF-8.3, RF-8.4, RF-8.6)
- [x] T11 — Panel «Qué buscas».
  - **Qué se hace:** el formulario de Preferencias en `details#que-buscas`, con «Guardar y buscar»; se borran
    `preferencias.html` y `preferencias.js`.
  - **Test:** abierto con las listas vacías o con `#que-buscas`; «Guardar y buscar» hace el `PUT` y luego
    `POST /api/recomendar {motivo: "buscar"}`.
- [x] T12 — Vista en el navegador.
  - **Qué se hace:** rango, orden y estado (Nuevas · Con candidatura · Descartadas, con su número) en una fila;
    `localStorage` con `try/catch`.
  - **Test:** cambiar la vista no hace ninguna petición al servidor; sin `localStorage`, valores por defecto.
- [x] T13 — Estado de candidatura y descartar.
  - **Qué se hace:** etiqueta y «Ver candidatura»; «Descartar» con aviso y «Deshacer»; «Recuperar».
  - **Test:** con candidatura abierta, sin «Descartar» y con «Ver candidatura» en lugar de «Preparar
    candidatura»; descartar y recuperar mueven la oferta entre vistas.
- [x] T14 — «Ver oferta original».
  - **Qué se hace:** `verOriginal(id)` en `comun.js`; botón en Recomendadas, Candidatura y Catálogo.
  - **Test:** el texto va con `textContent`; «Abrir en la web de origen» solo con URL; Esc cierra y el foco
    vuelve al botón.
  - **Navegador:** Recomendadas con la ventana abierta a 1280 y 390 px, en claro y en oscuro.

### Bloque E · Puntuar sin botón y avance (RF-8.5, RF-8.7)
- [x] T15 — Flujos con avance.
  - **Qué se hace:** `al_paso` en `PlainFlow` y `LangGraphFlow`; `al_tanda` en `recomendar`, con la revisión
    de RT-09 dentro de cada tanda.
  - **Test:** `al_paso` se llama una vez por paso en los dos; `al_tanda` una vez por tanda, con las
    explicaciones ya revisadas; evals de `recomendacion` en simulado, en verde.
- [x] T16 — Worker: guardado por tandas y progreso.
  - **Qué se hace:** `tarea_id` en `Dependencias`; guardar cada tanda y `avanzar`; rango 40-100 y orden
    «compatibles» fijos; descartadas excluidas; avance por pasos en el resto de tareas.
  - **Test:** un fallo en la tercera tanda deja guardadas las dos primeras; el progreso llega a 100 al
    terminar; una descartada no se puntúa.
- [x] T17 — `POST /api/recomendar` con las reglas de P1 y el tope del día.
  - **Test:** `reciente` antes de 1 h con «abrir»; «buscar» se lo salta; `tope` con 0,50 USD gastados;
    `en_marcha` devuelve la tarea en curso; `sin_pendientes`; el tope de la tarea es lo que queda del día;
    `puntuar_propias` sigue con el tope alcanzado.
- [x] T18 — «Puntuar ahora».
  - **Qué se hace:** `POST /api/matches/{oferta_id}/puntuar`, tarea `puntuar_una` y `_PuntuarUna`.
  - **Test:** puntúa una sola oferta; ya puntuada → 409; la 31.ª del día → 429 con el texto de RF-8.5f; con el
    tope del día alcanzado, funciona.
- [x] T19 — Pantallas con avance.
  - **Qué se hace:** `barraAvance` y `seguirTarea` en `comun.js`; Recomendadas sin «Recomendar», con la barra,
    los avisos de RF-8.5b y RF-8.5f, «Puntuar ahora» y las notas por tandas; barra en Añadir oferta y en
    Candidatura.
  - **Test:** estáticos sin `MAX_PUNTUANDO` ni botón «Recomendar»; al cargar con una tarea activa, la barra
    retoma su valor; al terminar, desaparece.
  - **Navegador:** Recomendadas, Añadir oferta y Candidatura con la barra a 1280 y 390 px, en claro y en oscuro.

### Bloque F · Cierre
- [x] T20 — Coherencia: `specs/index.md`, README, `system.md` si cambia algún RT; en la spec 002, RF-2.15c y en
  la 006, RF-6.3b, RF-6.3d, RF-6.3e y RF-6.5f marcados como sustituidos por la 008.
- [ ] T21 — Prueba manual de Mar.
  - **Qué se hace:** `docs/plan-pruebas-008.md` (gitignorado) con los criterios de aceptación; avisar del gasto
    antes; Mar los recorre y firma.
