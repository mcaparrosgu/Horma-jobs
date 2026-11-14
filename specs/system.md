---
type: system
title: Horma — Spec de sistema
description: Contrato de esquemas, arquitectura y requisitos transversales (RT-01…RT-14) que valen en todas las fases.
tags: [sistema, arquitectura, sdd]
status: active
sources: [./constitution.md, ../docs/Horma v2_ requerimientos por fases.pdf, ./000-cimientos/clarifications.md, ./001-ofertas/clarifications.md]
generated: { by: claude-code, at: 2026-11-12 }
verified: { by: human, at: 2026-11-14 }
stale_after: null
---

# Horma — Spec de sistema

Spec global (Spec-anchored). Lo que cambia en cada fase vive en `specs/NNN-<feature>/`; aquí solo
lo que vale siempre. Los principios y las líneas rojas están en la [constitución](./constitution.md).

## Visión
Una sola aplicación. Los agentes son código Python dentro de la web desde la fase 0, se prueban
uno a uno desde la consola `horma` y la orquestación está escrita para que LangGraph la sustituya
en la fase 4 sin tocar ningún agente.

## Arquitectura
Paquete `horma/` con tres puntos de entrada que llaman a los mismos flujos y agentes: consola,
API (FastAPI) y worker.

| Módulo | Contiene | Regla |
|---|---|---|
| `horma/schemas/` | Modelos Pydantic del contrato | Única fuente de verdad; las tablas se generan desde aquí |
| `horma/agents/<nombre>/` | `prompt.md`, `schemas.py` (entrada y salida), `agent.py` con `run()` | Sin estado, sin E/S, sin llamar a otros agentes |
| `horma/tools/` | Código determinista (`verificar_trazabilidad`, `medir_ats`, `buscar_ofertas`, `convertir_cv`) | Funciones puras con tests unitarios |
| `horma/flows/` | Interfaz `Flow`, `PlainFlow` (y `LangGraphFlow` en la fase 4) | Toda la composición de agentes vive aquí |
| `horma/llm/` | Puerta única `completar(agente, prompt, entrada, esquema_salida)` | Único módulo que importa el SDK de Anthropic |
| `horma/cli.py` | Consola Typer | Sin lógica propia: mismo código que la API. Nunca abre la BD: lo que necesita persistir pasa por la API |
| `horma/ingesta.py` | Ingestor de fuentes | Sin credenciales de BD: entrega las ofertas por `POST /ofertas` con una clave de API de alcance `ingesta` |
| `horma/web/` | FastAPI por capas (routers, servicios, repositorios), cola en Postgres, worker, HTML/CSS/JS planos | Solo la API y el worker leen y escriben en Postgres |
| `evals/` | Fixtures con resultado esperado y umbral por agente | Se ejecutan desde la consola y en CI |

Los flujos reciben el estado y lo devuelven; los agentes solo hablan con la puerta única.
Cada agente declara un modelo (`pequeno` para extraer y clasificar, `mayor` para redactar, juzgar
y puntuar); la puerta lo traduce al modelo real.

## Contrato de esquemas
Siete esquemas Pydantic en `horma/schemas/` y una tabla `origen` aparte, referenciada por cada
dato. Cambiar un `prompt.md` no toca código; cambiar un esquema es un cambio de contrato.

| Esquema | Qué representa | Entra en |
|---|---|---|
| `Oferta` | Oferta con sus campos extraídos, auditoría y taxonomía. `OfertaExtraida` es la oferta sin auditoría ni taxonomía, con `instrucciones_embebidas[]` | Fase 0 (extraída), fase 1 (completa) |
| `Perfil` | Datos de la usuaria con `origen` por dato y `preguntas_pendientes` | Fase 2 |
| `Preferencias` | Puestos, países, idiomas y sector, solo a partir del CV y editables | Fase 2 |
| `Match` | Nota 0-100 por experiencia y formación, nivel por condiciones de trabajo y explicación de 2-3 frases | Fase 2 |
| `Candidatura` | CV y carta adaptados, traza, huecos y estado (`borrador → aprobada → enviada → entrevista`) | Fase 3 |
| `Fuente` | Endpoint de ofertas: nombre, web del portal, URL del endpoint, método, parámetros, cabeceras, variable de entorno con la clave, mapeo de campos, activa | Fase 1 |
| `CalificacionFuente` | Resultado de calificar una fuente (condiciones de uso y `robots.txt`) | Fase 1 |

Además: `taxonomia.py` (sector, familia de puesto, nivel y stack; la misma para ofertas y perfiles).
Los campos concretos de cada esquema se fijan en la spec de la fase en la que entra; en la fase 0
solo se detallan `OfertaExtraida` y `Origen`.

## Requisitos transversales (EARS)
Valen en todas las fases. Cada uno tiene una verificación que entra en CI desde la fase 0.

