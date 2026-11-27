---
type: tasks
title: matcher-puestos — Desglose de tareas
description: Tareas pequeñas y comprobables de la spec 012 (paso 2 del PRD), en tres bloques — puestos, nota y explicación, y lo que ve la usuaria. Cada una empieza con un test que falla; cada gasto real, con estimación y OK de Mar.
tags: [tareas, matcher, puestos, recomendacion]
status: active
sources: [./plan.md]
generated: { at: 2026-11-25 }
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
- [x] T05 — Puerta por niveles, tope de nivel y genéricos con familia, medidos sobre las respuestas de T03 (0 USD)
  (26-nov: ajenos marcados 0, no marcados 0,98, marcados 0,79, cobertura 0,795, equidad 0; D-038).
  - **Test:** «Controller financiero» citando «Excel» queda fuera; el puesto entero de una experiencia da nivel 1;
    una titulación da nivel 2; «Senior …» no sale para un perfil junior; «Manager» no casa con una oferta de
    otra familia y sí con una sin familia.
- [x] T06 — `relacion` en el clasificador. 🛑 OK al gasto (~0,4-0,7 USD): segunda pasada del set y eval `perfil`
  (26-nov: 0,44 USD; `perfil` aprobado al 100 %; ajenos 0, marcados 0,98, no marcados 0,99, cobertura 0,94,
  equidad 0; 126 puestos nuevos por etiquetar).
- [x] T22 — Léxico y `en_genero` (`tools/lexico_genero.py`). 🛑 Mar repasa el léxico (0 USD; aprobado el 26-nov, D-050).
  - **Test:** la tabla de ejemplos de D-043, incluida «Costurera» sin cambio; ida y vuelta
    `en_genero(a_copia(x), género de x) == x`; sin género, «Camarero/a».
- [x] T23 — `PerfilCiego` y `copia_ciega()` (RF-12.30a y b).
  - **Test:** el esquema tiene exactamente los campos de la lista; al menos 10 gemelas escritas a mano (las del
    set y 5 con secretaria, asistenta, gobernanta y modista) dan el mismo `model_dump_json`; el nombre en una
    descripción, el correo, la URL y el teléfono desaparecen; las fechas y el perfil original no cambian.
- [x] T24 — El clasificador con la copia, puerta y huella de clasificación (RF-12.30f a h). Ejemplos del prompt en «/a».
  - **Test:** el proveedor simulado no recibe el nombre ni «Camarera»; un `dato` «Camarero/a» da nivel 1 y se
    guarda «Camarera»; con género femenino se ve «Camarera» y sin género «Camarero/a»; cambiar el nombre o
    `genero_puestos` no cambia `huella_clasificacion` y añadir una certificación sí; cambiar `genero_puestos`
    reescribe los títulos sin llamar al modelo.
- [x] T25 — Pares irregulares en `variantes_genero` y `canonico` (RF-12.30i).
  - **Test:** «Gobernanta» casa con «Gobernante/a de pisos»; «Actor» con «Actriz»;
    `canonico("Asistenta") != canonico("Asistente")`.
- T26 — Retirada (D-048): los modelos de Horma no admiten `temperature`.
- [x] T27 — Métricas de equidad (sobre las copias) y estabilidad (`--veces 3`).
  - **Test:** una gemela con una palabra fuera del léxico hace fallar la equidad; tres pasadas simuladas
    distintas bajan la estabilidad.
  - 🛑 OK al gasto (~0,5-0,8 USD): 3 pasadas reales del set `puestos` y eval `perfil`.
  - 🛑 Mar fija el umbral de estabilidad (26-nov: 0,50 USD, estabilidad 0,52, `perfil` aprobado; D-052: sin
    umbral y sus puestos, por código). Etiquetados los puestos nuevos (26-nov: 261, kappa 0,75, 53 repasados)
    y el set aprueba: ajenos 0, marcados 0,99, no marcados 1,0, cobertura 0,93, equidad 1,0.
