---
type: clarifications
title: cimientos — Aclaraciones
description: Preguntas abiertas resueltas con la persona antes de escribir la spec, más los supuestos.
tags: [clarify, cimientos]
status: active
sources: [https://claude.ai/artifact/XgsxiP5gLvaR34W8QeqDoj]
generated: { by: claude-code, at: 2026-11-11 }
verified: { by: human, at: 2026-11-11 }
stale_after: null
---

# cimientos — Aclaraciones

## Preguntas y respuestas
- P1: Base de datos y entorno. ¿Postgres en Docker Compose para desarrollo y CI, y Neon solo para entornos compartidos (propuesta), o Neon en todo? → R: Postgres en Docker Compose.
- P2: Identidad mínima de la fase 0. ¿Google OAuth 2.0 o email (con JWT y cookies seguras)? → R: Google OAuth 2.0.
- P3: Perfiles de prueba y fuentes. ¿Cuántos perfiles inventados y de qué sectores? ¿Qué fuentes entran en la primera pasada de `horma fuente calificar` (EURES, Adzuna, Arbeitnow, The Hub, InfoJobs)? → R: las que sugiera el asistente y perfiles variados (sin concretar número ni sectores).

## Propuestas por defecto (si se responde «sigue con supuestos»)
- SDK `anthropic` envuelto en `horma.llm` (frente a Claude Agent SDK).
- Herramientas: `uv`, `Typer`, `import-linter`, `pytest`, `ruff`.
- Flujos desde la API siempre por cola y worker, con flag de desarrollo para ejecutarlos en línea.
- Diseño de pantallas de las fases 2 y 3 (primero móvil): se pospone a esas fases.

## Decisiones derivadas
- Variables de entorno: `POSTGRES_*` y `DATABASE_URL` para Compose; `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` y `SESSION_SECRET` para el acceso. Se eliminan `DIRECT_URL` y `NEON_API_KEY`.
- Constitución, `.env.example`, README e índice actualizados con P1 y P2.

## Supuestos
- Fuentes de la primera pasada de `horma fuente calificar`: las cinco candidatas (EURES, Adzuna, Arbeitnow, The Hub, InfoJobs); se descartan las que no superen la calificación.
- Perfiles de prueba: 5 perfiles inventados de sectores variados (p. ej. hostelería, sanidad, tecnología, administración, comercio), elegidos por el asistente.
- Neon queda fuera de la fase 0 (solo Compose); se reconsidera para entornos compartidos.
