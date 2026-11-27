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
El número de una spec es su nombre fijo: no indica el orden de construcción.

## Transversales
- [PRD](./prd.md) — qué se construye y por qué: objetivos, requisitos y fuera de alcance. **Firmado por Mar el 25-nov.** Cada spec nueva cita los RF, NFR y US del PRD que desarrolla.
- [Constitución](./constitution.md) — principios y líneas rojas.
- [Spec de sistema](./system.md) — contrato, arquitectura, RT-01…RT-19 (RT-15 a RT-19, de ingesta, añadidos el 25-nov).

## Features (una por fase)
Cada carpeta lleva `clarifications.md`, `spec.md`, `plan.md` y `tasks.md`. Los requisitos que la spec 010
sustituyó llevan en su spec una línea que apunta a ella.

Formato: carpeta — qué es. **Estado.**
- `000-cimientos/` — base, contrato y `extractor-oferta`. **Construida (16 tareas).**
- `001-ofertas/` — fuentes, ingesta y auditoría de ofertas. **Construida y verificada; evals reales el 14-nov.**
- `002-perfil-recomendacion/` — perfil desde el CV y recomendación. **Cerrada el 15-nov.** El `matcher` tiene
  `nota` 0,67: se perfecciona en la spec 012 (paso 2 del [PRD](./prd.md)), antes de usuarias reales.
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
  (PR #26) y firmada el 21-nov. 9b sin construir y retirada:** la entrevista se especifica de nuevo en la spec 016.
- `010-simplificacion/` — 4 pantallas y 4 clics, candidatura sin CV base, un agente por oferta, 1 USD al día,
  orden interno y correcciones. Por bloques ([tasks.md](./010-simplificacion/tasks.md)):
  - **S1-S7: fusionadas** (PR #28 a #31) y probadas por Mar; el repaso a 390 px, más adelante.
  - **S8 (correcciones de la pasada del 22-nov): fusionada en `main`** (PR #34, 23-nov; T38-T49, T54-T67).
    El eval `cv` real pasó (22-nov, 33/33, 1,74 USD) y la prueba de cierre Q pasó por DOM/API (T50). Visual de Mar
    (1280/390 px, claro/oscuro) hecho y firmado (23-nov).
  - **S9 («Corregir explicación» amplía la información): fusionada en `main`** (PR #35, 23-nov; suite verde, R1-R9 por
    DOM/API). Visual de Mar hecho y firmado (23-nov).
  - **S10 (subir varios documentos a la vez): fusionada en `main`** (PR #36, 23-nov; T70-T74, probada por DOM/API). Visual de Mar hecho y firmado (23-nov, T75). **Fase 10 cerrada.**

## Pendiente
Qué es cada una, por qué y en qué orden se construye: [PRD](./prd.md), sección 4. La tabla va por número de spec.

| Spec | Qué | PRD | Estado |
|---|---|---|---|
| `011-aplicacion-autonoma/` | Parte 1: medición de destinos y mejoras pequeñas. Partes 2 y 3 (envío y correo; envío real): se especifican al llegar su paso | US-001, US-007 · RF-001 a 005, RF-016 | **Parte 1 fusionada (PR #44, 25-nov; T01-T09; la lectura por URL se retoma al volver a Ofertas (T08f); T05 arreglada tras la prueba de Mar: la edición a mano de una experiencia no vigilaba el dato personal; la barra tras borrar un CV dice «Actualizando tu perfil»; tras la segunda prueba de Mar: la barra de avance nunca parece parada (T08g), el aviso de dato personal sale al subir un CV (T08h), los cuadros de texto no se ensanchan (T08i) y la barra de la lectura por URL se ve al cerrar la ventana (T08j); y, por decisión de Mar: una URL ya añadida no se vuelve a leer (T08k), una sola barra al añadir una oferta (T08l), el filtro de datos personales también al rehacer el perfil (T08m) y el borrado de ofertas caducadas con notas (T08n); tercera prueba de Mar: M12a a M18 funcionan, M17 a trompicones (la barra parecía congelada al volver de otra pestaña); tras ella: el visor de documentos ocupa la ventana (T08o), «Mostrar» tiene «Añadidas por mí» (T08p, D-033), «Más recientes» ordena por la llegada a Horma (T08q, D-034), «Por URL» se abre vacío (T08r) y la barra avanza según lo que suele tardar cada tarea y cuenta el tiempo fuera (T08s, D-035); cuarta prueba de Mar: M17 y M19 a M22 bien, a 1280 y 390 px)** (paso 1). La spec del 23-nov, anterior al PRD, está archivada como insumo |
| `012-matcher-puestos/` | `matcher` y puestos afines | US-002 · RF-006, RF-007 | **Firmada el 25-nov y en construcción** (paso 2; bloque P, rama `matcher-p`: T02 a T06; copia ciega añadida, D-043 a D-052; T22 a T27; set `puestos` en umbral; T07 y T07b hechas, D-053, D-061 y D-062; quedan T08 y T09; además, cambios pequeños del 26-nov: portada a 390 px, favicon, iconos, simetría a 390 px, «Ver» un PDF en el móvil y `tests/capturas.js`) |
| `013-calidad-cv-carta/` | Calidad de CV y carta, con PDF comprobado | US-004 · RF-008, RF-009 | **Firmada el 26-nov (aclaraciones, spec, plan y tareas; D-054 a D-060), sin construir** (paso 3) |
| `014` | Ingesta programada, conectores, ritmo (RT-15 a RT-19) y vigilancia | US-005 · RF-010, RF-011 | **Sin spec.** Agregación de ofertas públicas en alcance (PRD, 7.1; 25-nov). Investigación del banco de ofertas (F5) entregada y decidida (25-nov). Espera a la prueba práctica |
| `015` | Privacidad y cuenta (RGPD y Configuración) | US-003 · RF-012, RF-013 | **Sin spec** |
| `016` | Entrevista por texto (sustituye a la parte 9b de la 009) | US-008 · RF-014 | **Sin spec** |
| `017` | Gasto por usuaria (sustituye a RF-8.5 y RF-10.9d) | US-006 · RF-015 | **Sin spec;** espera a su investigación |

**Antes de usuarias reales, además:** `evals-reales` en la CI, red-teaming y prueba con cinco personas.
