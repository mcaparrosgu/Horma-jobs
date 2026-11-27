---
type: system
title: Horma — Spec de sistema
description: Contrato de esquemas, arquitectura y requisitos transversales (RT-01…RT-19) que valen en todas las fases.
tags: [sistema, arquitectura, sdd]
status: active
sources: [./constitution.md, ./prd.md, ../docs/Horma v2_ requerimientos por fases.pdf, ./000-cimientos/clarifications.md, ./001-ofertas/clarifications.md]
generated: { at: 2026-11-12 }
verified: { by: human, at: 2026-11-14 }
stale_after: null
---

# Horma — Spec de sistema

Spec global (Spec-anchored). Lo que cambia en cada fase vive en `specs/NNN-<feature>/`; aquí solo
lo que vale siempre. Los principios y las líneas rojas están en la [constitución](./constitution.md); el qué,
el porqué y el orden de lo que falta por construir, en el [PRD](./prd.md).

## Visión
Una sola aplicación. Los agentes son código Python dentro de la web desde la fase 0, se prueban
uno a uno desde la consola `horma` y la orquestación está escrita para que LangGraph la sustituya
en la fase 4 sin tocar ningún agente (hecho: `LangGraphFlow` para `candidatura`, elegido con `HORMA_FLOW_IMPL`, que vale `langgraph` por defecto desde la spec 010; `PlainFlow` queda como referencia en la suite, RT-12).

## Arquitectura
Paquete `horma/` con tres puntos de entrada que llaman a los mismos flujos y agentes: consola,
API (FastAPI) y worker.

| Módulo | Contiene | Regla |
|---|---|---|
| `horma/schemas/` | Modelos Pydantic del contrato | Única fuente de verdad de los datos que viajan; las tablas están en las migraciones (SQL) |
| `horma/agents/<nombre>/` | `prompt.md`, `schemas.py` (entrada y salida), `agent.py` con `run()` | Sin estado, sin E/S, sin llamar a otros agentes |
| `horma/tools/` | Código determinista (`verificar_trazabilidad`, `medir_ats`, `buscar_ofertas`, `convertir_cv`, `generar_pdf`) | Funciones con tests unitarios; las que usan la red son `descargar`, `leer_pagina`, `greenhouse` y `dominio` (DNS) |
| `horma/flows/` | Interfaz `Flow` (con `pausas` y `reanudar`), `PlainFlow` y `LangGraphFlow` (`grafo.py`, único módulo que importa `langgraph`) | Toda la composición de agentes vive aquí |
| `horma/llm/` | Puerta única `completar(agente, prompt, entrada, esquema_salida)` | Único módulo que importa el SDK de Anthropic |
| `horma/cli.py` | Consola Typer | Sin lógica propia: mismo código que la API. Nunca abre la BD: lo que necesita persistir pasa por la API |
| `horma/ingesta` | Ingestor de fuentes: conectores, parsers y cola de ejecuciones (hoy, `ingesta.py`) | Sin credenciales de BD: entrega las ofertas por `POST /ofertas` con una clave de API de alcance `ingesta`. Cumple RT-15 a RT-19 |
| `horma/web/` | FastAPI por capas (routers, servicios, repositorios), cola en Postgres, worker, HTML/CSS/JS planos | Solo la API y el worker leen y escriben en Postgres. Los routers llaman solo a servicios (nunca a repositorios ni a la cola: contrato de import-linter) y solo los servicios encolan tareas (RF-10.11) |
| `evals/` | Fixtures con resultado esperado y umbral por agente | Se ejecutan desde la consola y en CI |

Los flujos reciben el estado y lo devuelven; los agentes solo hablan con la puerta única.
Cada agente declara un modelo (`pequeno` para extraer y clasificar, `mayor` para redactar, juzgar
y puntuar); la puerta lo traduce al modelo real.

## Contrato de esquemas
Diez módulos de esquemas Pydantic en `horma/schemas/` (los siete de la tabla más `taxonomia`, `filtros`, `estilo` y `origen`) y una tabla `origen` aparte, referenciada por cada
dato. Las tablas de la base de datos están escritas en SQL (migraciones de Alembic), no se generan desde los esquemas. Cambiar un `prompt.md` no toca código; cambiar un esquema es un cambio de contrato.

