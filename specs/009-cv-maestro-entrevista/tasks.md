---
type: tasks
title: cv-maestro-entrevista — Desglose de tareas (9a)
description: Tareas pequeñas y comprobables de la parte 9a. Cada una empieza con un test que falla; las de pantalla se comprueban a 1280 y 390 px, en claro y en oscuro. Las de 9b se escriben al cerrar 9a.
tags: [tareas, perfil, preferencias, agentes, frontend]
status: active
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-21 }
verified: { by: human, at: 2026-11-21 }
stale_after: null
---

# cv-maestro-entrevista — Tareas (9a)

## Forma de trabajo
- **Modelo:** spec, plan y tareas, con Opus; la construcción (B-F), con Sonnet.
- **Rama:** `fase9a-construccion` desde `fase9-spec`, con todos los bloques seguidos. El PR se abre al terminar F.
- **Gasto:** solo T10 (evals de `perfil`) y T19 (prueba manual) llaman al modelo real: se avisa antes con la
  estimación.
- **Tests:** `UV_NO_SYNC=1 uv run pytest`.

### Bloque A · Spec
- [x] T01 — Aclaraciones y spec 009 escritas y aprobadas. *(firmadas por Mar el 21-nov)*
- [x] T02 — Plan y tareas de 9a aprobados. *(firmados por Mar el 21-nov)*
  - **Test:** Mar los lee y los firma (`verified`).

### Bloque B · Datos y herramientas (RF-9.1, RF-9.2, RF-9.3c-d)
- [x] T03 — Esquemas: `Actividad` y `PeriodoCubierto` en el perfil; `puestos`, `puestos_sugeridos` y
  `excluidos` en Preferencias.
  - **Test:** un perfil antiguo sin esas listas se lee; `PeriodoCubierto` no admite texto; `extra="forbid"`.
- [x] T04 — Migración 0021.
  - **Qué se hace:** columnas de `preferencias`; `ofertas.titulo_norm` con su relleno; tablas `avisos_vistos` y
    `ajustes_perfil` con RLS.
  - **Test:** columnas y `CHECK`; `titulo_norm` relleno en las ofertas que ya había; RLS (una usuaria no lee
    ni borra lo de otra).
- [x] T05 — `detectar_huecos`.
  - **Test:** 8 meses → hueco; 4 → no; año suelto no inventa huecos; solapados; voluntariado o periodo cubierto
    tapan el hueco; una entrada sin fechas no cuenta; texto del aviso con meses en castellano.
- [x] T06 — `avisos_perfil` con clave y huella.
  - **Test:** los cinco avisos de RF-9.2; un CV sin correo ni teléfono da aviso y uno con teléfono no; la huella
    cambia si cambia la descripción.
- [x] T07 — `normalizar_titulo` y `buscar_ofertas` con puestos y excluidos.
  - **Test:** «Data Analyst» casa con «Senior Data Analyst (m/f)» y no con «Data Entry»; plurales y guiones;
    un excluido saca la oferta; una oferta de otra familia entra por título; sin puestos ni familias no filtra.
- [x] T08 — Set de títulos reales (RF-9.3e). *(firmada por Mar el 21-nov)*
  - **Qué se hace:** Claude saca ~150 títulos del catálogo con puestos candidatos a
    `tests/fixtures/titulos_puestos.json`; **Mar marca acierto o falso positivo**; test de precisión y
    cobertura.
  - **Test:** precisión ≥ 0,95 y cobertura ≥ 0,90. Si no llega, se ajusta `normalizar_titulo`, no el set.
  - **Estado (21-nov):** hecho. 150 pares etiquetados por mayoría de tres etiquetadores ciegos independientes (no por Mar); `2 passed`. Mar repasa y firma los 6 pares sin unanimidad y los 6 que difieren del código.

