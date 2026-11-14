---
type: spec
title: cimientos — Spec funcional
description: Requisitos funcionales de la fase 0 (cimientos), en notación EARS.
tags: [spec, cimientos]
status: draft
sources: [./clarifications.md, ../system.md]
generated: { by: claude-code, at: 2026-11-12 }
verified: { by: human, at: 2026-11-14 }
stale_after: null
---

# cimientos — Especificación

## Contexto
Una llamada a `extractor-oferta` recorre todo el camino (consola → puerta única → modelo →
Postgres → web) y ese camino queda cubierto por tests, un eval y CI. Esta fase fija la forma de
todo lo que viene después. Los requisitos transversales (RT-xx) están en [system.md](../system.md).

## Requisitos (EARS)
- **RF-0.1** El repositorio DEBERÁ tener `specs/` (constitución y una spec por fase en OKF), `horma/` como paquete instalable, `evals/`, `.env.example` y Docker Compose con API, worker y PostgreSQL.
- **RF-0.2** El sistema DEBERÁ definir en `horma/schemas/` los esquemas Pydantic que entran en esta fase (`OfertaExtraida` y `Origen`) y generar las tablas con migraciones a partir de ellos, con una tabla `origen` aparte referenciada por cada dato.
- **RF-0.3** El sistema DEBERÁ exponer `horma.llm.completar(agente, prompt, entrada, esquema_salida)` con reintentos con retroceso, timeout, validación de salida (RT-03), registro de métricas (RT-06) y un modo simulado para tests.
- **RF-0.4** El sistema DEBERÁ incluir la clase base `Agente` y el agente `extractor-oferta`, ejecutable con `horma agente correr extractor-oferta --entrada oferta.md` (RT-01, RT-04, RT-07).
- **RF-0.5** El sistema DEBERÁ autenticar con Google OAuth 2.0 (verificando el token de Google), usar cookies seguras y CSRF, y aislar los datos por usuaria con roles de base de datos y seguridad por filas (RLS).
- **RF-0.6** El sistema DEBERÁ tener una cola de tareas en PostgreSQL y un worker con reintentos y tope de coste por tarea (RT-14); la carga de la cola DEBERÁ guardar ids, no texto.
- **RF-0.7** El sistema DEBERÁ incluir el harness de evals: `horma eval correr ofertas` lee los fixtures, ejecuta el agente, compara campo a campo y deja una ejecución fechada en `evals/resultados/` (RT-11).
- **RF-0.8** El sistema DEBERÁ tener CI que corra `pytest`, el test de arquitectura (RT-02, RT-13), el eval de `extractor-oferta` con una clave de presupuesto limitado y un escaneo de secretos.
- **RF-0.9** La web DEBERÁ servir HTML, CSS y JavaScript planos desde FastAPI, con texto siempre escapado y CSP estricta, y mostrar la lista de ofertas procesadas.
- **RF-0.10** SI un usuario intenta leer datos de otra usuaria, ENTONCES el sistema DEBERÁ denegar el acceso (probado con un test de RLS).
- **RF-0.11** SI la salida del modelo no valida contra el esquema tras el reintento, ENTONCES el sistema DEBERÁ lanzar `SalidaInvalida` y no persistir nada (RT-03).

## Criterios de aceptación (puerta de salida)
- [x] CI en verde con el eval de `extractor-oferta` sobre 10 fixtures inventados, incluidos casos con instrucciones embebidas (RT-07). Cumplido en simulado y medido con el modelo real el 14-nov-2026 sobre el set `ofertas` ampliado a 25 casos en la fase 1 (aprobado).
- [x] `horma agente correr` y `horma eval correr` documentados en el README.
- [x] Test de RLS pasando (leer datos de otra usuaria falla).
- [x] Métricas de cada llamada al modelo registradas sin guardar texto (RT-06).

## Fuera de alcance
- Ingesta real desde fuentes, perfil, recomendación y candidaturas (fases 1-3).
- LangGraph y PWA (fase 4).
- Auditoría y clasificación de ofertas (fase 1): aquí la oferta se guarda sin ellas.
