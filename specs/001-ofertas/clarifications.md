---
type: clarifications
title: ofertas — Aclaraciones
description: Preguntas abiertas de la fase 1 resueltas con la persona antes de escribir la spec, más los supuestos.
tags: [clarify, ofertas]
status: active
sources: [../system.md, ../000-cimientos/plan.md, ../../docs/Horma v2_ requerimientos por fases.pdf]
generated: { by: claude-code, at: 2026-11-12 }
verified: { by: human, at: null }
stale_after: null
---

# ofertas — Aclaraciones

## Preguntas y respuestas
- P1: En la fase 0 cada oferta pertenece a una usuaria; las que llegan por ingesta o por clave de API no tienen dueña. ¿Catálogo común o por usuaria? → R: **catálogo común**. Cualquier usuaria con sesión lee las ofertas; solo la API (ingesta o clave) y el worker las escriben.
- P2: ¿Quién edita fuentes y lanza ingestas desde el dashboard? → R: **solo administradoras**, por una lista de cuentas de Google en `.env` (`HORMA_ADMINS`).
- P3: ¿Con qué fuentes reales se hace la primera ingesta? → R: **Arbeitnow** (API pública sin clave). Las demás se registran inactivas y pasan por `horma fuente calificar`.
- P4: ¿Se corren los evals con el modelo real? → R: **solo en simulado**. La puerta queda construida y probada con el harness; la medición real la lanza la persona. *Actualizado: la persona la lanzó el 14-nov-2026 y ambos sets aprobaron.*

## Decisiones derivadas
- La regla de RLS de `ofertas` cambia: lectura para cualquier sesión con usuaria; escritura solo en modo sistema (API con clave, ingesta y worker). Los tests de la fase 0 que comprobaban «cada usuaria ve solo sus ofertas» se sustituyen por los del catálogo común.
- `HORMA_ADMINS` guarda el identificador `sub` de Google (Horma solo pide el ámbito `openid`: no conoce el email). La web enseña a cada usuaria su `sub` para poder añadirlo.
- La consola no tiene credenciales de la base de datos: lo que necesita guardar lo hace a través de la API con una clave (RF-1.2 y la regla «solo la API y el worker leen y escriben en Postgres»).

## Supuestos (revisables)
- Taxonomía cerrada inicial en `horma/schemas/taxonomia.py` (sector, familia de puesto, nivel y stack); se ajusta con las primeras ejecuciones reales.
- Las ofertas pegadas en la web por una usuaria también entran al catálogo común (son la misma ruta `POST /ofertas`).
- `evals/ofertas/` pasa de 10 a 25 casos inventados (5 adversarios); `evals/fuentes/` tiene 5 portales inventados (1 adversario).
- Se siembran en `fuentes` Arbeitnow y Adzuna, ambas inactivas: solo se activan con una calificación apta.
