---
type: tasks
title: simplificacion — Desglose de tareas
description: Tareas pequeñas y comprobables de la simplificación, por bloques S1-S6 (una rama y un PR por bloque). Cada una empieza con un test que falla; las de pantalla se comprueban a 1280 y 390 px, en claro y en oscuro.
tags: [tareas, simplificacion, frontend, flujos, costes, arquitectura]
status: active
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-21 }
verified: { by: human, at: 2026-11-21 }
stale_after: null
---

# simplificacion — Tareas

## Forma de trabajo
- **Modelo:** aclaraciones, spec, plan y tareas, con Opus; la construcción (S1-S6), con Sonnet. Un fallo de
  eval poco claro se analiza con Opus.
- **Ramas:** una por bloque desde `main` (`simplificacion-s1` … `simplificacion-s6`), cada una con su PR. Mar
  prueba y firma cada bloque antes del siguiente. Dentro de un bloque, todas las tareas seguidas.
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
- [ ] T12 — Cierre de S2: prueba manual de Mar (usuaria nueva: sube CV y prepara candidatura) y PR. *(la prueba pasa al plan de pruebas de la fase 10)*

### S3 · Avance y subida (RF-10.8, RF-10.5 subida)
- [x] T13 — Indicador de avance en la guía y en la cabecera. *(navegador sin comprobar: 1280/390 px, claro/oscuro)*
  - **Test:** `/api/tareas/activas` sin `tipo` da las tareas de la usuaria con su URL; otra usuaria no las ve;
    el indicador desaparece al terminar.
  - **Navegador:** cabecera con indicador a 1280 y 390 px, en claro y en oscuro.
- [x] T14 — Subida al elegir el archivo. *(«Carta» no se sube hasta S4)*
  - **Test:** el `change` sube con `clase=fuente`; no hay botón «Subir CV» en el estado vacío.
- [ ] T15 — Cierre de S3: prueba manual de Mar y PR.

### S4 · Perfil en una pantalla (RF-10.4, RF-10.5)
- [x] T16 — `GET /api/perfil/cv.pdf`.
  - **Test:** da `application/pdf` con el nombre y una experiencia del perfil; otra usuaria o sin perfil, 404.
- [x] T17 — Perfil: estado vacío, cinco bloques, «Por resolver», una sola elección de longitud, clases «CV» y
  «Carta». *(navegador sin comprobar: 1280/390 px, claro/oscuro)*
  - **Test:** orden de RF-10.5b; cada elemento de «Por resolver» con dos acciones; `estetico` nuevo → 422; un
    estético antiguo se lista.
  - **Navegador:** Perfil vacío y lleno a 1280 y 390 px, en claro y en oscuro.
- [ ] T18 — Cierre de S4: prueba manual de Mar y PR.

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
- [x] T23 — Cierre de S5: prueba manual de Mar (Admin › Costes: una oferta = una llamada) y PR. *(pasos en `docs/plan-pruebas-010.md`; navegador de S3-S5 comprobado por Claude el 21-nov)*

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
- [ ] T28 — Cierre de S6: suite verde y PR.
