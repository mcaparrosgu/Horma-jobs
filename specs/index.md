---
type: index
title: Horma — Índice de specs
description: Índice OKF que enlaza todas las specs del proyecto por carpeta.
tags: [indice, sdd]
status: draft
sources: [./constitution.md]
generated: { by: claude-code, at: 2026-11-11 }
verified: { by: human, at: 2026-11-14 }
stale_after: null
---

# Índice de specs

## Transversales
- [Constitución](./constitution.md) — principios y líneas rojas.
- [Spec de sistema](./system.md) — contrato, arquitectura, RT-01…RT-14. Verificada.

## Features (una por fase)
Cada carpeta lleva `clarifications.md`, `spec.md`, `plan.md` y `tasks.md`.
- `000-cimientos/` — fase 0, construida (16 tareas).
- `001-ofertas/` — fase 1, construida y verificada (16 tareas; evals con el modelo real el 14-nov).
- `002-perfil-recomendacion/` — fase 2, cerrada el 15-nov (T01-T23). `recomendacion` queda con `nota` 0,67: antes de usuarias reales, el `matcher` debe pasar su [plan de perfeccionamiento](./002-perfil-recomendacion/spec.md#plan-para-perfeccionar-el-matcher-obligatorio-antes-de-probar-con-usuarias-reales).
- `003-candidatura/` — fase 3, cerrada el 16-nov con el bloque H (simplificar la candidatura); T01-T32, P1-P17.
- `004-langgraph-salida/` — fase 4, construida y fusionada (bloques A a G; T24 firmada el 17-nov). Cerrada también T19 (despliegue): el profesor dijo local con Compose ahora y Vercel después (P6); cerrada el 19-nov.
- `005-correcciones-profesor/` — fase 5, construida y fusionada (T00 y bloques A a H; P1-P18; 36 tareas). Probada por Mar el 19-nov; solo falta enviar el correo a Greenhouse (20-nov). Jobicy y Himalayas están activadas y probadas en local (19-nov). InfoJobs, Greenhouse y Lever esperan las indicaciones del profesor; Greenhouse está construida pero inactiva (NO APTA sin permiso por escrito). El `/ingesta` ya permite activar o desactivar una fuente y editar su `cada_horas`.
- `006-rediseno-2c/` — fase 6, rediseño visual «Editorial» de todas las pantallas (20 tareas: T01-T19 y T17b; bloques A a F). Spec firmada por Mar el 19-nov. Construida (T01-T19 y T17b); prueba manual firmada por Mar el 20-nov. PR de construcción abierto contra `main`.
- `007-ajustes-pantalla/` — fase 7, ajustes de pantalla: «Solo remoto» estricto, ofertas propias sin fecha, segunda persona, nombres enteros, Perfil por bloques, Ingesta y menú Admin más el bloque G de correcciones de la prueba manual: guardado de la guía de estilo, estilo en párrafo corto, desplegables en Perfil, Condiciones simétricas y totales en Costes (21 tareas; P1-P14). Spec firmada por Mar el 20-nov. Cerrada el 20-nov (T01-T21): evals reales en umbral (`ofertas`, `estilo`; `recomendacion` con la `nota` pendiente del plan del `matcher`) y pruebas manuales firmadas por Mar.
- `008-portada-ofertas/` — fase 8: landing y `/entrar`, catálogo común en Admin, «Ver oferta original», «Qué buscas» dentro de Recomendadas, puntuación sin botón con tope provisional de 0,50 USD al día y «Puntuar ahora» por oferta, estado de candidatura y descartar, y avance con % (P1-P11). Aclaraciones, spec, plan y tareas (21, bloques A-F) firmados por Mar el 20-nov; construida el 20-nov (T03-T20); prueba manual (T21) firmada por Mar el 21-nov. RF-8.5 es provisional: hay que mejorarlo antes de usuarias reales.
- `009-cv-maestro-entrevista/` — fase 9: huecos y avisos del CV, entrevista con catálogo de preguntas de recruiter (texto o audio con Whisper local), valoración para entrenar, respuestas como fuente de CV, carta y estilo, puestos recomendados en «Qué buscas» y CV maestro visible (P1-P18). Dividida en dos partes: 9a (CV y puestos) y 9b (entrevista). Aclaraciones, spec, plan y tareas de 9a (19, bloques A-F) firmados por Mar el 21-nov; 9a construida; T10 (evals reales) hecha; faltan T08 (títulos que etiqueta Mar) y T19 (prueba manual de Mar). El plan y las tareas de 9b se escriben al cerrar 9a.