| Esquema | Qué representa | Entra en |
|---|---|---|
| `Oferta` | Oferta con sus campos extraídos, auditoría y taxonomía. `OfertaExtraida` es la oferta sin auditoría ni taxonomía, con `instrucciones_embebidas[]` | Fase 0 (extraída), fase 1 (completa) |
| `Perfil` | Datos de la usuaria con `origen` por dato y `preguntas_pendientes` | Fase 2 |
| `Preferencias` | Puestos, países, idiomas y sector, solo a partir del CV y editables | Fase 2 |
| `Match` | Nota 0-100 por experiencia y formación, nivel por condiciones de trabajo y explicación de 2-3 frases | Fase 2 |
| `Candidatura` | CV y carta adaptados, traza, huecos y estado (`borrador → aprobada → enviada → entrevista`, y `cerrada` con motivo desde cualquier estado) | Fase 3 |
| `Fuente` | Endpoint de ofertas: nombre, web del portal, URL del endpoint, método, parámetros, cabeceras, variable de entorno con la clave, mapeo de campos, activa | Fase 1 |
| `CalificacionFuente` | Resultado de calificar una fuente (condiciones de uso y `robots.txt`) | Fase 1 |

Además: `taxonomia.py` (sector, familia de puesto, nivel y stack; la misma para ofertas y perfiles).
Los campos concretos de cada esquema se fijan en la spec de la fase en la que entra; en la fase 0
solo se detallan `OfertaExtraida` y `Origen`.

## Requisitos transversales (EARS)
Valen en todas las fases. Cada uno tiene una verificación que entra en CI desde la fase 0 (RT-15 a RT-19, desde la spec 014).

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
| RT-12 | Los flujos DEBERÁN depender de la interfaz `Flow` y no de su implementación; la misma suite DEBERÁ pasar con `PlainFlow` y, desde la fase 4, con `LangGraphFlow`. La interfaz admite pausas: el flujo se para antes de un paso y `reanudar` lo continúa (en `candidatura`, antes de `entregar`). El checkpointer de Postgres se crea en `horma.web.checkpointer` y se inyecta. | Suite de flujos parametrizada por implementación |
| RT-13 | Un agente NO DEBERÁ llamar a otro agente; la composición vive en los flujos. | Test de arquitectura |
| RT-14 | CUANDO una tarea de la cola supere su tope de coste o de reintentos, el worker DEBERÁ detenerla y dejar la entidad en estado `error` con el motivo. | Test del worker con tope bajo |
| RT-15 | El ingestor DEBERÁ leer solo ofertas públicas de fuentes activas con calificación apta, sin sesión iniciada, con un `User-Agent` que identifique a Horma y un contacto, y NO DEBERÁ eludir captchas, bloqueos ni límites. | Test: una fuente no apta o inactiva no se pide |
| RT-16 | El ingestor DEBERÁ limitar el ritmo por dominio: una petición a la vez y una pausa mínima configurable por fuente (1 s por defecto); con Scrapy, `AutoThrottle` activado. | Test con transporte simulado y reloj falso |
| RT-17 | CUANDO una fuente responda 429 o 503, el ingestor DEBERÁ esperar lo que indique `Retry-After` o, si falta, reintentar con espera exponencial y aleatoria, tres veces como máximo; después la ejecución queda en `error`. CUANDO responda 403, DEBERÁ parar y dejar la fuente como «no apta». | Test con respuestas simuladas |
| RT-18 | El ingestor DEBERÁ extraer de forma incremental: respeta `cada_horas`, pide solo lo nuevo o cambiado desde la última ejecución (fecha, `id_externo`, `ETag` o `If-Modified-Since` si la fuente lo admite) y no vuelve a pedir el detalle de una oferta ya guardada. | Test: la segunda ejecución no repite peticiones de detalle |
| RT-19 | El ingestor NO DEBERÁ guardar datos personales de terceros (nombres, correos ni teléfonos de personas): se retiran antes de `POST /ofertas`. | Fixtures con datos personales sembrados, 100 % retirados |

RT-15 a RT-19 se verifican en CI desde la spec 014; hasta entonces `ingesta.py` no cumple RT-16 a RT-18.

