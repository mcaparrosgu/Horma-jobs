---
type: tasks
title: matcher-puestos — Desglose de tareas
description: Tareas pequeñas y comprobables de la spec 012 (paso 2 del PRD), en tres bloques — puestos, nota y explicación, y lo que ve la usuaria. Cada una empieza con un test que falla; cada gasto real, con estimación y OK de Mar.
tags: [tareas, matcher, puestos, recomendacion]
status: active
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-25 }
verified: { by: human, at: 2026-11-25 }
stale_after: null
---

# matcher-puestos — Tareas

El estado está en [specs/index.md](../index.md); aquí solo van las casillas.

## Forma de trabajo
- **Ramas:** `matcher-p`, `matcher-n` y `matcher-v`, un PR cada una y en ese orden.
- **Gasto:** solo en las tareas con 🛑 de gasto. Estimación antes y OK de Mar ([plan](./plan.md), Costes).
- **Tests:** `$env:UV_NO_SYNC=1; $env:PRESUPUESTO_DIARIO_USD='1.0'; uv run pytest`.

### Spec
- [x] T01 — Aclaraciones, spec, plan y tareas, firmados por Mar (25-nov).

### P · Puestos (RF-12.1 a 12.10)
- [x] T02 — Set `puestos`: 12 CV difíciles nuevos y el harness con sus métricas, en simulado.
  - **Test:** con respuestas simuladas, cada métrica da lo esperado; un puesto «ajeno» marcado hace fallar el set.
- [x] T03 — 🛑 OK al gasto (~0,1 USD). Pasada real del `clasificador_postulante` actual; respuestas guardadas (26-nov: 40 llamadas, 0,05 USD).
- [x] T04 — Etiquetado ciego (tres etiquetadores) e imprescindibles. 🛑 Mar repasa lo que no tiene unanimidad
  (26-nov: 296 puestos, kappa 0,77, 53 repasados; D-037).
- [ ] T05 — Puerta por niveles, tope de nivel y genéricos con familia, medidos sobre las respuestas de T03 (0 USD).
  - **Test:** «Controller financiero» citando «Excel» queda fuera; el puesto entero de una experiencia da nivel 1;
    una titulación da nivel 2; «Senior …» no sale para un perfil junior; «Manager» no casa con una oferta de
    otra familia y sí con una sin familia.
- [ ] T06 — `relacion` en el clasificador. 🛑 OK al gasto (~0,4-0,7 USD): segunda pasada del set y eval `perfil`.
- [ ] T07 — Set de títulos de 9a: ~50 pares de sinónimos. 🛑 Mar firma los pares dudosos. Se vuelve a medir
  RF-9.3e; SI la cobertura baja de 0,90, 🛑 se para y se propone la prueba de embeddings (F4-D6).
- [ ] T08 — «Qué buscas»: nivel 1 marcado, nivel 2 sin marcar con su porqué y junior sin experiencia (RF-12.7).
  - **Test:** la API devuelve nivel y porqué; un CV sin experiencia trae marcados los de titulación.
  - **Navegador:** 1280 y 390 px, claro y oscuro.
- [ ] T09 — Cierre de P: set `puestos` en umbral, suite verde, `specs/index.md` al día y PR.

### N · Nota y explicación (RF-12.11 a 12.24)
- [ ] T10 — Eval `recomendacion` a ~60 casos, con orden y pares de equidad (0 USD). 🛑 Mar repasa los casos con más
  de 10 puntos entre etiquetadores y cualquier cambio de una nota esperada existente (RF-12.14).
- [ ] T11 — Harness: `--veces 3`, variación por caso, `orden`, `equidad`, `citas` y el revisor, en simulado.
  - **Test:** un par invertido hace fallar `orden`; dos notas de un par a más de 3 puntos hacen fallar `equidad`;
    el revisor simulado detecta una explicación sembrada que no se apoya en su cita.
- [ ] T12 — Prompt del `matcher` (franjas, sin nombrar instrucciones, citas literales) y `verificar_citas` con un
  reintento.
  - **Test:** una cita inventada se pide una vez más; si vuelve a fallar, la explicación se retira y la nota se
    conserva; una tanda con una oferta sin resultado la deja «sin puntuar».
- [ ] T13 — `convertir_cv` ignora el texto invisible.
  - **Test:** un PDF y un DOCX con una instrucción en blanco o de tamaño 0 no la devuelven en el texto.
- [ ] T14 — 🛑 OK al gasto (~0,8-1 USD). Una ejecución real entera; después, solo los casos que fallan
  (🛑 OK a cada tanda, ~0,1-0,3 USD), hasta que el `matcher` llegue.
- [ ] T15 — 🛑 OK al gasto (~2,4-3 USD). Puerta: 3 ejecuciones seguidas con el modelo mayor.
- [ ] T16 — 🛑 OK al gasto (~0,15-0,3 USD). 3 ejecuciones con el modelo pequeño. 🛑 Mar decide F1-E6 (D-NNN).
- [ ] T17 — `recomendacion` de vuelta en `evals-reales`. Cierre de N: suite verde, `specs/index.md` al día y PR.

### V · Lo que ve la usuaria (RF-12.25 a 12.29)
- [ ] T18 — Veredicto en palabras y línea de condiciones, con el orden de empate. Primero en la guía.
  - **Test:** 70 da «Muy compatible» y 69 «Compatible»; con sueldo mínimo marcado, una oferta sin sueldo dice «No
    dice el sueldo» y conserva su nota; a igual nota, la que cumple todo va antes.
  - **Navegador:** lista y detalle de Ofertas, 1280 y 390 px, claro y oscuro.
- [ ] T19 — La nota corregida manda en su lista, con su motivo y «Quitar mi nota»; texto de ayuda de RF-10.15e.
  - **Test:** corregir de 75 a 40 cambia orden, rango y veredicto; la corrección sigue tras una versión nueva del
    perfil; «Quitar mi nota» devuelve el 75. Ninguna llamada al modelo.
  - **Navegador:** 1280 y 390 px, claro y oscuro.
- [ ] T20 — Landing revisada: promete solo lo que funciona.
- [ ] T21 — Cierre del paso. 🛑 Revisión de Mar sobre 20 recomendaciones y prueba manual (sección en
  `docs/plan-pruebas-manuales.md`); `specs/index.md`, PRD y pauta al día; PR.