### Bloque C · Agentes y flujos (RF-9.1d, RF-9.3)
- [x] T09 — Prompts y flujos.
  - **Qué se hace:** `extractor_perfil` saca `actividades`; `quitar_sensibles` convierte en periodo cubierto la
    que tenga un rasgo personal; el CV maestro añade «Otras actividades»; `clasificador_postulante` devuelve
    8-15 puestos con su dato; el código descarta los que no se citan en el perfil; `preferencias_desde_cv` y
    `_ClasificarPerfil` aplican los puestos sin pisar los de ella.
  - **Test (simulado):** «baja por enfermedad 2019-2020» → periodo cubierto sin texto y fuera del maestro;
    voluntariado en el maestro con su cita; un puesto con un dato que no está en el perfil se descarta; una
    subida nueva no pisa los puestos marcados por ella.
- [x] T10 — Evals de `perfil` con modelo real. *(firmada por Mar el 21-nov)*
  - **Qué se hace:** casos nuevos (voluntariado, baja médica, cuidados, puestos esperados en castellano e
    inglés); avisar del gasto antes.
  - **Test:** evals de `perfil` en umbral; ningún rasgo personal en el perfil ni en los puestos.
  - **Estado (21-nov):** corrida real hecha (0,74 USD): los casos nuevos 15-18 pasan (un fallo suelto de «puestos» en el 15 no se repitió). `10-sin-datos` fallaba también sin los cambios de 9a (deriva del modelo); arreglado por código: un CV sin experiencia, formación ni idiomas siempre pregunta por cada sección (`_perfil_vacio`), y el caso pasa.

### Bloque D · API (RF-9.1c, RF-9.2, RF-9.2d)
- [x] T11 — `GET /api/perfil/avisos`, `PUT /api/perfil/avisos/visto` y `PUT /api/perfil/longitud`.
  - **Test:** huecos y avisos sin los vistos; visto con la misma huella no vuelve al subir el mismo CV; vuelve
    si cambia la causa; elegir longitud oculta el aviso de CV largo; otra usuaria no ve nada ajeno.
- [x] T12 — Otras actividades editables en Mi perfil (API).
  - **Test:** añadir, corregir y borrar una actividad crea versión (RF-2.4); con un rasgo personal se guarda
    como periodo cubierto y avisa.
- [x] T13 — Preferencias con puestos y excluidos en `GET`/`PUT /api/preferencias` y en `opciones`.
  - **Test:** marcar o escribir un puesto pone origen «usuaria»; los sugeridos llegan con su dato.

### Bloque E · Pantallas (RF-9.3b, RF-9.4, RF-9.5)
- [x] T14 — Guía: aviso con dos acciones y aviso con elección de longitud.
  - **Test:** estáticos: las clases existen con tokens; filas nuevas en la tabla de RF-6.4 (spec 006).
- [x] T15 — «Qué buscas»: Área, Puestos y Términos excluidos.
  - **Test:** sugeridos marcados; «Seleccionar todo» y «Quitar selección»; añadir y quitar un excluido;
    «Guardar y buscar» manda los tres grupos.
  - **Navegador:** Recomendadas con «Qué buscas» abierto a 1280 y 390 px, en claro y en oscuro.
- [x] T16 — Perfil: orden de bloques, «Preguntas pendientes y avisos» y «Otras actividades».
  - **Test:** orden de RF-9.5; número en el título; abierto si hay alguno; «Añadir en Mi perfil», «Corregir» y
    «Dar por visto» llevan a su sitio.
- [x] T17 — «Tu CV maestro».
  - **Test:** coincide con `perfiles.cv_maestro`; fecha y versión; «Editar» por sección; sin `innerHTML`.
  - **Navegador:** Perfil entero a 1280 y 390 px, en claro y en oscuro.

### Bloque F · Cierre
- [x] T18 — Coherencia: `specs/index.md`, README, `system.md` si cambia algún RT; en la spec 002, RF-2.8 y
  RF-2.11; en la 007, RF-7.5; en la 008, RF-8.4, marcados como cambiados por la 009.
- [x] T19 — Prueba manual de Mar. *(firmada por Mar el 21-nov)*
  - **Estado (21-nov):** plan recorrido por Mar y firmado.
  - **Qué se hace:** un plan de pruebas manual (gitignorado, retirado) con los criterios de aceptación de 9a; avisar
    del gasto antes; Mar los recorre y firma.