| ID | Requisito | Se verifica con |
|---|---|---|
| RT-01 | El sistema DEBERÁ implementar cada agente como un módulo con prompt en archivo, esquemas Pydantic de entrada y salida y una función `run` sin acceso a base de datos ni a disco. | Test unitario por agente con la puerta única simulada |
| RT-02 | El sistema DEBERÁ hacer todas las llamadas al modelo a través de `horma.llm`; ningún otro módulo importará el SDK del proveedor. | Test de arquitectura (import-linter) en CI |
| RT-03 | CUANDO la salida de un agente no valide contra su esquema, la puerta única DEBERÁ reintentar una vez con el error de validación y, si vuelve a fallar, lanzar `SalidaInvalida` sin persistir nada. | Test con salida corrupta simulada |
| RT-04 | El sistema DEBERÁ permitir ejecutar cualquier agente desde la consola con una entrada en archivo y guardar la salida en archivo. | `horma agente correr <nombre> --entrada x --salida y` |
| RT-05 | El sistema DEBERÁ permitir ejecutar cualquier flujo desde la consola paso a paso, mostrando la entrada y la salida de cada paso y guardando la traza en una carpeta. | `horma flujo correr <nombre> --paso-a-paso --traza <dir>` |
| RT-06 | El sistema DEBERÁ registrar por cada llamada al modelo: agente, modelo, tokens de entrada y salida, coste, latencia y resultado, sin el texto de la usuaria. | Tabla `llm_llamadas` y test de que no guarda texto |
| RT-07 | CUANDO una oferta, un CV o un correo contenga instrucciones, el agente DEBERÁ registrarlas en `instrucciones_embebidas` y no ejecutarlas. | Fixtures adversarias en cada eval, 100 % sin efecto |
| RT-08 | El sistema DEBERÁ conservar el origen de cada dato de perfil y de cada frase de CV y carta; si no existe origen, el dato irá a `preguntas_pendientes` o a `huecos`, nunca al documento. | `verificar_trazabilidad` + eval de CV |
| RT-09 | El sistema NO DEBERÁ inferir ni almacenar edad, nacionalidad ni categorías del art. 9 RGPD, ni mencionarlas en explicaciones. | Juez sobre explicaciones y perfiles, 100 % |
| RT-10 | MIENTRAS una candidatura no esté en estado `aprobada` por su dueña con su sesión, el sistema NO DEBERÁ marcarla como enviada ni exponerla a terceros. | Test de la máquina de estados y de permisos |
| RT-11 | Cada agente DEBERÁ tener un set de evals con umbral; el sistema DEBERÁ poder correrlos desde la consola y en CI con una clave de presupuesto limitado. | `horma eval correr <set>` y job de CI |
| RT-12 | Los flujos DEBERÁN depender de la interfaz `Flow` y no de su implementación; la misma suite DEBERÁ pasar con `PlainFlow` y, en la fase 4, con `LangGraphFlow`. | Suite de flujos parametrizada por implementación |
| RT-13 | Un agente NO DEBERÁ llamar a otro agente; la composición vive en los flujos. | Test de arquitectura |
| RT-14 | CUANDO una tarea de la cola supere su tope de coste o de reintentos, el worker DEBERÁ detenerla y dejar la entidad en estado `error` con el motivo. | Test del worker con tope bajo |

## Decisiones de sistema
- **Base de datos:** PostgreSQL en Docker Compose (api, worker, postgres), con RLS y cola de tareas. Neon queda fuera de la fase 0.
- **Identidad:** Google OAuth 2.0; sesión en cookie segura; CSRF. Sin email ni contraseña propios.
- **Librería del modelo:** SDK `anthropic` envuelto en `horma.llm` (no Claude Agent SDK: los agentes son llamadas de un paso con esquema y el único bucle lo lleva el flujo).
- **Herramientas:** `uv`, Typer, `import-linter`, `pytest`, `ruff`.
- **Flujos desde la API:** siempre por cola y worker, con un flag de desarrollo para ejecutarlos en línea.
- **Sin RAG:** el match es filtro duro en SQL, pre-orden por taxonomía compartida y puntuación del matcher por tandas.
- **Fuentes:** nunca LinkedIn ni Indeed; cada fuente es una fila editable de la tabla `fuentes`, sembrada desde `config/endpoints.json`. Una fuente solo se activa con una calificación apta (condiciones de uso y `robots.txt`).
- **Ofertas:** catálogo común (desde la fase 1). Cualquier sesión las lee; solo el modo sistema (la API al recibirlas y el worker al procesarlas) las escribe, por RLS.
- **Administración:** el dashboard `/ingesta` y las claves de API son solo para las cuentas listadas en `HORMA_ADMINS`.
- **Datos de prueba:** inventados; el repositorio versiona fixtures, nunca datos de una persona.

## Fases
| Fase | Feature | Agentes que entran | Puerta de salida |
|---|---|---|---|
| 0 | [`000-cimientos`](./000-cimientos/clarifications.md) | `extractor-oferta` | Eval en CI sobre 10 fixtures; RLS probada; métricas de cada llamada registradas |
| 1 | `001-ofertas` | `auditor-oferta`, `clasificador-oferta`, `auditor-fuentes` | Precisión ≥ 0,9 por campo; adversarias 100 % |
| 2 | `002-perfil-recomendacion` | `extractor-perfil`, `clasificador-postulante`, `generador-cv-base`, `matcher` | Evals de perfil y recomendación en verde |
| 3 | `003-candidatura` | `redactor-cv`, `juez-cv`, `redactor-carta`, `juez-carta`, `clasificador-respuesta` | Errores sembrados rechazados al 100 %; flujo paso a paso en consola |
| 4 | `004-langgraph-salida` | ninguno | Misma suite en verde con `LangGraphFlow`; umbrales bloqueantes en CI |

Las fases no tienen fechas: se pasa de una a otra cuando se cumple su puerta. Si hace falta
recortar, se recortan pantallas, nunca agentes ni evals.
