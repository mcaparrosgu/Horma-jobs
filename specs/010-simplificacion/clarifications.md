---
type: clarifications
title: simplificacion — Aclaraciones
description: Las 12 decisiones de la simplificación de Horma (S0), tomadas con Mar a partir de una auditoría externa de producto, UX y arquitectura, antes de escribir la spec 010.
tags: [clarify, simplificacion, ux, costes, arquitectura]
status: active
sources: [../system.md, ../constitution.md, ../002-perfil-recomendacion/spec.md, ../003-candidatura/spec.md, ../005-correcciones-profesor/spec.md, ../008-portada-ofertas/spec.md, ../009-cv-maestro-entrevista/spec.md]
generated: { by: claude-code, at: 2026-11-21 }
verified: { by: human, at: 2026-11-21 }
stale_after: null
---

# simplificacion — Aclaraciones

## Punto de partida
Al probar Horma, Mar vio que es demasiado complejo para la usuaria. Una auditoría externa (21-nov, solo
lectura, base `afcdca0`) contó el recorrido mínimo hasta descargar una candidatura:

| | Hoy | Propuesta |
|---|---|---|
| Pantallas | 6 | 4 |
| Clics | 9 | 4 |
| Esperas | 4 | 3 |
| Conceptos que tiene que entender | 18 (seis de ellos, «CV») | 8 |
| Agentes activos | 13 | 9 |

Comprobado en el código (21-nov):
- Sin un CV base, «Preparar candidatura» da error, y nada lleva a `/cv-base`; la landing no lo menciona.
- El CV estético se guarda y no lo usa ningún flujo: salió de la candidatura en la fase 3 (migración `0007`).
- `HORMA_FLOW_IMPL` vale `langgraph` en `.env`, `.env.example` y la CI, pero el valor por defecto del código
  es `plain` (`config.py:67`).
- Solo la puntuación del catálogo tiene tope diario (0,50 USD, RF-8.5b). Candidaturas, perfil, estilo y
  lectura de URL tienen tope por tarea, pero no por día. Los precios del modelo de `config.py` son estimados.
- `clasificador-respuesta` solo se usa desde la consola y en los evals.

## Preguntas y respuestas
- P1: ¿Sale el CV base del recorrido? → R: **sí**. La candidatura parte del CV maestro («Tu CV completo»).
  Las tablas `cv_base` y `cv_base_versiones` se dejan de escribir; no se borra ningún dato. La calidad se
  comprueba con el eval real `cv`: si no llega al umbral, el CV base vuelve como respaldo.
- P2: ¿Hace falta un CV general para usar fuera de Horma? → R: **sí: «Tu CV completo», en PDF y sin IA**.
  Lo compone el código a partir del perfil. Se ve y se descarga; no se edita: lo que esté mal se corrige en
  el perfil.
- P3: ¿Cuántas pestañas? → R: **tres: Ofertas · Candidaturas · Perfil**. «Añadir oferta» pasa a ser un botón
  dentro de Ofertas que abre una ventana. Admin sigue aparte.
- P4: ¿Qué nombres? → R: **los ocho conceptos de RF-10.2**. «Recomendadas» pasa a llamarse «Ofertas» y «CV
  maestro», «Tu CV completo». «Compatibilidad» es la única palabra para la nota (fuera «nota» y
  «puntuación»). «Hueco» solo nombra periodos sin actividad.
- P5: ¿Puntúa sola en cuanto termina de leer el CV? → R: **no; se queda como está** (RF-8.5: al abrir
  Ofertas si ha pasado 1 h, o al guardar «Qué buscas»). Así no se gasta en usuarias que no vuelven.
- P6: ¿LangGraph? → R: **sí, por defecto en `candidatura`**. El valor por defecto del código pasa a
  `langgraph`, como ya tienen `.env`, la CI y la spec 004. `PlainFlow` se queda en los tests como
  referencia. Los demás flujos siguen lineales.
- P7: ¿Un solo agente por oferta? → R: **sí, con el eval como puerta**. `analizador-oferta` sustituye a
  `extractor-oferta`, `clasificador-oferta` y `auditor-oferta` (de 3 llamadas a 1). SI no llega al umbral
  de `ofertas` y `red-teaming`, **se vuelve a las tres llamadas de hoy**, no a dos.
- P8: ¿Qué forma tiene la entrevista de la 9b? → R: **la sesión de 20-30 minutos que se firmó en la spec
  009** (RF-9.7i), no por tandas. Se puede dejar a medias, como ya dice la spec.
- P9: ¿Audio y valoración en la 9b? → R: **después**. La 9b se hace solo con texto. El audio (Whisper) y el
  `valorador_entrevista` vuelven cuando se mida cuánto se usa la entrevista.
- P10: ¿Se retira el CV estético? → R: **sí, hasta la fase de diseños de CV**. Al subir solo quedan «CV» y
  «Carta». Los ya subidos se conservan en «Documentos subidos».
- P11: ¿Un presupuesto diario único por usuaria? → R: **sí, 1 USD al día, provisional**. Se comprueba en un
  solo sitio, al encolar. Los topes por tarea se quedan como red de seguridad. La cifra definitiva sale del
  estudio de costes, con los precios oficiales del modelo.
- P12: ¿Se aparca `clasificador-respuesta`? → R: **sí**, con su eval `respuestas`. También se aparca
  `generador-cv-base` y se borra la tarea muerta `extraer_oferta`. `clasificador-respuesta` vuelve como
  **mejora próxima de prioridad alta**, junto al aplicador autónomo de ofertas (ver «Fuera de alcance» de la
  spec).

## Además, de la auditoría (aprobado por Mar el 21-nov)
Entran en la spec sin pregunta propia: landing con Google directo; subir el CV al elegir el archivo; avance
en la cabecera; bandeja «Por resolver»; una sola elección de longitud; estado de la candidatura en una sola
etiqueta; quitar los textos internos; arreglar Ofertas en blanco sin perfil; caché de la compatibilidad que
sobreviva a ediciones menores; precios oficiales del modelo; «solo los servicios encolan»; `textos.js`.

## Numeración
La spec 010 es la simplificación. Las antiguas fases 10 (CV y carta ideales, diseños) y 11 (ingesta
programada, vigía de portales) pasan a llamarse 11 y 12.
