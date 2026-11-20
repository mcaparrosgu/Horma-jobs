---
type: clarifications
title: cv-maestro-entrevista — Aclaraciones
description: Preguntas abiertas de la fase 9 (huecos y avisos del CV, entrevista con catálogo de preguntas de recruiter, respuestas por audio, valoración, estilo, puestos recomendados y CV maestro visible) y sus respuestas, antes de escribir la spec.
tags: [clarify, perfil, entrevista, estilo, preferencias, agentes]
status: draft
sources: [../system.md, ../constitution.md, ../002-perfil-recomendacion/spec.md, ../005-correcciones-profesor/spec.md, ../007-ajustes-pantalla/spec.md, ../008-portada-ofertas/spec.md]
generated: { by: claude-code, at: 2026-11-21 }
verified: null
stale_after: null
---

# cv-maestro-entrevista — Aclaraciones

## Punto de partida
Mar pidió estos cambios en su listado del 20-nov (fase 9: CV maestro y entrevista).

Comprobado en el código (21-nov):
- Al subir un CV fuente, el flujo `perfilar` extrae, verifica el origen, quita datos sensibles, clasifica y compone
  el CV maestro. Las «preguntas pendientes» ya existen (datos que faltan, ambiguos o contradictorios), pero **no
  se detectan huecos de tiempo** ni avisos de calidad.
- Las preguntas pendientes se guardan dentro de cada versión del perfil. Una subida nueva rehace el perfil desde
  cero: **lo respondido no evita que se vuelva a preguntar**.
- No hay entrevista ni ningún agente que pregunte.
- La guía de estilo sale solo de los CV y las cartas subidos, y se analiza una vez.
- «Qué buscas» solo tiene las 19 familias de la taxonomía y la búsqueda compara la familia exacta: no mira el
  título del puesto ni sinónimos.
- El CV maestro (`perfiles.cv_maestro`) no se ve en ninguna pantalla.
- Perfil no guarda correo ni teléfono.

## Preguntas y respuestas
- P1: ¿Qué detecta Horma al subir el CV? → R: **huecos de tiempo y avisos de calidad**.
- P2: ¿Cómo se detectan los avisos? → R: **reglas por código y además un agente** con criterio de recruiter.
- P3: ¿Desde cuánto es un hueco? → R: **6 meses** sin trabajo ni estudios.
- P4: ¿Qué forma tiene la entrevista? → R: **preguntas guiadas**, una a una, respondidas **por escrito o por audio**.
  Accesibilidad (personas sordas, ciegas…) y otros idiomas oficiales de España: a mejoras futuras.
- P5: ¿Cómo se pasa la voz a texto? → R: **Whisper libre en el worker de Horma**: sin terceros ni coste por minuto.
  La usuaria ve el texto y lo corrige antes de guardarlo; el audio no se guarda.
- P6: ¿Qué se hace con las respuestas? → R: se guardan aparte, por usuaria, y **nunca se vuelven a preguntar**.
  La forma de usarlas la cambia P15.
- P7: ¿Cómo entran en el estilo? → R: **como fuente marcada «entrevista»**: aportan personalidad y expresiones; el
  registro lo siguen marcando CV y cartas. Al terminar la entrevista se reanaliza el estilo solo si la usuaria no
  ha editado la guía; si la editó, se le ofrece con un botón.
- P8: ¿Dónde está la entrevista? → R: un bloque **«Tu entrevista»** en Perfil que **sustituye a Preguntas
  pendientes** y lo reúne todo (datos que faltan, huecos, avisos y preguntas de recruiter). Aparece al terminar
  el CV maestro, es voluntaria y se puede dejar a medias.
- P9: ¿Qué efecto tienen los puestos recomendados? → R: **amplían**: entra a puntuar la oferta cuya familia
  coincide o cuyo título contiene un puesto marcado. Hay que afinarlo para no colar ofertas que no son.
- P10: ¿Qué se afina? → R: **la coincidencia del título** (frase completa normalizada, nunca palabras sueltas,
  con términos excluidos por la usuaria) y **una medición con títulos reales** del catálogo y un umbral.
- P11: ¿Quién sugiere los puestos? → R: **el clasificador del perfil**, en la misma llamada.
- P12: ¿Cómo se ve el CV maestro? → R: **bloque de solo lectura** en Perfil, con formato, fecha y versión, y
  «Editar» por sección hacia Mi perfil. No se edita el texto.
- P13: ¿Uno o dos agentes para avisos y preguntas? → R: **uno solo**, el entrevistador.
- P14: ¿Cuántas entrevistas y cómo se eligen las preguntas? → R: los huecos y sus motivos son distintos en cada
  persona, así que hay un **catálogo amplio de preguntas de recruiter** (100-150, etiquetadas por situación,
  revisado y firmado por Mar) y el agente **elige las que encajan** con cada persona y adapta la redacción, sin
  inventar preguntas. Los huecos se preguntan de forma neutra, con «Prefiero no contarlo». Una entrevista
  inicial; seguimiento solo al subir otro CV; «Contar algo más» siempre disponible; respuestas editables; topes
  de audio.
- P15: ¿Las respuestas pasan al perfil? → R: **no**. La entrevista sirve sobre todo para conocer la
  personalidad, las soft skills y los logros conseguidos gracias a ellas, para personalizar cartas y CV y para
  entrenar entrevistas. Las respuestas son **una fuente más**: el redactor elige qué usar según la oferta; la
  usuaria no marca nada. Sustituye a la parte de P6 que llevaba las respuestas al perfil. Las preguntas de datos
  (fechas que faltan, contradicciones) siguen actualizando el perfil como hoy.
- P16: ¿Qué recibe para entrenar? → R: **una valoración al terminar** la entrevista, corta y por respuesta (qué
  funciona y cómo mejorarla: situación, acción, resultado). Puede reescribir la respuesta.

- P17 (21-nov, tras leer el resumen del borrador): ¿una fase o dos? → R: **dos partes**. 9a: huecos, avisos
  por reglas, puestos recomendados y CV maestro visible. 9b: entrevista, audio, valoración y uso de las
  respuestas. Cada parte tiene su plan, sus tareas, su prueba manual y su PR. En 9a, los huecos y avisos
  se ven en el bloque de preguntas pendientes; en 9b pasan a «Tu entrevista».

## Fuera de alcance (decidido en el Clarify)
- Accesibilidad específica para personas sordas o ciegas en la entrevista (P4).
- Entrevista en otros idiomas oficiales de España (P4).
- Simulacro de entrevista para una oferta concreta (P16).
