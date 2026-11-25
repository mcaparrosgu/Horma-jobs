---
type: tasks
title: aplicacion-autonoma — Desglose de tareas
description: Tareas pequeñas y comprobables de la parte 1 de la spec 011 (paso 1 del PRD) — medición de destinos y mejoras pequeñas. Cada una empieza con un test que falla; las de pantalla se comprueban a 1280 y 390 px, en claro y en oscuro.
tags: [tareas, envio, medicion, frontend]
status: draft
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-25 }
verified: { by: null, at: null }
stale_after: null
---

# aplicacion-autonoma — Tareas (parte 1)

El estado está en [specs/index.md](../index.md); aquí solo van las casillas.

## Forma de trabajo
- **Ramas:** `envio-a` y `mejoras-m`, una por bloque y un PR cada una. Primero A.
- **Gasto:** 0 USD. Ninguna tarea llama al modelo ni envía nada.
- **Tests:** `UV_NO_SYNC=1 uv run pytest`.

### Spec
- [ ] T01 — Spec, plan y tareas de la parte 1, firmados por Mar (`verified`).

### A · Medición de destinos (RF-11.1)
- [ ] T02 — `portales.json` y `resolver_destino`.
  - **Test:** direcciones de ejemplo de cada portal dan su canal; LinkedIn e Indeed dan «no
    automático»; InfoJobs y WTTJ dan su canal; una redirección se sigue; ninguna petición es distinta de `GET`.
- [ ] T03 — Medición en consola y en Admin.
  - **Test:** con un catálogo de fixtures, la tabla cuenta bien portal, ofertas y «exige cuenta»; sin sesión
    de admin, la API responde 403.
  - **Navegador:** Admin a 1280 y 390 px, claro y oscuro.
- [ ] T04 — Cierre de A. 🛑 Mar lee la medición del catálogo real y se anota en la hoja de ruta como decisión; PR.

### M · Mejoras pequeñas (RF-11.25 a 11.28)
- [ ] T05 — El aviso «Hemos quitado un dato personal» se ve.
  - **Test:** un CV con un dato que Horma no guarda devuelve el aviso en la API y la pantalla lo pinta.
- [ ] T06 — Calificar una fuente que responde 403 da «no apta» con motivo.
  - **Test:** con un 403 simulado, la calificación termina sin error y guarda el motivo.
- [ ] T07 — Botones de archivo con una sola norma, resaltado simétrico en «Añadir oferta» y barras sin borde.
  - **Navegador:** Ofertas, Perfil y la ventana «Añadir oferta» a 1280 y 390 px, claro y oscuro.
- [ ] T08 — Barra de rango de compatibilidad, primero en la guía.
  - **Test:** el mínimo no pasa del máximo; el filtro da las mismas ofertas que las dos casillas; se maneja
    con el teclado.
  - **Navegador:** 1280 y 390 px, claro y oscuro.
- [ ] T09 — Cierre de M. 🛑 Prueba manual de Mar; `specs/index.md` al día; PR.
