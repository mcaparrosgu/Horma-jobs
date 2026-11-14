# Horma

Asistente de búsqueda de empleo: ingiere y audita ofertas de fuentes registradas, construye el perfil de la usuaria a partir de su CV (con el origen de cada dato), recomienda ofertas explicando el porqué y genera un CV y una carta adaptados que ella aprueba antes de enviarlos.

Es una sola aplicación. Los agentes son código Python que se prueba uno a uno desde la consola `horma`.

> Estado: fase 1 (ofertas) construida: catálogo común de ofertas, agentes `auditor-oferta`, `clasificador-oferta` y `auditor-fuentes`, flujos `procesar_oferta` y `calificar_fuente` sobre la interfaz `Flow`, ingestor por API, claves de API y dashboard `/ingesta`. Evals medidas con el modelo real el 14-nov-2026 (ambos sets aprobados); el CI las corre en simulado hasta que `ANTHROPIC_API_KEY` sea secreto en GitHub.

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
5. `docker compose up -d --build` levanta también la API (http://localhost:8000) y el worker.
6. `uv run pytest` (los tests de base de datos necesitan el paso 3), `uv run ruff check .` y `uv run lint-imports`.

### Fase 1: fuentes e ingesta

1. Entra en la web: debajo del catálogo sale tu identificador de Google (`sub`). Ponlo en
   `HORMA_ADMINS` del `.env` y reinicia la API. Ya verás el enlace «Ingesta».
2. En `/ingesta`, califica la web de la fuente (p. ej. `https://www.arbeitnow.com`). Solo una
   calificación APTA permite activarla.
3. Crea una clave de alcance `ingesta`, cópiala (solo se enseña una vez) en `HORMA_CLAVE_INGESTA`
   y arranca el ingestor: `docker compose --profile ingesta up -d`. El ingestor no tiene
   credenciales de la base de datos.
4. Lanza la ingesta desde el dashboard o con `uv run horma ingestar arbeitnow --limite 20`.

## Consola

- `uv run horma agente listar` · `uv run horma agente correr <agente> --entrada x [--salida y]`
  (con `--simulado --respuesta r.json` no llama al modelo).
- `uv run horma flujo listar` · `uv run horma flujo correr procesar_oferta --entrada oferta.md
  --paso-a-paso --traza trazas/` enseña la entrada y la salida de cada paso y guarda la traza.
- `uv run horma ingestar <fuente> [--limite N] [--en-seco]`: `--en-seco` lee la fuente de
  `config/endpoints.json` y enseña las ofertas normalizadas sin entregarlas.
- `uv run horma fuente calificar <url>`: pide la calificación a la API y espera el veredicto.
- `uv run horma eval correr ofertas|fuentes` corre los casos de `evals/<set>/casos/` y deja la
  ejecución en `evals/resultados/`. Con `--simulado` solo prueba el harness: no mide el modelo.
  Sin `--simulado` llama al modelo real y **gasta saldo de Anthropic**.

## Git

Sin commits automáticos y sin coautoría de IA.

## Reglas de agentes

Ver [AGENTS.md](./AGENTS.md): única fuente de verdad.