## Decisiones de sistema
- **Base de datos:** PostgreSQL en Docker Compose (api, worker, postgres), con RLS y cola de tareas. Neon queda fuera de la fase 0.
- **Identidad:** Google OAuth 2.0; sesión en cookie segura; CSRF. Sin email ni contraseña propios.
- **Librería del modelo:** SDK `anthropic` envuelto en `horma.llm` (no Claude Agent SDK: los agentes son llamadas de un paso con esquema y el único bucle lo lleva el flujo).
- **Herramientas:** `uv`, Typer, `import-linter`, `pytest`, `ruff`.
- **Flujos desde la API:** siempre por cola y worker, con un flag de desarrollo para ejecutarlos en línea.
- **Sin RAG:** el match es filtro duro en SQL, pre-orden por taxonomía compartida y puntuación del matcher por tandas.
- **Fuentes:** nunca LinkedIn ni Indeed; cada fuente es una fila editable de la tabla `fuentes`, sembrada desde `config/endpoints.json`. Una fuente solo se activa con una calificación apta (condiciones de uso y `robots.txt`). Con esa calificación, añadir su conector (API, feed, sitemap, API de índice público, Apify, Zyte, Scrapy, Crawlee o Firecrawl) no necesita más permiso que RT-15 a RT-19.
- **Ofertas:** catálogo común (desde la fase 1). Cualquier sesión las lee; solo el modo sistema (la API al recibirlas y el worker al procesarlas) las escribe, por RLS.
- **Administración:** el dashboard `/ingesta` y las claves de API son solo para las cuentas listadas en `HORMA_ADMINS`.
Las decisiones de cada fase se leen junto con las siguientes: la **simplificación (fase 10)**, al final,
sustituye lo que cambia del CV base, de `generar_cv_base` y de `clasificar_respuesta`.

- **Fase 2 (perfil y recomendación):** los flujos `perfilar`, `clasificar_perfil`, `generar_cv_base` (aparcado desde la fase 10) y `recomendar` corren en el worker y también desde la consola (`horma flujo correr`, `horma recomendar`). Los CV subidos viven en el volumen `horma_archivos`, solo montado en la API; el worker recibe el texto. `GET /api/catalogo` (clave `ingesta`) da a la consola las ofertas comunes sin datos personales. Las correcciones de la usuaria no entran en `evals/` sin `horma eval importar-correccion`.
- **Fase 3 (candidatura, construida):** los flujos `candidatura` y `clasificar_respuesta` corren en el worker y desde la consola (`horma flujo correr`, con `--usuaria` y `--oferta` sin base de datos). La candidatura separa `estado` (la máquina, que solo cambia la usuaria) y `preparacion` (el resultado del flujo: `lista` o `pendiente_de_ti`). Simplificada en el bloque H (16-nov-2026): el CV base de partida lo elige la herramienta `elegir_cv_base` (sin modelo; desde la fase 10 la candidatura parte del CV maestro, sin CV base) y un solo juez (`juez-candidatura`) revisa CV y carta con una vuelta como máximo (3-5 llamadas por candidatura). Un CV base editado por ella cuenta como fuente con origen «usuaria»; lo que edita en una candidatura se queda en esa candidatura, y cada CV base guarda un historial de versiones al editarlo desde su pantalla. Los errores de trazabilidad y del juez son avisos junto a su frase (pulsar Aprobar cuenta como revisarlos). El tope de coste por candidatura (1 USD) se comprueba en la puerta única, falle o no la tarea. La respuesta de la empresa se marca con dos botones («Me han llamado», «Me han rechazado»); el flujo `clasificar_respuesta` queda solo para la consola.
- **Datos de prueba:** inventados; el repositorio versiona fixtures, nunca datos de una persona.

- **Fase 4 (LangGraph, calidad y salida):** LangGraph solo para `candidatura` (`flows/grafo.py`, único módulo que importa `langgraph`; `HORMA_FLOW_IMPL` elige `plain` o `langgraph`). El flujo se para antes de `entregar` con el estado en Postgres y, al aprobar la usuaria, se reanuda y deja los PDF fijos. La puerta del modelo marca por código las órdenes a la IA en la entrada y detecta fugas del prompt en la salida; `main` está protegida (`secretos` y `calidad`; `evals-reales` solo a mano desde la fase 5). `/costes` (solo admins) y las alertas de gasto y errores (pantalla, log y correo SMTP) no llevan datos personales. El despliegue es, de momento, local con Docker Compose y PostgreSQL; Vercel, más adelante (P6, profesor, 17-nov-2026). El red-teaming no es prioritario hasta que haya usuarias reales. **Antes de usuarias reales, el `matcher` debe pasar la puerta de salida del paso 2 del PRD** (spec 012).

