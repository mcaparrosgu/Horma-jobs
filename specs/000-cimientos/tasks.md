---
type: tasks
title: cimientos — Desglose de tareas
description: Tareas pequeñas y comprobables derivadas del plan. Cada una empieza con un test que falla.
tags: [tareas, cimientos]
status: active
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-12 }
verified: { by: human, at: 2026-11-14 }
stale_after: null
---

# cimientos — Tareas

- [x] T01 — Proyecto Python (`pyproject.toml`, uv, ruff, pytest) y paquete `horma/` · test: `import horma` y `horma --help` · cubre: RF-0.1
- [x] T02 — Contrato de arquitectura (import-linter) · test: falla si algo fuera de `horma.llm` importa `anthropic`, o si un agente importa BD o a otro agente · cubre: RT-02, RT-13
- [x] T03 — Esquemas `OfertaExtraida` y `Origen` · test: valida un caso correcto y rechaza campos inválidos · cubre: RF-0.2
- [x] T04 — Puerta única `completar` con modo simulado y reintento de validación · test: salida corrupta → un reintento → `SalidaInvalida` sin persistir · cubre: RF-0.3, RF-0.11, RT-03
- [x] T05 — Métricas por llamada · test: se registra agente, modelo, tokens, coste, latencia y resultado, y ningún texto · cubre: RF-0.3, RT-06
- [x] T06 — Clase `Agente` y `extractor-oferta` · test: con la puerta simulada devuelve una `OfertaExtraida` y copia las instrucciones embebidas · cubre: RF-0.4, RT-01, RT-07
- [x] T07 — Consola `horma agente correr` · test: entrada en archivo → salida validada en archivo · cubre: RF-0.4, RT-04
- [x] T08 — Harness de evals y 10 fixtures inventados · test: corre los casos, compara campo a campo y escribe la ejecución fechada · cubre: RF-0.7, RT-11
- [x] T09 — Docker Compose y migraciones (tablas, roles `horma_migrador` y `horma_app`) · test: las tablas existen y cada campo del esquema tiene columna · cubre: RF-0.1, RF-0.2
- [x] T10 — Seguridad por filas (RLS) · test: la usuaria B no lee lo de la usuaria A · cubre: RF-0.5, RF-0.10
- [x] T11 — Cola en Postgres y worker con tope de coste y reintentos · test: tope bajo → tarea en `error` con motivo; la carga guarda ids · cubre: RF-0.6, RT-14
- [x] T12 — Acceso con Google OAuth, sesión en cookie segura y CSRF · test: con proveedor simulado, sin sesión o sin CSRF → 401/403 · cubre: RF-0.5
- [x] T13 — `POST /ofertas` y `GET /ofertas` · test: crea la oferta pendiente, encola por id y lista solo las de la usuaria · cubre: RF-0.6, RF-0.9
- [x] T14 — Web plana con CSP y texto escapado · test: cabecera CSP presente y un `<script>` en el texto de una oferta no se ejecuta · cubre: RF-0.9
- [x] T15 — Camino completo de punta a punta · test: oferta pegada → worker con puerta simulada → aparece procesada en la lista · cubre: RF-0.4, RF-0.6, RF-0.9
- [x] T16 — CI (GitHub Actions) y README · test: el flujo corre ruff, import-linter, pytest, eval y escaneo de secretos; README documenta `horma agente correr` y `horma eval correr` · cubre: RF-0.8

## Pendiente de la persona (no se puede hacer sin ti)
- Nada: todo lo que dependía de ti está hecho.

## Hecho por la persona
- Cliente OAuth de Google creado y `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` en `.env`; login real en uso.
- `ANTHROPIC_API_KEY` como secreto del repositorio en GitHub (14-nov): el CI mide con el modelo real.
- `ANTHROPIC_API_KEY` en `.env` (13-nov) y eval real medido (14-nov, set `ofertas` de 25 casos).
