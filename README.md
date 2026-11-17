# Horma

Asistente de búsqueda de empleo: ingiere y audita ofertas de fuentes registradas, construye el perfil de la usuaria a partir de su CV (con el origen de cada dato), recomienda ofertas explicando el porqué y genera un CV y una carta adaptados que ella aprueba antes de enviarlos.

Es una sola aplicación. Los agentes son código Python que se prueba uno a uno desde la consola `horma`.

> Estado: fase 1 (ofertas) construida: catálogo común de ofertas, agentes `auditor-oferta`, `clasificador-oferta` y `auditor-fuentes`, flujos `procesar_oferta` y `calificar_fuente` sobre la interfaz `Flow`, ingestor por API, claves de API y dashboard `/ingesta`. Evals medidas con el modelo real el 14-nov-2026 (ambos sets aprobados); el CI las corre con el modelo real (`ANTHROPIC_API_KEY` es secreto del repositorio desde esa fecha).

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

### Fase 2: perfil y recomendación

1. `uv run alembic upgrade head` aplica la migración 0003; `docker compose up -d --build` monta el
   volumen `horma_archivos` (los CV subidos, solo en la API).
2. Entra en la web: en `/cv-base` subes tu CV (PDF, DOCX o Markdown); en `/perfil` respondes lo que
   falte; en `/preferencias` eliges los filtros (grupos de más de 2 casillas con «Seleccionar todo» y «Quitar selección»); en `/recomendadas` ves las ofertas con su nota.
3. Para probarlo sin web: `horma flujo correr perfilar` y `horma recomendar` (ver Consola).
4. Puerta de salida: `horma eval correr perfil`, `cv-base` y `recomendacion` con el modelo real
   (tope de 1 USD por ejecución).

### Fase 3: candidatura y seguimiento

1. `uv run alembic upgrade head` aplica la migración 0006 (candidaturas, historial y versiones de CV base).
2. En `/recomendadas`, «Preparar candidatura» crea la candidatura (si la oferta ya tuvo una cerrada, avisa y pide confirmar); el worker elige el CV base y
   redacta CV y carta. En `/candidaturas` las ves por estado: revisas, editas, apruebas, descargas
   los PDF y sigues el proceso (enviada, entrevista, cerrada). Cada CV base guarda su historial en `/cv-base`.
3. Para probarlo sin web: `horma flujo correr candidatura` y `horma flujo correr clasificar_respuesta`
   (ver Consola).
4. Puerta de salida: `horma eval correr cv` y `respuestas` con el modelo real (tope de 1 USD, solo de construcción).

### Fase 4 (código completo; falta despliegue, T19): pausa, calidad y salida
1. `uv run alembic upgrade head` aplica la migración 0008 (PDF guardados, señales de entrada, alertas y las
   tablas donde LangGraph guarda la pausa).
2. `HORMA_FLOW_IMPL=langgraph` en `.env` activa el flujo con pausa: el worker prepara CV y carta y se para
   antes de `entregar`; al aprobar se reanuda y los PDF quedan fijos. Con `plain` (valor por defecto del
   código) todo funciona como en la fase 3, y los PDF se generan al descargar.
3. Web instalable (PWA): manifest, iconos y `/sw.js` (guarda solo `/static/*`, nunca `/api/*`) y una
   página «Sin conexión». `/salud` responde sin datos.
4. Límites de ritmo por minuto en `.env`: `LIMITE_LOGIN_POR_MINUTO` (por IP), `LIMITE_CV_POR_MINUTO` y
   `LIMITE_CANDIDATURAS_POR_MINUTO` (por usuaria; crear y reintentar comparten contador). Al pasarse, 429.
5. Perfil de producción: copia `.env.produccion.example` a `.env.produccion`, rellénalo y ejecuta
   `docker compose --env-file .env.produccion -f docker-compose.yml -f docker-compose.prod.yml up -d`.
   Solo Caddy publica puertos (80 y 443, HTTPS); con `HORMA_DOMINIO=localhost` usa su CA interna. Con
   `APP_ENV=produccion` salen HSTS y `Permissions-Policy` y la API no arranca con secretos cortos, vacíos
   o de ejemplo, ni con `GOOGLE_REDIRECT_URI` sin https. El despliegue en un servidor espera al profesor (T19).
6. Observabilidad: `/costes` (solo `HORMA_ADMINS`) muestra coste y errores por día, agente y modelo, sin datos
   personales. Las alertas (`ALERTA_GASTO_DIA_USD`, `ALERTA_TASA_ERRORES`, `ALERTA_MIN_LLAMADAS`,
   `ALERTA_INTERVALO_MIN`) salen en `/costes`, en el log y, con `SMTP_HOST`, `SMTP_*` y `ALERTAS_CORREO`, por
   correo. `LOG_LEVEL` se aplica en la API y el worker.