- **Fase 5 (correcciones del profesor, construida):** lo que edita la usuaria en el perfil manda sobre los CV subidos (CV maestro). Las ofertas que ella añade (texto o URL, leída con Apify; portales vetados en `horma/assets/portales_vetados.json`; los portales a los que se podrá enviar, en `portales.json`, para la medición de destinos del paso 1) son privadas: solo las ve quien las añadió, por RLS, y entran en Recomendadas con la marca «Añadida por ti». `validar_cv` y `muletillas_ia` son código, sin modelo; el juez revisa además coherencia y que no suene a IA. El agente `analizador_estilo` crea una guía de estilo una sola vez (más botón) que siguen los redactores. Fuentes nuevas con adaptadores de ingesta (Basic auth, detalle, `cada_horas`, atribución visible, borrado de caducadas): Himalayas y Jobicy aptas; Remotive, Adzuna e InfoJobs inactivas. `evals-reales` solo corre a mano hasta el lanzamiento.

- **Simplificación (fase 10, spec 010):** agentes en uso por defecto, 10 (el décimo, `sinonimos-puestos`, de la spec 012, su set de evals, en la CI con las respuestas grabadas; spec 012, D-068 y D-076): `analizador-oferta` (una llamada por oferta en lugar de `extractor-oferta`, `clasificador-oferta` y `auditor-oferta`, que quedan registrados como reserva con `HORMA_OFERTA_UN_AGENTE=false`), `auditor-fuentes`, `extractor-perfil`, `clasificador-postulante`, `matcher`, `redactor-cv`, `redactor-carta`, `juez-candidatura`, `analizador-estilo` y `sinonimos-puestos`. **Aparcados** (código conservado, sin uso ni evals en la CI): `clasificador-respuesta` y `generador-cv-base`. Presupuesto único de 1 USD por usuaria y día; la compatibilidad se guarda con una huella del perfil y no se repite si no cambia. Alertas de gasto: más de 5 USD al día o más de un 50 % de llamadas fallidas en la última hora (con al menos 10). Los routers solo hablan con servicios y qué tarea lanza a cuál está en una tabla (`ENCADENADOS`, en el worker). La candidatura parte del CV maestro, sin CV base (las tablas `cv_base` se conservan, sin escribirse). El avance de cada tarea se ve en su pantalla, nunca en la cabecera.

## Fases
| Fase | Feature | Agentes que entran | Puerta de salida |
|---|---|---|---|
| 0 | [`000-cimientos`](./000-cimientos/clarifications.md) | `extractor-oferta` | Eval en CI sobre 10 fixtures; RLS probada; métricas de cada llamada registradas |
| 1 | `001-ofertas` | `auditor-oferta`, `clasificador-oferta`, `auditor-fuentes` | Precisión ≥ 0,9 por campo; adversarias 100 % |
| 2 | `002-perfil-recomendacion` | `extractor-perfil`, `clasificador-postulante`, `generador-cv-base`, `matcher` | Evals de perfil y recomendación en verde |
| 3 | `003-candidatura` | `redactor-cv`, `redactor-carta`, `juez-candidatura`, `clasificador-respuesta` (retirados en el bloque H: `juez-cv`, `juez-carta`, `selector-cv-base`) | Errores sembrados rechazados al 100 %; flujo paso a paso en consola |
| 4 | `004-langgraph-salida` | ninguno (cambia `clasificador-respuesta`: añade la línea de art. 9) | Misma suite en verde con `LangGraphFlow`; umbrales bloqueantes en CI (`evals-reales`, a mano desde la fase 5); red-teaming al 100 %; revisión de líneas rojas firmada |
| 5 | `005-correcciones-profesor` | `analizador_estilo` (cambian `extractor-perfil`, `juez-candidatura`, `generador-cv-base` y los redactores) | Evals `perfil`, `cv`, `cv-base` y `estilo` en umbral |
| 6-9 | `006` a `009` (rediseño, ajustes de pantalla, portada de ofertas, CV maestro y entrevista) | `analizador-estilo` sin cambios; ver [`index.md`](./index.md) | Ver cada spec |
| 10 | `010-simplificacion` | `analizador-oferta` (sustituye a tres en el flujo); aparcados `clasificador-respuesta` y `generador-cv-base` | Evals `ofertas` y `red-teaming` en umbral con `analizador-oferta`; suite verde; prueba manual de Mar por bloque |

Las fases no tienen fechas: se pasa de una a otra cuando se cumple su puerta. Si hace falta
recortar, se recortan pantallas, nunca agentes ni evals.
