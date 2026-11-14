---
type: plan
title: cimientos — Plan técnico
description: Arquitectura, contratos y modelo de datos que cubren cada requisito de la fase 0.
tags: [plan, cimientos]
status: draft
sources: [./spec.md, ../system.md]
generated: { by: claude-code, at: 2026-11-12 }
verified: { by: human, at: 2026-11-14 }
stale_after: null
---

# cimientos — Plan

## Arquitectura
Se crea el esqueleto de `horma/` de [system.md](../system.md), pero solo con lo que usa la fase 0:

```
horma/
  schemas/    oferta.py (OfertaExtraida), origen.py
  llm/        gateway.py (completar), metricas.py, simulado.py
  agents/     base.py, registry.py, extractor_oferta/ (prompt.md, schemas.py, agent.py)
  cli.py      agente correr · eval correr
  web/        main.py, routers/, services/, repositories/, models/, migrations/, queue/, auth/, static/
evals/        ofertas/casos/<id>/{entrada.md, esperado.json}, resultados/ (el ejecutor es horma/evals.py)
tests/        unitarios (gateway simulado), arquitectura, RLS, worker
```

- **Camino de una oferta:** la usuaria pega el texto en la web → `POST /ofertas` lo guarda como `pendiente` y encola una tarea con el id → el worker lanza `ExtractorOferta.run` por la puerta única → guarda `OfertaExtraida` y sus `origen` → la web la lista.
- **Capas web:** routers → servicios → repositorios (SQLAlchemy). Solo los repositorios tocan la base de datos; los agentes y `horma.llm` no.
- **Persistencia:** SQLAlchemy + Alembic. Los esquemas Pydantic son la fuente de verdad; un test comprueba que cada campo del esquema tiene su columna.
- **Docker Compose:** `postgres`, `api` y `worker` (misma imagen, sin root; el puerto de Postgres no se publica fuera del entorno local).

## Contratos
**Consola**
- `horma agente correr <nombre> --entrada f [--salida f] [--simulado]`
- `horma eval correr <set> [--solo caso]`

**Puerta única** — `completar(agente, prompt, entrada, esquema_salida, modelo)`: salida estructurada del SDK de Anthropic validada con Pydantic; reintento con retroceso y timeout; un reintento extra con el error de validación y, si falla, `SalidaInvalida`. Con `--simulado` devuelve la respuesta de un fixture sin llamar al modelo.

**API**
| Ruta | Qué hace |
|---|---|
| `GET /auth/google/login`, `GET /auth/google/callback`, `POST /auth/logout` | Acceso con Google OAuth 2.0; verifica el token de Google y abre sesión en cookie segura |
| `POST /ofertas` | Con sesión y CSRF: guarda el texto y encola la tarea |
| `GET /ofertas` | Lista las ofertas de la usuaria con su estado |
| `GET /` | Página plana (HTML/CSS/JS) con la lista; texto siempre escapado y CSP estricta |

**OfertaExtraida** (campos de la fase 0; cada valor extraído se enlaza a un `origen`): `titulo`, `empresa`, `ubicacion`, `remoto`, `contrato`, `salario` (mínimo, máximo, moneda), `idiomas`, `requisitos`, `fecha_publicacion`, `url`, `instrucciones_embebidas[]`. Lo que no aparezca en el texto queda vacío; nunca se infiere.

**Origen**: `id`, `entidad`, `entidad_id`, `campo`, `fragmento` (cita literal del texto de la oferta).

## Requisito → componente
| Requisito | Componente | Notas |
|---|---|---|
| RF-0.1 | Estructura del repo, `pyproject.toml` (uv), `docker-compose.yml`, `.env.example` | CI y herramientas: `ruff`, `pytest`, `import-linter` |
| RF-0.2 | `horma/schemas/`, `web/models/`, migraciones Alembic | Test esquema ↔ columnas |
| RF-0.3 | `horma/llm/` | RT-02, RT-03, RT-06 |
| RF-0.4 | `agents/base.py`, `agents/extractor_oferta/`, `cli.py` | RT-01, RT-04, RT-07 |
| RF-0.5 | `web/auth/`, roles de BD, políticas RLS | Ver «Modelo de datos» |
| RF-0.6 | `web/queue/` y `worker.py` | `SELECT … FOR UPDATE SKIP LOCKED`; RT-14 |
| RF-0.7 | `horma/evals.py`, `cli.py` | Umbral inicial: ≥ 0,9 por campo (a confirmar con las primeras ejecuciones) |
| RF-0.8 | `.github/workflows/ci.yml` | Escaneo de secretos con `gitleaks` |
| RF-0.9 | `web/static/`, `web/routers/`, cabeceras CSP | |
| RF-0.10 | `tests/test_rls.py` | Dos usuarias; la segunda no lee lo de la primera |
| RF-0.11 | `llm/gateway.py` | Test con salida corrupta simulada |

## Modelo de datos
| Tabla | Campos principales | RLS |
|---|---|---|
| `usuarias` | `id`, `google_sub`, `creada_en` | Cada usuaria ve solo su fila |
| `ofertas` | `id`, `usuaria_id`, `texto_crudo`, `estado` (`pendiente`/`procesada`/`error`), `motivo_error`, campos de `OfertaExtraida` | `usuaria_id = usuaria actual` |
| `origen` | ver arriba, más `usuaria_id` | `usuaria_id = usuaria actual` |
| `tareas` | `id`, `tipo`, `entidad_id`, `estado`, `intentos`, `coste_acumulado`, `tope_coste`, `motivo_error` | `usuaria_id = usuaria actual` |
| `llm_llamadas` | `id`, `agente`, `modelo`, `tokens_entrada`, `tokens_salida`, `coste`, `latencia_ms`, `resultado`, `creada_en` | Sin texto, solo métricas |

**Roles:** `horma_migrador` (propietario, aplica migraciones) y `horma_app` (sin superusuario ni `BYPASSRLS`; API y worker). Cada transacción fija `app.usuaria_id` y las políticas RLS comparan con ese valor. Dos funciones `SECURITY DEFINER` cubren lo que necesita ver más allá de una usuaria: `obtener_o_crear_usuaria(sub)` (login) y `reclamar_tarea()` (el worker toma la siguiente tarea y después trabaja ya bajo la RLS de su dueña).

## Decisiones del plan (revisables)
- `ofertas` lleva `usuaria_id` en la fase 0 para poder probar RLS; la fase 1 revisará si las ofertas pasan a ser compartidas.
- `POST /ofertas` con clave de API (ingesta) llega en la fase 1; aquí solo con sesión.
- Variables nuevas en `.env.example`: `HORMA_FLUJO_EN_LINEA` (flag de desarrollo para ejecutar sin cola), los topes de coste y de reintentos por tarea, los dos roles de BD y `POSTGRES_PORT` (5434, para no chocar con otros Postgres locales). Las URL usan `127.0.0.1` (con `localhost` Windows prueba antes IPv6 y la conexión tarda).
- Solo se guardan los datos de la oferta que se pueden localizar literalmente en su texto (RT-08); el resto se descarta. `titulo` es obligatorio: si no se localiza, su origen es la primera línea.
- Tope de coste: se comprueba tras cada intento fallido; un intento correcto se guarda siempre. Sin credenciales de Google la API arranca y el login responde 503.
