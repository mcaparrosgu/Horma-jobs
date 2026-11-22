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

Este es el único sitio con el estado de cada fase. El README enlaza aquí; los `tasks.md` solo llevan las casillas.
Número de fase = número de su carpeta, en orden de construcción; lo que aún no tiene spec se nombra por su tema.

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
  orden interno y correcciones. Por bloques ([tasks.md](./010-simplificacion/tasks.md)):
  - **S1-S7: fusionadas** (PR #28 a #31) y probadas por Mar; el repaso a 390 px, más adelante.
  - **S8 (correcciones de la pasada del 22-nov): construida** en `simplificacion-s8` (T38-T49, T54-T67), sin PR.
    El eval `cv` real pasó (22-nov, 33/33, 1,74 USD) y la prueba de cierre Q pasó por DOM/API (T50). Faltan lo visual
    (1280/390 px, claro/oscuro) que mira Mar y el PR.
  - **S9 («Corregir explicación» amplía la información): construida** en `simplificacion-s9` (T51-T53), sin PR.
    Falta T68: migración `0029`, suite con base de datos, navegador y la prueba de Mar (sección R).
  - **S10 (subir varios documentos a la vez): sin spec** (T69). Con ella se cierra la fase 10.

## Lo que viene, en este orden
1. **Fase 11 · Aplicación autónoma y correo** (`011-aplicacion-autonoma/`, sin spec): enviar candidaturas en
   portales dentro de una regla de la usuaria, en modo prueba hasta las fases 12 y 13, y leer las respuestas por
   correo reenviado. Antes, cambiar y firmar la constitución.
2. **Fase 9b · Entrevista por texto** (spec en `009-…`, RF-10.12; sin plan).
3. **Fase 12 · `matcher` y puestos afines** (`012`): el [plan del `matcher`](./002-perfil-recomendacion/spec.md#plan-para-perfeccionar-el-matcher-obligatorio-antes-de-probar-con-usuarias-reales),
   el modelo pequeño para puntuar y el coste de editar el perfil. Espera a una investigación de puestos afines.
4. **Fase 13 · Calidad de CV y carta** (`013`): rúbricas de CV y carta, PDF comprobado, falsos «Dato dudoso»,
   descripciones recortadas por el extractor y huecos genéricos («manejo de ordenador»).
5. **Fase 14 · Ingesta y vigilancia** (`014`): ingesta programada, vigía de portales y fuentes nuevas. Espera a una
   investigación del banco de ofertas.

**Antes de usuarias reales:** gestión del gasto (mejorar RF-8.5 y los avisos de presupuesto), `evals-reales` en la
CI, red-teaming, RGPD y prueba con cinco personas.
