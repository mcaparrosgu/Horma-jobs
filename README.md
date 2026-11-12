# Horma

Asistente de búsqueda de empleo: ingiere y audita ofertas de fuentes registradas, construye el perfil de la usuaria a partir de su CV (con el origen de cada dato), recomienda ofertas explicando el porqué y genera un CV y una carta adaptados que ella aprueba antes de enviarlos.

Es una sola aplicación. Los agentes son código Python que se prueba uno a uno desde la consola `horma`.

> Estado: fase 0 (cimientos) construida: puerta única al modelo, agente `extractor-oferta`, consola, evals, Postgres con RLS, cola y worker, acceso con Google y web mínima. Pendiente para cerrarla: credenciales de Google y clave de Anthropic (ver «Puesta en marcha»).

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

1. `cp .env.example .env` y rellenar: contraseñas de Postgres (`POSTGRES_PASSWORD`, `HORMA_MIGRADOR_PASSWORD`, `HORMA_APP_PASSWORD`), las dos URL de base de datos, `SESSION_SECRET`, `ANTHROPIC_API_KEY` y las credenciales de Google OAuth (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`; URI de redirección `http://localhost:8000/auth/google/callback`). Sin las de Google la web arranca, pero nadie puede entrar.
2. `uv sync`
3. `docker compose up -d postgres` (Postgres local en el puerto 5434; Neon queda fuera de la fase 0).
4. `uv run alembic upgrade head` (migraciones con el rol `horma_migrador`).
5. `docker compose up -d` levanta también la API (http://localhost:8000) y el worker.
6. `uv run pytest` (los tests de base de datos necesitan el paso 3), `uv run ruff check .` y `uv run lint-imports`.

## Consola

Puerta de salida de la fase 0:

- `uv run horma agente listar`
- `uv run horma agente correr extractor-oferta --entrada oferta.md [--salida salida.json]`
  (con `--simulado --respuesta r.json` no llama al modelo).
- `uv run horma eval correr ofertas` corre los 10 casos de `evals/ofertas/casos/` y deja la ejecución en
  `evals/resultados/`. Con `--simulado` solo prueba el harness: no mide el modelo.

## Git

Sin commits automáticos y sin coautoría de IA.

## Reglas de agentes

Ver [AGENTS.md](./AGENTS.md): única fuente de verdad.
