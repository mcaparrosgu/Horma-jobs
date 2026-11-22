---
type: index
title: Horma — Índice de specs
description: Índice OKF que enlaza todas las specs del proyecto por carpeta, con el estado real de cada fase.
tags: [indice, sdd]
status: draft
sources: [./constitution.md]
generated: { by: claude-code, at: 2026-11-11 }
verified: { by: human, at: 2026-11-14 }
stale_after: null
---

# Índice de specs

Este es el único sitio con el estado detallado de cada fase. El README solo lo resume.

## Transversales
- [Constitución](./constitution.md) — principios y líneas rojas.
- [Spec de sistema](./system.md) — contrato, arquitectura, RT-01…RT-14. Verificada.

## Features (una por fase)
Cada carpeta lleva `clarifications.md`, `spec.md`, `plan.md` y `tasks.md`. Los requisitos que la spec 010
sustituyó llevan en su spec una línea que apunta a ella.

Formato: carpeta — qué es. **Estado.**
- `000-cimientos/` — base, contrato y `extractor-oferta`. **Construida (16 tareas).**
- `001-ofertas/` — fuentes, ingesta y auditoría de ofertas. **Construida y verificada; evals reales el 14-nov.**
- `002-perfil-recomendacion/` — perfil desde el CV y recomendación. **Cerrada el 15-nov.** El `matcher` tiene
  `nota` 0,67: antes de usuarias reales, su [plan de perfeccionamiento](./002-perfil-recomendacion/spec.md#plan-para-perfeccionar-el-matcher-obligatorio-antes-de-probar-con-usuarias-reales).
- `003-candidatura/` — CV y carta adaptados y seguimiento. **Cerrada el 16-nov con el bloque H (T01-T32, P1-P17).**
- `004-langgraph-salida/` — LangGraph, calidad, PWA y salida. **Fusionada; T24 firmada el 17-nov.** Despliegue
  local con Compose; Vercel, después (P6).
- `005-correcciones-profesor/` — CV maestro, ofertas propias, estilo y fuentes nuevas. **Fusionada y probada por
  Mar el 19-nov; falta el correo a Greenhouse.** Jobicy y Himalayas activas; Greenhouse, Remotive, Adzuna e
  InfoJobs inactivas.
- `006-rediseno-2c/` — rediseño visual «Editorial». **Fusionada; prueba de Mar firmada el 20-nov.**
- `007-ajustes-pantalla/` — ajustes de pantalla. **Fusionada (PR #24); cerrada el 20-nov.**
- `008-portada-ofertas/` — landing, catálogo, puntuación sin botón y avance con %. **Fusionada (PR #25); prueba
  firmada el 21-nov.** RF-8.5 es provisional: mejorarlo antes de usuarias reales.
- `009-cv-maestro-entrevista/` — 9a (huecos, avisos, puestos sugeridos) y 9b (entrevista). **9a fusionada
  (PR #26) y firmada el 21-nov. 9b sin plan:** se hará solo con texto (RF-10.12).
- `010-simplificacion/` — 4 pantallas y 4 clics, candidatura sin CV base, un agente por oferta, 1 USD al día,
  orden interno y correcciones tras la prueba (S1-S7). **S1-S7 fusionadas (PR #28 a #31; S7 cerrada por Mar el
  22-nov). Cerrada: pruebas de Mar hechas; el repaso a 390 px, más adelante.** **S8 (correcciones de la pasada del 22-nov): construida (T39-T49) en la rama `simplificacion-s8`, sin PR; falta la prueba de Mar.** Detalle en
  [tasks.md](./010-simplificacion/tasks.md#estado-22-nov).

## Lo que viene (sin spec todavía)
- **9b:** la entrevista, solo con texto (RF-10.12).
- **Mejoras próximas, prioridad alta:** aplicador autónomo de ofertas (antes hay que cambiar la constitución) y
  leer el correo con `clasificador-respuesta` desaparcado (spec 010, «Fuera de alcance»).
- **Fase 11:** CV y carta ideales, plantillas de CV y CV estético.
- **Fase 12:** ingesta programada y vigía de portales.
- **Antes de usuarias reales:** el plan del `matcher` y mejorar RF-8.5.
