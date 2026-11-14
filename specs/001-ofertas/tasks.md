---
type: tasks
title: ofertas — Desglose de tareas
description: Tareas pequeñas y comprobables derivadas del plan de la fase 1. Cada una empieza con un test que falla.
tags: [tareas, ofertas]
status: active
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-12 }
verified: { by: human, at: null }
stale_after: null
---

# ofertas — Tareas

- [x] T01 — Taxonomía y esquemas `Auditoria`, `Taxonomia`, `Oferta`, `Fuente`, `CalificacionFuente` · test: casos válidos e inválidos (literal fuera de taxonomía, URL sin https) · cubre: RF-1.1, RF-1.5, RF-1.6
- [x] T02 — Interfaz `Flow` y `PlainFlow` · test: recorre aristas, `run_step`, `pasos()`, arista condicional y `ErrorDePaso` con el nombre del paso · cubre: RF-1.4, RT-12
- [x] T03 — Herramientas `origen_oferta`, `dominio`, `robots` y `normalizar` · test: unitarios con DNS y HTTP simulados · cubre: RF-1.2, RF-1.5, RF-1.7, RT-08
- [x] T04 — Agentes `auditor-oferta`, `clasificador-oferta` y `auditor-fuentes` · test: con la puerta simulada devuelven su esquema; los prompts piden registrar instrucciones · cubre: RF-1.5, RF-1.6, RF-1.7, RT-01, RT-07
- [x] T05 — Flujo `procesar_oferta` · test: fantasma, fraude con cita, salario no publicado, dato sin origen descartado, paso que falla · cubre: RF-1.4, RF-1.5, RF-1.9
- [x] T06 — Flujo `calificar_fuente` · test: LinkedIn/Indeed sin llamar al modelo; robots que prohíbe → no apta · cubre: RF-1.7
- [x] T07 — Consola `flujo listar/correr` con `--paso-a-paso` y `--traza` · test: muestra cada paso y guarda un JSON por paso · cubre: RF-1.12, RT-05
- [x] T08 — Evals `ofertas` (25 casos) y `fuentes` (5 casos) · test: el harness corre el flujo, mide por campo y exige adversarias al 100 % · cubre: RT-11, RT-07 · *medido también con el modelo real el 14-nov-2026: aprobado*
- [x] T09 — Migración 0002 (catálogo común, fuentes, calificaciones, ejecuciones, claves) y semilla · test: tablas, columnas del esquema, RLS de catálogo y de sistema · cubre: RF-1.1, RF-1.9
- [x] T10 — Claves de API y `POST /ofertas` con clave · test: hash, revocación, alcance, tamaño, ritmo e idempotencia · cubre: RF-1.3, RF-1.11
- [x] T11 — Worker con `procesar_oferta` y `calificar_fuente` · test: oferta completa guardada; repetida marcada; error con paso y motivo · cubre: RF-1.4, RF-1.7, RF-1.11
- [x] T12 — Rutas de administración e ingesta (resumen, fuentes, ejecuciones, calificaciones, claves) · test: 403 sin admin; activar sin calificación apta → 409 · cubre: RF-1.1, RF-1.7, RF-1.8, RF-1.10
- [x] T13 — Ingestor sin BD (`horma ingestar`) · test: con API y endpoint simulados entrega N ofertas y cierra la ejecución; arquitectura: no importa BD (contrato de import-linter) · cubre: RF-1.2
- [x] T14 — Dashboard de ingesta y catálogo en la web · test: página solo para admin, JS sin `innerHTML` · cubre: RF-1.8, RF-1.9
- [x] T15 — Consola `fuente calificar` · test: encola por la API y muestra el resultado; `--local` no guarda · cubre: RF-1.7
- [x] T16 — CI, Compose (`ingestor`), `.env.example`, README y spec de sistema · test: CI corre los dos sets; README documenta los comandos · cubre: RF-1.2, RT-11

## Pendiente de la persona (no se puede hacer sin ti)
- Verificar spec, plan y tareas de la fase 1 (siguen en borrador; `verified: null`).

## Hecho por la persona
- Evals con el modelo real (14-nov-2026): `ofertas` y `fuentes` aprobados.
- `ANTHROPIC_API_KEY` como secreto del repositorio en GitHub (14-nov-2026): el CI mide con el modelo real.
- Tu `sub` de Google en `HORMA_ADMINS`; Arbeitnow calificada como apta y activada en el dashboard.