- [x] T07 — Set de títulos de 9a: ~50 pares de sinónimos. 🛑 Mar firma los pares dudosos. Se vuelve a medir
  RF-9.3e; SI la cobertura baja de 0,90, 🛑 se para y se propone la prueba de embeddings (F4-D6). Hecho (26-nov):
  0,58 con texto; se midieron tres vías y entran tabla y modelo (D-053, D-061).
  Set de 202 pares: cumple RF-9.3e; en 80 pares nuevos, cobertura 0,68 y precisión 1,0.
- [x] T07b — Las otras formas que da el modelo (RF-12.4c): agente pequeño, guardadas con las preferencias y pedidas
  en el worker al clasificar y al guardar un puesto escrito a mano. Con T08: «También busco: …» bajo cada puesto
  marcado, sin editar.
  - **Test:** guardar «Peluquera» pide sus formas una vez y la búsqueda las usa; la API las enseña.
- [x] T08 — «Qué buscas»: nivel 1 marcado, nivel 2 sin marcar con su porqué y junior sin experiencia (RF-12.7).
  - **Test:** la API devuelve nivel y porqué; un CV sin experiencia trae marcados los de titulación.
  - **Navegador:** 1280 y 390 px, claro y oscuro (`tests/capturas.js`, 27-nov). El porqué de cada puesto, D-063.
- [x] T09 — Cierre de P: set `puestos` en umbral, suite verde, `specs/index.md` al día y PR. Hecho (27-nov): set en
  umbral y en la CI con las respuestas grabadas (D-064), suite verde; PR #46 fusionado.

### N · Nota y explicación (RF-12.11 a 12.24, 12.31 y 12.32; y RF-12.4e)
- [x] T10 — Eval `recomendacion` a ~60 casos, con orden y pares de equidad (0 USD). 🛑 Mar repasa los casos con más
  de 10 puntos entre etiquetadores y cualquier cambio de una nota esperada existente (RF-12.14).
  Hecho (27-nov): 60 casos (6 de orden y 6 pares de equidad); 6 ofertas repasadas (D-069); ninguna nota anterior cambia.
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
- [ ] T28 — Con T12 y antes de T14: el `matcher` con la copia y sin condiciones (RF-12.31), RF-12.32 en el prompt y
  `huella_compatibilidad` sobre la copia, con una migración que reescriba las huellas guardadas (sin ella se
  vuelve a puntuar todo).
  - **Test:** el proveedor simulado no recibe el nombre, «Camarera» ni las condiciones; cambiar el nombre no
    cambia la huella; la migración conserva las notas.
- [ ] T29 — Con T12: citas contra la copia.
  - **Test:** «encargado/a de turno» existe en la copia y se enseña «encargada de turno»; una cita con el nombre
    de la usuaria no existe y se pide otra vez.
- [ ] T30 — Con T11: pares de RF-12.22 solo para edad, hueco y nacionalidad.
  - **Test:** dos medianas a más de 3 puntos hacen fallar la equidad.
- [ ] T31 — Set de evals de `sinonimos-puestos` (RF-12.4e, D-068), con su harness en simulado. 🛑 Mar fija el umbral.
  🛑 OK al gasto antes de medir con el modelo real; entra en la CI sin gasto.
  - **Test:** una forma que sea otro puesto hace fallar el set.
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

### Cambios pequeños
- [x] 390 px: botones de la portada a todo el ancho, sin «Calificar todas» cuando no hay CV, y `tests/capturas.js` para
  comprobar pantallas. Test: `tests/test_s12_portada_movil_calificar.py`.
- [x] `/favicon.ico` con el cuadrado de la marca. Test: `tests/test_s12_favicon.py`.
- [x] «Ver» un PDF en el móvil: cada página como imagen (`pypdfium2`; prueba M19 de Mar). Test:
  `tests/test_s12_visor_pdf_movil.py`.
- [x] Simetría a 390 px: paneles de Perfil a todo el ancho, ventanas con «Cerrar» junto al título, filas de
  botones en columnas iguales y sin la caja vacía en Candidatura. Test: `tests/test_s12_simetria_movil.py`.
- [x] Iconos de la app instalable (192, 512 y maskable) con el cuadrado de la marca sobre fondo oscuro.
