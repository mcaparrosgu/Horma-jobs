# Horma

Asistente de búsqueda de empleo: ingiere y audita ofertas de fuentes registradas, construye el perfil de la usuaria a partir de su CV (con el origen de cada dato), recomienda ofertas explicando el porqué y genera un CV y una carta adaptados que ella aprueba antes de enviarlos.

Es una sola aplicación. Los agentes son código Python que se prueba uno a uno desde la consola `horma`.

> Estado: andamiaje listo; aún no hay código de la aplicación. La fase 0 espera el gate de Clarify.

## Cómo trabajamos (SDD)

Desarrollo guiado por specs: los artefactos se escriben antes que el código.

**Constitución → Clarify → Spec (EARS) → Plan → Tareas → Implementación (TDD) → Validación → Cambio**

| Artefacto | Qué es |
|---|---|
| `specs/constitution.md` | Principios y líneas rojas |
| `specs/system.md` | Spec de sistema: contrato, arquitectura, RT-01…RT-14 |
| `specs/NNN-<feature>/clarifications.md` | Preguntas del gate de Clarify y sus respuestas |
| `…/spec.md` | Requisitos en notación EARS |
| `…/plan.md` | Arquitectura técnica y contratos |
| `…/tasks.md` | Tareas pequeñas y comprobables |

## Fases

0. **Cimientos** (`000-cimientos`)
1. **Ofertas** (`001-ofertas`)
2. **Perfil y recomendación** (`002-perfil-recomendacion`)
3. **Candidatura y seguimiento** (`003-candidatura`)
4. **LangGraph, calidad y salida** (`004-langgraph-salida`)

Cada fase se cierra con sus evals en verde.

## Añadir un feature

1. Crear `specs/NNN-<feature>/` (prefijo numérico incremental + slug).
2. Pasar por el gate de Clarify (`clarifications.md`).
3. Spec (EARS) → Plan → Tareas.

## OKF

Las specs son markdown con frontmatter YAML (Open Knowledge Format).

| Campo | Significado |
|---|---|
| `type` | Clase de documento (`spec`, `plan`, `tasks`…) |
| `title`, `description` | Texto legible |
| `tags` | Etiquetas |
| `status` | `draft` · `active` · `verified` · `deprecated` |
| `sources` | Documentos u orígenes de los que deriva |
| `generated` | Quién y cuándo lo creó |
| `verified` | Quién y cuándo lo confirmó (`null` hasta que una persona lo haga) |
| `stale_after` | Caducidad (o `null`) |

## Puesta en marcha

Pendiente de la fase 0; previsto:

1. `cp .env.example .env` y rellenar valores.
2. `uv sync`
3. `docker compose up` (Postgres) o `npx neon@latest init` (Neon).
4. `pytest`

## Consola

Puerta de salida de la fase 0 (aún no implementada):

- `horma agente correr <nombre> --entrada f`
- `horma eval correr <set>`

## Git

Sin commits automáticos y sin coautoría de IA.

## Reglas de agentes

Ver [AGENTS.md](./AGENTS.md): única fuente de verdad.
