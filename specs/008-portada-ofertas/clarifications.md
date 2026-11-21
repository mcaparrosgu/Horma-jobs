---
type: clarifications
title: portada-ofertas — Aclaraciones
description: Preguntas abiertas de la fase 8 (landing, oferta original, «Qué buscas» dentro de Recomendadas, puntuación sin botón, estado de candidatura, descartar y avance con %) y sus respuestas, antes de escribir la spec.
tags: [clarify, frontend, landing, recomendadas, candidaturas, worker]
status: active
sources: [../system.md, ../constitution.md, ../002-perfil-recomendacion/spec.md, ../005-correcciones-profesor/spec.md, ../006-rediseno-2c/spec.md, ../007-ajustes-pantalla/spec.md]
generated: { by: claude-code, at: 2026-11-20 }
verified: { by: human, at: 2026-11-20 }
stale_after: null
---

# portada-ofertas — Aclaraciones

## Punto de partida
Mar pidió estos cambios en su listado del 20-nov y en la prueba manual de la fase 7 (P14 de la 007).

Comprobado en el código (20-nov):
- `/` enseña, con sesión, el catálogo común (las 200 últimas ofertas de todas las fuentes, sin filtrar ni
  puntuar) con un menú propio, sin la cabecera común. Sin sesión, solo «Entrar con Google». Tras el login,
  `/auth/google/callback` lleva siempre a `/`.
- Ningún endpoint devuelve el texto original de una oferta (`texto_crudo`). Recomendadas enlaza la URL en el
  título; las ofertas pegadas no tienen URL.
- Preferencias y los filtros de Recomendadas son lo mismo: filtrar en Recomendadas hace `PUT /api/preferencias`
  y sobrescribe lo guardado. Guardar Preferencias no lanza ninguna búsqueda.
- «Recomendar» puntúa hasta 150 ofertas por pulsación (5 tandas de 30; unos 0,09 USD por tanda) y guarda todo
  al final: si la tarea falla o pasa su tope, no se guarda ninguna tanda.
- La pantalla deduce el avance del contador «sin puntuar» y deja de sondear a los 90 s. `tareas` no tiene
  progreso ni hay endpoint de estado; al cambiar de página, nada lo retoma.
- `matches` no tiene estado ni «descartada»; Recomendadas no consulta `candidaturas`. Solo puede haber una
  candidatura viva por oferta, y cerrarla es definitivo.
- La guía de la fase 6 tiene plegable y un diálogo (el visor de CV de Perfil), pero no barra de progreso.

## Preguntas y respuestas
- P1: Sin botón «Recomendar», ¿cuándo puntúa Horma? → R: **al abrir Recomendadas o al cambiar «Qué buscas»**,
  solo si hay ofertas sin nota y la última puntuación empezó hace más de 1 h; cambiar «Qué buscas» se salta
  la hora. Tope de **0,50 USD al día por usuaria**. Solo gasta si la usuaria entra.
- P2: ¿Qué se guarda y qué es vista? → R: separación limpia. **«Qué buscas»** (se guarda, vuelve a buscar y
  puntuar): puestos, sector, contrato, nivel, país, idiomas, solo remoto, solo con salario y sueldo mínimo.
  **Vista** (gratis, no va al servidor; este navegador la recuerda): nota mínima y máxima, orden y estado.
- P3: ¿Hasta dónde se juntan Recomendadas y Candidaturas? → R: **dos pestañas**. Cada oferta de Recomendadas
  enseña el estado de su candidatura con un enlace a ella, y «Descartar», que la oculta y se puede deshacer
  desde la vista «Descartadas». Candidaturas sigue igual.
- P4: ¿Y si la oferta tiene una candidatura abierta? → R: **sin «Descartar»**; se cierra desde la candidatura,
  como hoy. Así «Descartar» siempre se puede deshacer.
- P5: ¿Cómo se ve la oferta original? → R: **en una ventana encima** (como el visor de CV), con el texto tal
  como entró y «Abrir en la web de origen» si hay URL. En Recomendadas y en el detalle de cada candidatura.
- P6: Landing y entrada → R: `/` explica qué hace Horma y sus servicios; arriba a la derecha, «Crear cuenta» y
  «Entrar», que llevan a `/entrar` con Google. Con sesión, `/` y la vuelta de Google van a **Recomendadas**, o
  a Perfil si aún no hay perfil. Otras formas de entrar: fuera de la fase (tocan la constitución).
- P7: ¿Qué se hace con el catálogo común? → R: pasa a **Admin › Catálogo**, solo para administradoras. Para la
  usuaria quedan Recomendadas (lo que encaja con lo que busca) y Candidaturas (lo que prepara).
- P8: ¿Dónde se ve el avance con %? → R: **en la pantalla de cada trabajo** (Recomendadas, Añadir oferta, la
  candidatura), y se retoma al volver a ella. Las notas aparecen por tandas. Sin aviso en la cabecera.
- P9: ¿Quién escribe el texto de la landing? → R: borrador de Claude, solo con lo que Horma hace hoy; Mar lo
  corrige al firmar la spec.

## Revisión de la spec (20-nov)
- P10: Una oferta sin nota no puede quedarse esperando a la próxima tanda → R: **«Puntuar ahora»** en cada
  oferta sin nota: puntúa solo esa al momento. Funciona siempre, también con el tope del día, hasta 30 sueltas
  al día (unos 0,015 USD cada una; más cara que en tanda porque el perfil se envía entero cada vez).
- P11: ¿Cómo se gestiona el gasto por usuaria? → R: Mar no lo tiene claro y pide asesoramiento más adelante;
  **de momento**, 0,50 USD al día para las tandas y 30 sueltas al día. Anotado en las mejoras futuras.