7. Guardarraíles: la entrada se vigila por código (marca, no bloquea) y el set `evals/red-teaming/` debe pasar
   al 100 %. La revisión de cada prompt frente a las líneas rojas está en `docs/revision-lineas-rojas.md`.
8. **Antes de abrir Horma a usuarias reales:** el `matcher` debe pasar su plan de perfeccionamiento
   (`specs/002-perfil-recomendacion/spec.md`); hoy su `nota` mide 0,67 y la recomendación está fuera de
   `evals-reales`.

## Consola

- `uv run horma agente listar` · `uv run horma agente correr <agente> --entrada x [--salida y]`
  (con `--simulado --respuesta r.json` no llama al modelo).
- `uv run horma flujo listar` · `uv run horma flujo correr procesar_oferta --entrada oferta.md
  --paso-a-paso --traza trazas/` enseña la entrada y la salida de cada paso y guarda la traza.
- `uv run horma ingestar <fuente> [--limite N] [--en-seco]`: `--en-seco` lee la fuente de
  `config/endpoints.json` y enseña las ofertas normalizadas sin entregarlas.
- `uv run horma fuente calificar <url>`: pide la calificación a la API y espera el veredicto.
- `uv run horma flujo correr perfilar --usuaria ana --entrada cv.pdf [--paso-a-paso --traza trazas/]`
  (también `.docx` y `.md`): construye el perfil en local y no guarda nada; `--usuaria` solo
  nombra el CV en la traza.
- `uv run horma recomendar ana --rango 40-100 [--ofertas catalogo.json]`: puntúa el catálogo con el
  perfil de prueba `evals/perfil/perfiles/ana.json` (`--perfil` para otro) y enseña la lista. Sin
  `--ofertas` pide el catálogo común a `GET /api/catalogo` con `HORMA_CLAVE_INGESTA`.
- `uv run horma agente correr extractor-perfil|clasificador-postulante|generador-cv-base|matcher
  --entrada x.json`: cada agente nuevo por separado.
- `uv run horma flujo correr candidatura --usuaria ana --oferta <id> [--aprobar] [--ofertas catalogo.json]
  [--paso-a-paso --traza trazas/]`: prepara CV y carta en local con la usuaria de prueba
  `evals/cv/usuarias/ana` y una oferta del catálogo (sin `--ofertas`, de `GET /api/catalogo`); no guarda nada.
  Se para en la pausa; con `--aprobar` sigue con `entregar` y, con `--traza`, guarda `cv.pdf` y `carta.pdf`.
- `uv run horma flujo correr clasificar_respuesta --entrada r.json`: `r.json` = `{"texto": "…",
  "estado_actual": "enviada"}`; enseña la etiqueta y la transición propuesta.
- `uv run horma agente correr redactor-cv|redactor-carta|juez-candidatura|clasificador-respuesta
  --entrada x.json`: los agentes de la fase 3, cada uno por separado.
- `uv run horma eval correr cv|respuestas`: los evals de la fase 3 (`--simulado` solo prueba el harness).
- `uv run horma eval correr ofertas|fuentes` y, de la fase 2, `horma eval correr perfil`,
  `horma eval correr cv-base` y `horma eval correr recomendacion` corren los casos de
  `evals/<set>/casos/` y dejan la ejecución en `evals/resultados/`. Con `--simulado` solo prueban
  el harness: no miden el modelo. Sin `--simulado` llaman al modelo real y **gastan saldo de
  Anthropic**; `--tope-coste` (1 USD por defecto) detiene el eval al superarlo y lo deja anotado.
  Los umbrales viven en `evals/umbrales.json` (no se rebajan desde la consola; `cv` exige además
  cobertura ATS media ≥ 0,75). `--flujo plain|langgraph` elige la implementación de `candidatura`.
- CI: `calidad` corre tests, estilo y todos los evals en simulado en cada push; `evals-reales` mide el
  modelo (langgraph, 1 USD por set; `recomendacion` queda fuera hasta mejorar el `matcher`) en cada PR a
  `main` y a mano, y falla si falta `ANTHROPIC_API_KEY`. `main` está protegida: solo se cambia con PR y
  con `secretos`, `calidad` y `evals-reales` en verde.
- `uv run horma eval importar-correccion --archivo caso.json`: enseña una corrección de la usuaria
  (se exporta desde la pantalla de recomendadas) y, solo si confirmas, la copia a
  `evals/recomendacion/casos/`. Nada entra en los evals sin pasar por aquí.

## Git

Sin commits automáticos y sin coautoría de IA.

## Reglas de agentes

Ver [AGENTS.md](./AGENTS.md): única fuente de verdad.
