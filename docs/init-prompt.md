
Sos mi asistente de **inicialización de proyecto**. Vas a dejar el entorno de trabajo listo siguiendo EXACTAMENTE las reglas de abajo.

**Reglas globales, no negociables:**

- **No escribas código de la aplicación todavía.** Solo andamiaje: reglas de agentes, estructura de carpetas, specs, plantillas, config y archivos de entorno.
- **Empezá por el Pre-flight (sección 1) y respetá el gate de Clarify (sección 3).** Son paradas obligatorias: no avances si no las cumpliste.
- Trabajá de forma incremental y contame qué vas creando.
- Todos los **archivos del repo en inglés** (nombres, contenido, comentarios). Hablame a mí en español.
  - Excepción: los identificadores del dominio que fija el documento de requerimientos se mantienen en español (`Oferta`, `Perfil`, `Candidatura`, `horma agente correr`, `extractor-oferta`…). Ver «Notas de adaptación».
- Al final, mostrame el **checklist de verificación** (última sección) marcando cada punto.

**Contexto del proyecto:**

- Nombre: `Horma`
- Descripción: `Asistente de búsqueda de empleo: ingesta y audita ofertas de fuentes registradas, construye el perfil de la usuaria a partir de su CV (con el origen de cada dato), recomienda ofertas con el porqué y genera CV y carta adaptados que ella aprueba antes de enviar. Es una sola app: los agentes son código Python dentro de la web desde la fase 0, se prueban uno a uno desde la consola y la orquestación está escrita para que LangGraph la reemplace en la fase 4 sin tocar ningún agente.`
- Stack: `Python (paquete instalable horma/, uv) · Pydantic (contrato de esquemas) · SDK anthropic (Messages API) detrás de la puerta única horma.llm · FastAPI por capas + HTML/CSS/JS planos (PWA en fase 4) · Typer (consola horma) · PostgreSQL con RLS y cola de tareas + worker · Docker Compose (api, worker, postgres) · LangGraph en la fase 4 · pytest, import-linter, ruff · CI con evals`
- Fuente de requerimientos: [Horma v2: requerimientos por fases](https://claude.ai/artifact/XgsxiP5gLvaR34W8QeqDoj) (11-nov-2026).
- Primer feature: `000-cimientos` (fase 0). Fases siguientes: `001-ofertas`, `002-perfil-recomendacion`, `003-candidatura`, `004-langgraph-salida`.
- `USE_N8N=false`

---

### 1. Pre-flight (idempotencia) — HACÉ ESTO PRIMERO

Antes de crear o modificar **nada**:

1. Inspeccioná el estado actual del directorio: `git status` (si hay repo), y verificá si ya existen `AGENTS.md`, `CLAUDE.md`, `README.md`, `specs/`, `.env`, `.env.example`, `.gitignore`.
2. **Si algún archivo ya existe, NO lo sobrescribas.** Mostrame una lista de lo que encontraste y preguntame cómo seguir para cada caso:
    - **completar solo lo que falta** (merge no destructivo), o
    - **dejar intacto** lo existente y saltarlo.
3. Solo creá archivos **nuevos**, o los que yo autorice explícitamente. Cualquier cambio destructivo (sobrescribir, borrar, mover) requiere mi OK explícito antes.
4. Si el directorio ya estaba inicializado, ajustá el resto de los pasos para **rellenar huecos**, no para rehacer todo.

---

### 2. Reglas de agentes: `AGENTS.md` + `CLAUDE.md`

Creá dos archivos en la raíz. **`AGENTS.md` es la fuente única de verdad** de cómo debe operar cualquier agente de desarrollo en este repo; **`CLAUDE.md` solo apunta a `AGENTS.md`** (sin duplicar reglas).

> Ojo: en Horma, `CLAUDE.md` y `.claude/` son herramientas para **desarrollar** el repo con Claude Code. Los agentes **del producto** viven en `horma/agents/` como código Python, no como prosa en `.claude/`.

**`AGENTS.md`**

```markdown
# Agent operating instructions

These rules apply to ANY AI agent working in this repository (Claude Code, and others).
Project principles live in `specs/constitution.md` (OKF) — read that first; this file is the
operational layer on top of it. System-wide architecture and cross-cutting requirements
(RT-xx) live in `specs/system.md`.

## Golden rules
- Spec-first: never write application code before its spec/plan/tasks exist under
  `specs/NNN-<feature>/`.
- Clarify before specifying: ask open questions and WAIT for human answers before writing a spec.
- TDD: a failing test precedes every implementation task.
- Every product agent ships with its eval set and threshold (`evals/<set>/`).
- Secrets: live only in `.env` (never committed). Document keys in `.env.example`.
- Knowledge artifacts use the Open Knowledge Format (OKF): markdown + YAML frontmatter.

## Product architecture rules (from specs/system.md)
- Product agents are Python modules: `prompt.md` + Pydantic input/output schemas + `run()`.
  No state, no DB or disk access, never call another agent (RT-01, RT-13).
- Only `horma/llm/` imports the Anthropic SDK; every model call goes through
  `horma.llm.completar` (RT-02).
- Agent composition lives only in `horma/flows/`, behind the `Flow` interface (RT-12).
- Only the API and the worker read/write Postgres.

## Workflow
Constitution → Clarify → Spec (EARS) → Plan → Tasks → Implement (TDD) → Validate → Change

## Git
- Do NOT commit unless the human explicitly asks.
- Never add Claude / any AI as co-author or collaborator. No `Co-Authored-By` lines.
  Commits are authored by the human.

## Layout
- `specs/`                 SDD artifacts (OKF)
- `horma/`                 application package (schemas, llm, agents, tools, flows, cli, web)
- `evals/`                 eval fixtures, runner and results
- `tests/`                 unit, architecture, flow and RLS tests
- `config/endpoints.json`  seed for the job-sources table
- `.env` / `.env.example`  environment variables
- `AGENTS.md`              this file — single source of truth for agent behavior
- `CLAUDE.md`              pointer to this file
```

**`CLAUDE.md`**

```markdown
# CLAUDE.md

The operating instructions for this repository are defined in **[AGENTS.md](./AGENTS.md)**.
Read and follow that file. Do not duplicate rules here — `AGENTS.md` is the single source of truth.
```

---

### 3. Spec-Driven Development (SDD) + gate de Clarify

Adoptamos SDD. El flujo es:

> **Constitution → Clarify → Spec → Plan → Tasks → Implement (TDD) → Validate → Change**

Los artefactos se escriben **antes** que el código de la app.

Usamos Spec-anchored. Dividimos en spec de sistema (lo global: `specs/system.md` con el contrato, la arquitectura y los requisitos transversales RT-01…RT-14) y spec de feature (una por fase: `000-cimientos` … `004-langgraph-salida`).

Constitución mínima.

“Cuando un pedido mío contradiga una spec, el pedido gana. Proponé el cambio en la spec y mostramelo antes de tocar código. con mi OK actualizá la spec y regenerá tasks.md.”

Regenerar spec en vez de emparchar.

#### 3.1 Clarify — GATE OBLIGATORIO (antes de escribir cualquier spec)

Antes de redactar `spec.md`, `plan.md` o `tasks.md`:

1. Haceme **3 preguntas puntuales** sobre lo ambiguo del feature `cimientos`: alcance, usuarios/actores, datos, edge cases, restricciones y criterios de aceptación.
   Puntos abiertos del documento de requerimientos que conviene cubrir:
    - Base de datos en desarrollo: Postgres en Docker Compose o Neon (propuesta: Compose para CI y Neon para los entornos compartidos).
    - Identidad mínima de la fase 0: Google OAuth 2.0 o email.
    - Librería del modelo: SDK `anthropic` envuelto en `horma.llm` (propuesta) frente a Claude Agent SDK.
    - Herramientas del repo: `uv`, `Typer`, `import-linter`, `pytest`, `ruff` (propuesta).
    - Ejecución de flujos desde la API: siempre por cola y worker, con flag de desarrollo para correrlos en línea (propuesta).
    - Pendientes de información: perfiles de prueba (cuántos y de qué sectores), fuentes para la primera ejecución de `horma fuente calificar` (EURES, Adzuna, Arbeitnow, The Hub, InfoJobs), diseño de pantallas de fases 2 y 3 (móvil primero).
2. **PARÁ y esperá mis respuestas.** No escribas ningún spec hasta que yo responda.
3. Registrá las preguntas y mis respuestas en `clarifications.md` (frontmatter OKF `type: clarifications`).
4. Si respondo _"seguí con supuestos"_, documentá los **supuestos explícitos** en `clarifications.md` y recién ahí avanzá.

#### 3.2 Estructura de specs

Creá esta estructura (la numeración sigue a las fases del documento de requerimientos, por eso empieza en `000-`):

```
specs/
  constitution.md                 # líneas rojas, reglas y principios del proyecto (transversal)
  system.md                       # spec de sistema: contrato, arquitectura, RT-01…RT-14
  index.md                        # índice OKF que enlaza todos los specs
  000-cimientos/
    clarifications.md             # preguntas del gate de Clarify + respuestas/supuestos
    spec.md                       # requisitos funcionales RF-0.x en notación EARS
    plan.md                       # arquitectura técnica + contratos
    tasks.md                      # tareas granulares y testeables
  001-ofertas/                    # se crean vacías; cada una pasa su propio gate de Clarify
  002-perfil-recomendacion/
  003-candidatura/
  004-langgraph-salida/
```

Convención de carpetas: prefijo numérico incremental (`000-`, `001-`, …) + slug del feature.

`spec.md` usa **notación EARS** (Easy Approach to Requirements Syntax):

- Ubicuo: `The system SHALL <requisito>.`
- Evento: `WHEN <disparador>, the system SHALL <respuesta>.`
- Estado: `WHILE <estado>, the system SHALL <requisito>.`
- Opcional/feature: `WHERE <feature presente>, the system SHALL <requisito>.`
- Condición no deseada: `IF <condición de error>, THEN the system SHALL <respuesta>.`

Usá **exactamente** estas plantillas (cada spec lleva frontmatter OKF; ver sección 4):

**`specs/constitution.md`**

```markdown
---
type: constitution
title: Horma — Project Constitution
description: Non-negotiable principles, red lines, constraints and conventions for this project.
tags: [governance, sdd]
status: draft
sources: [https://claude.ai/artifact/XgsxiP5gLvaR34W8QeqDoj]
generated: { by: claude-code, at: <ISO-8601> }
verified: { by: human, at: null }
stale_after: null
---

# Horma — Constitution

## Principles
- Spec-first: no application code is written before its spec, plan and tasks exist.
- Clarify-first: ambiguities are resolved with the human before specifying.
- Test-Driven: every task ships with a failing test first; every agent ships with an eval.
- Clean boundaries: domain logic stays independent of frameworks, ORM and I/O.
- One app: agents are Python code inside the web app from phase 0, runnable one by one from the console.

## Red lines
- Origin rule: every profile datum and every CV/letter sentence keeps its `origen`;
  without origin it is asked, never invented.
- Job offers, CVs and emails are untrusted text; embedded instructions are logged, never executed.
- Every application needs the user's approval before any sending.
- Never infer or store age, nationality or GDPR art. 9 categories.
- Never use LinkedIn or Indeed as sources.
- Test data is invented until privacy and GDPR are closed; the repo never holds a real person's data.

## Constraints
- Stack: Python (uv) · Pydantic · anthropic SDK behind `horma.llm` · FastAPI + plain HTML/CSS/JS ·
  Typer CLI · PostgreSQL (RLS + task queue) · Docker Compose · LangGraph (phase 4).
- No RAG: no embeddings, no hybrid search.
- All secrets live in `.env` (never committed).

## Conventions
- Specs live under `specs/NNN-<feature>/`; system-wide rules in `specs/system.md`.
- Requirements use EARS notation.
- Knowledge artifacts follow the Open Knowledge Format (OKF).
- Agent behavior is governed by `AGENTS.md`.
```

**`specs/000-cimientos/clarifications.md`**

```markdown
---
type: clarifications
title: cimientos — Clarifications
description: Open questions resolved with the human before writing the spec, plus assumptions.
tags: [clarify, cimientos]
status: draft
sources: []
generated: { by: claude-code, at: <ISO-8601> }
verified: { by: human, at: null }
stale_after: null
---

# cimientos — Clarifications

## Questions & answers
- Q1: <pregunta> → A: <respuesta>

## Assumptions
- <supuesto explícito si se avanzó sin respuesta>
```

**`specs/000-cimientos/spec.md`**

```markdown
---
type: spec
title: cimientos — Functional Spec
description: Functional requirements for the cimientos feature (phase 0), in EARS notation.
tags: [spec, cimientos]
status: draft
sources: [./clarifications.md, ../system.md]
generated: { by: claude-code, at: <ISO-8601> }
verified: { by: human, at: null }
stale_after: null
---

# cimientos — Specification

## Context
One call to one agent (`extractor-oferta`) travels the whole path — console → single gateway →
model → Postgres → web — and that path is covered by tests, an eval and CI. This phase fixes the
shape of everything that follows.

## Requirements (EARS)
- R1. The system SHALL ...   (RF-0.1 … RF-0.9 from the requirements doc)
- R2. WHEN <trigger>, the system SHALL ...
- R3. IF <error condition>, THEN the system SHALL ...

## Acceptance criteria
- [ ] CI green with the `extractor-oferta` eval over 10 fixtures.
- [ ] `horma agente correr` and `horma eval correr` documented in the README.
- [ ] RLS test passing (reading another user's data fails).

## Out of scope
- Real ingestion from sources, profile, recommendation and applications (phases 1-3).
- LangGraph (phase 4).
```

**`specs/000-cimientos/plan.md`**

```markdown
---
type: plan
title: cimientos — Technical Plan
description: Architecture, module boundaries and contracts mapping each requirement.
tags: [plan, cimientos]
status: draft
sources: [./spec.md]
generated: { by: claude-code, at: <ISO-8601> }
verified: { by: human, at: null }
stale_after: null
---

# cimientos — Plan

## Architecture
<capas / módulos / dependencias: horma/schemas, llm, agents, tools, flows, cli.py, web/>

## Contracts
<interfaces, endpoints o comandos CLI; entradas/salidas>

## Requirement → Component map
| Requirement | Component | Notes |
|-------------|-----------|-------|
| R1          |           |       |

## Data model
<entidades (los siete esquemas del contrato + tabla `origen`) y su relación con la DB (Postgres / Neon)>
```

**`specs/000-cimientos/tasks.md`**

```markdown
---
type: tasks
title: cimientos — Task Breakdown
description: Granular, testable tasks derived from the plan.
tags: [tasks, cimientos]
status: draft
sources: [./plan.md]
generated: { by: claude-code, at: <ISO-8601> }
verified: { by: human, at: null }
stale_after: null
---

# cimientos — Tasks

- [ ] T1 — <tarea> · test: <qué verifica> · covers: R1
- [ ] T2 — <tarea> · test: <qué verifica> · covers: R2
```

---

### 4. Formato de las specs: Open Knowledge Format (OKF)

Todos los artefactos de conocimiento (specs, constitution, docs) siguen **OKF** (`https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf`): **markdown plano con frontmatter YAML**, enlazados entre sí con links markdown relativos.

Campos de frontmatter que usamos (ya reflejados en las plantillas de arriba):

- `type` — clasificación del documento (`constitution`, `system`, `clarifications`, `spec`, `plan`, `tasks`, `index`).
- `title`, `description` — humano-legibles.
- `tags` — etiquetas categóricas.
- `status` — `draft` | `active` | `verified` | `deprecated`.
- `sources` — orígenes / documentos de los que deriva (rutas relativas o URLs).
- `generated` — `{ by, at }` metadata de creación.
- `verified` — `{ by, at }` (queda `null` hasta que un humano lo confirme).
- `stale_after` — fecha/condición de caducidad (o `null`).

Reglas OKF:

- Un concepto = un archivo markdown.
- Enlaces entre documentos con links markdown relativos (`[plan](./plan.md)`).
- Generá `specs/index.md` (`type: index`) que liste y enlace todos los specs por carpeta.
- El formato es extensible: podés agregar claves extra al frontmatter sin romper nada.

---

### 5. Variables de entorno (`.env`)

- **Todas** las variables de entorno van en un único archivo `.env` en la raíz.
- `.env` **nunca se commitea** (va en `.gitignore`, ver sección 7).
- Creá también un `.env.example` **sí versionado**, con las mismas claves pero **sin valores** (o con placeholders), para documentar qué necesita el proyecto.

Estructura inicial de claves (ajustala al stack real):

```dotenv
# .env.example  (committed — placeholders only)
# Database
DATABASE_URL=
DIRECT_URL=
NEON_API_KEY=
# Model gateway (horma.llm is the only consumer)
ANTHROPIC_API_KEY=
# Auth (phase 0: Google OAuth 2.0 or email, JWT, secure cookies)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
JWT_SECRET=
# App
APP_ENV=development
LOG_LEVEL=info
# Job sources: one env var per registered source, referenced from the `fuentes` table
# (e.g. ADZUNA_APP_ID=, ADZUNA_APP_KEY=) — add them when each source is activated
# n8n (only if USE_N8N=true) — not used in Horma
# N8N_MCP_TOKEN=
# N8N_BASE_URL=
```

Cargá las variables desde `.env` en el código (`pydantic-settings`). Nunca hardcodees secretos.

---

### 6. Base de datos: Neon (Postgres serverless)

> Decisión abierta en el documento de requerimientos: Postgres en Docker Compose (api, worker, postgres) para desarrollo y CI, y Neon para los entornos compartidos. Confirmalo en el gate de Clarify antes de ejecutar esta sección.

Vamos a usar **Neon** para los entornos compartidos. Hacé lo siguiente:

1. Inicializá Neon en el proyecto:

    ```bash
    npx neon@latest init
    ```

    Seguí el flujo (login / creación de proyecto). Esto scaffoldea la config de conexión.

2. Guardá las connection strings en `.env` (no en el código ni en git):

    - `DATABASE_URL` → conexión **pooled** (host con `-pooler`), para la app.
    - `DIRECT_URL` → conexión **directa** (unpooled), para migraciones/DDL. Formato:

    ```
    postgresql://USER:PASSWORD@HOST/neondb?sslmode=require&channel_binding=require
    ```

3. Verificá la conexión (usando la variable, sin pegar credenciales en el chat):

    ```bash
    psql "$DATABASE_URL"
    ```

4. En el código, mantené la conexión detrás de la capa de infraestructura (`horma/web/repositories/`), separada del dominio — coherente con Clean Architecture / DDD. Los agentes y los flujos nunca tocan la base de datos.

> Si `psql` no está instalado o el token todavía no existe, dejá la variable como placeholder en `.env` / `.env.example` y avisame qué falta; no bloquees el resto del setup.

---

### 7. Git

1. **Inicializá el repo** (`git init`) si no existe. Remoto: `https://github.com/mcaparrosgu/Horma-jobs` (público).
2. **Generá un `.gitignore`** apropiado para el stack. Como mínimo debe incluir:

    ```gitignore
    # Secrets / env
    .env
    .env.*
    !.env.example

    # Python
    __pycache__/
    *.py[cod]
    .venv/
    venv/
    .mypy_cache/
    .pytest_cache/
    .ruff_cache/

    # Neon / DB
    .neon*
    *.sqlite3

    # Evals / traces (may contain model output; fixtures stay versioned)
    trazas/

    # OS / editor
    .DS_Store
    .idea/
    .vscode/

    # Node (si aplica, p. ej. tooling de Neon)
    node_modules/
    ```

3. **No commitees nada por ahora.** Dejá todo en el working tree / staging a mi criterio. No corras `git commit` salvo que yo te lo pida explícitamente.
4. **No agregues a Claude como colaborador ni como co-autor:**
    - No incluyas líneas `Co-Authored-By: Claude ...` ni firmas de asistente en commits.
    - Configurá el repo para que los commits queden a mi nombre.
    - Si en algún momento se agregó un usuario/bot de Claude como **collaborator** del repo remoto, quitalo (o indicame el comando `gh` exacto para hacerlo).

---

### 8. n8n — OPCIONAL (solo si `USE_N8N=true`)

`USE_N8N=false` para Horma: **saltá esta sección** y dejá anotado en el checklist que quedó pendiente.

---

### 9. README de onboarding

Generá un `README.md` (en inglés) que sirva para vos-futuro, colaboradores o alumnos. Debe cubrir:

- **What is this** — Horma: a job-search assistant built as one app; agents are Python code, testable one by one from the `horma` console.
- **How we work (SDD)** — el flujo Constitution → Clarify → Spec → Plan → Tasks → Implement (TDD) → Validate → Change, y qué es cada artefacto/carpeta.
- **Phases** — 0 Cimientos · 1 Ofertas · 2 Perfil y recomendación · 3 Candidatura y seguimiento · 4 LangGraph, calidad y salida; cada fase se cierra con sus evals en verde.
- **Add a new feature** — crear `specs/NNN-<feature>/`, pasar por el gate de Clarify, luego Spec (EARS) → Plan → Tasks.
- **OKF** — una tabla corta con los campos de frontmatter y qué significan.
- **Setup** — copiar `.env` desde `.env.example`, `uv sync`, levantar Postgres (`docker compose up`) o inicializar Neon (`npx neon@latest init`), correr los tests (`pytest`).
- **Console** — `horma agente correr <nombre> --entrada f` y `horma eval correr <set>` (puerta de salida de la fase 0).
- **Git rule** — sin commits automáticos, sin co-autoría de IA.
- **Agent rules** — apuntar a `AGENTS.md` como fuente de verdad.

---

### 10. Verificación final (mostrame este checklist marcado)

- [ ] **Pre-flight** hecho: inspeccioné el directorio y no sobrescribí nada sin tu OK.
- [ ] `AGENTS.md` creado (reglas operativas) y `CLAUDE.md` apuntando a `AGENTS.md`.
- [ ] **Clarify gate** cumplido: te hice preguntas, esperé respuestas y las registré en `clarifications.md`.
- [ ] Estructura `specs/` creada: `constitution.md`, `system.md`, `index.md`, `000-cimientos/` con `clarifications.md`, `spec.md` (EARS), `plan.md`, `tasks.md`, y carpetas `001`–`004` vacías.
- [ ] Todos los specs tienen frontmatter **OKF** válido (YAML) y enlaces relativos correctos.
- [ ] `.env` creado (no versionado) y `.env.example` versionado con las mismas claves.
- [ ] Base de datos: decisión Compose/Neon registrada; `DATABASE_URL` (pooled) y `DIRECT_URL` (directa) en `.env`; conexión verificada (o pendiente anotado).
- [ ] `.gitignore` generado e ignorando `.env` (pero **no** `.env.example`).
- [ ] Repo `git init` hecho; **sin commits**; sin co-autoría/colaborador de Claude.
- [ ] `README.md` de onboarding generado.
- [ ] n8n: marcado como pendiente (`USE_N8N=false`).
- [ ] No se escribió código de la aplicación.

Cuando termines, resumime qué quedó listo y qué necesita input mío (tokens, decisiones de arquitectura, etc.).

---

### Notas de adaptación (plantilla v2 → Horma)

Diferencias entre la plantilla genérica y el documento de requerimientos, resueltas así:

| Punto | Plantilla | Documento Horma | Cómo queda |
|---|---|---|---|
| Numeración de specs | `001-{{FEATURE_SLUG}}` | `000-cimientos` … `004-langgraph-salida` + `system.md` | Se sigue el documento |
| Base de datos | Neon | Postgres en Docker Compose; Neon como opción abierta | Compose para dev/CI, Neon para compartidos (a confirmar en Clarify) |
| Idioma del repo | Todo en inglés | Identificadores del dominio en español (`Oferta`, `horma agente correr`) | Inglés salvo esos identificadores (a confirmar en Clarify) |
| `CLAUDE.md` | Puntero a `AGENTS.md` | Convenciones para desarrollar con Claude Code | Compatible: puntero, y las convenciones en `AGENTS.md` |
| n8n | Opcional | No se menciona | `USE_N8N=false` |
