---
type: clarifications
title: langgraph-salida — Aclaraciones
description: Preguntas abiertas de la fase 4 (LangGraph, calidad y salida) resueltas con la persona antes de escribir la spec, más los supuestos.
tags: [clarify, langgraph, ci, guardarrailes, despliegue, observabilidad]
status: active
sources: [../system.md, ../constitution.md, ../003-candidatura/spec.md, ../../docs/Horma v2_ requerimientos por fases.pdf]
generated: { at: 2026-11-16 }
verified: { by: human, at: 2026-11-16 }
stale_after: null
---

# langgraph-salida — Aclaraciones

## Punto de partida
La fase 3 está cerrada (T01-T32, bloque H incluido). La fase 4 migra el flujo `candidatura` ya
simplificado (`elegir_cv_base → redactar_cv → redactar_carta → comprobar → juzgar → vuelta única →
componer`). No entra ningún agente nuevo (PDF, «Fase 4»): si un agente tuviera que cambiar para
migrar, la fase 3 no estaba bien cerrada.

## Preguntas y respuestas
- P1: ¿Qué flujos pasan a LangGraph? → R: **solo `candidatura`**, como propone el PDF. `procesar_oferta`,
  `perfilar`, `recomendar` y los demás son lineales y siguen en `PlainFlow`. La interfaz `Flow` permite
  migrarlos más adelante sin tocar nada más.
- P2: ¿Cómo se hace la parada para la aprobación (RF-4.3)? → R: **pausa y paso final**. El grafo se para
  cuando los documentos están listos, con el estado guardado en Postgres (checkpointer). Cuando la
  usuaria aprueba, se reanuda con un último paso, `entregar`, que toma el texto aprobado (con sus
  ediciones), genera los dos PDF y los guarda tal cual. Se descarta la alternativa de dejar la
  aprobación como ruta aparte, que no cumplía RF-4.3.
- P3: ¿Cuándo corren los evals con el modelo real en CI y cómo bloquean? → R: **con el modelo real en
  cada PR a `main`, bloqueante**. Cada push corre en simulado (rápido y gratis). GitHub no deja fusionar
  si un umbral falla (protección de rama). Mar pasa a trabajar con rama → PR → fusionar. Se arregla la
  clave que hoy llega vacía a CI. Coste: unos pocos USD por PR (tope de 1 USD por set).
- P4: ¿Qué umbral ATS se fija (RF-4.4)? → R: **media ≥ 0,75** en el set `cv`. La media medida en la fase 3
  fue 0,78; el margen absorbe la variación normal del modelo.
- P5: ¿Cómo es la capa de entrada de los guardarraíles (RF-4.5)? → R: **código que marca y registra, sin
  bloquear**. Antes de cada llamada al modelo se buscan patrones de manipulación; se registran y se
  avisa, pero el texto pasa (así no se pierden ofertas legítimas por un falso positivo). Set nuevo
  `evals/red-teaming/` con unas 10 ofertas y unos 10 correos que intentan manipular a la IA, activar un
  envío o sacar datos; exige 100 % sin efecto y corre en CI.
- P6: ¿Dónde se despliega (RF-4.6)? → R: **respondido por el profesor (17-nov-2026): de momento en local, con Docker Compose y PostgreSQL; más adelante, en Vercel.** (Texto previo a la respuesta: El PDF no nombra destino: solo
  propone «Compose para CI y Neon para los entornos compartidos», y la constitución fija «PostgreSQL en
  Docker Compose, sin Neon». Mientras tanto, todo se prepara sin depender del destino (perfil de
  producción, proxy con HTTPS, endurecimiento) y se prueba en local; la tarea de despliegue real queda
  bloqueada hasta su respuesta.)
  Vercel no ejecuta contenedores ni un Postgres propio ni el worker: al llegar ese momento habrá que
  revisar la arquitectura y la constitución («PostgreSQL en Docker Compose, sin Neon»).
- P7: ¿Dónde se ven los costes y cómo avisan las alertas (RF-4.7)? → R: **pantalla de admin `/costes` y
  aviso por correo**. La pantalla muestra coste y errores por día, agente y modelo, sin datos
  personales. Las alertas saltan por gasto del día y por tasa de errores; se ven en la pantalla, se
  registran en el log y llegan por correo.
- P8: ¿Cómo se hace la prueba con cinco personas (RF-4.8)? → R: **la hace Mar**, con 5 CV inventados y 5
  casos distintos que, entre todos, recorren el 100 % de las opciones de Horma. Cambia el RF-4.8 del
  PDF (el pedido gana). Se comprueba que todo funciona; la prueba de uso con personas que no conocen
  Horma queda fuera de esta fase.
- P9: ¿Cómo se hace la revisión de líneas rojas (RF-4.8)? → R: **Claude revisa y Mar firma**. Una tabla
  con cada prompt (los agentes activos) y el flujo de aprobación frente a cada línea roja, con la prueba
  que lo demuestra (test, eval o línea del prompt) y lo que falte arreglar. Queda en
  `docs/revision-lineas-rojas.md`.

## Decisiones derivadas
- `LangGraphFlow` cumple la misma interfaz `Flow` que `PlainFlow` (`run`, `run_step`, `siguiente`,
  `pasos`), porque la consola recorre los flujos paso a paso con `run_step` y `siguiente`.
- La interfaz `Flow` gana la pausa: `pausas` (los pasos antes de los que se para) y `reanudar`. Las dos
  implementaciones la cumplen, para que la misma suite pase con ambas (RF-4.2, RT-12).
- `entregar` es código (sin modelo): no suma llamadas ni coste a la candidatura.
- El checkpoint guarda texto de la usuaria (CV y carta). Se borra en cuanto la candidatura se entrega o
  se cierra (minimización de datos), y solo lo tocan el worker y la API.
- Los umbrales de todos los sets se guardan en un archivo versionado; CI no puede rebajarlos con
  opciones de la consola.
- **Refinamiento de P3 (17-nov, por coste):** `evals-reales` sigue siendo obligatorio en cada PR a `main`, pero
  solo llama al modelo si el PR toca `horma/`, `evals/`, `config/`, `pyproject.toml`, `uv.lock` o `ci.yml`; un PR
  de solo specs, README, docs o tests termina en verde sin gasto (cada ejecución real cuesta unos 1,8 USD). Además,
  un push nuevo cancela la ejecución anterior del mismo PR (`concurrency`).
- Las alertas y los registros nunca llevan texto de la usuaria: el motivo de error de una tarea se
  guarda como paso + tipo de error + mensaje fijo.

## Fuera de alcance (anotado, no se construye aquí)
- LangGraph en los flujos lineales (P1).
- El despliegue real en Vercel: el profesor lo sitúa «más adelante» (P6); de momento, local con Compose.
- Red-teaming (P5): el profesor lo da por poco importante hasta que haya usuarias reales (17-nov-2026). El set
  y su umbral se mantienen; no se invierte más tiempo en estabilizarlo (PR #8 aparcado).
- Prueba de uso con personas que no conocen Horma (P8): antes de abrir a usuarias reales.
- `horma flujo correr --desde <paso>` (ya diferido en la fase 3).
- Perfeccionar el `matcher`: obligatorio antes de probar con usuarias reales (hoy, spec 012: paso 2 del PRD).
- Modo sin conexión completo de la PWA.
- Después de la fase 4 sigue el plan del PDF sin cambios: portal de empresas, privacidad y RGPD, envío
  automático con supervisor (ya como grafo), entrevista del perfil, suscripciones y MCP de solo lectura.

## Supuestos (revisables)
- La implementación activa se elige con `HORMA_FLOW_IMPL` (`plain` o `langgraph`). Vale `plain` por
  defecto hasta que la suite pase con las dos y la pausa funcione; después, `langgraph`.
- `PlainFlow` también se para antes de `entregar`; su estado pausado es la propia fila de la
  candidatura (no necesita checkpointer).
- Las tablas del checkpointer las crea la migración 0008, sin RLS por usuaria (no tienen columna de
  usuaria). El hilo se identifica con el id de la candidatura.
- La PWA se puede instalar (manifest y service worker que guarda lo estático) y muestra una página «Sin
  conexión»; no funciona sin red.
- El correo de alertas sale por SMTP genérico configurado en `.env` (`SMTP_*`, `ALERTAS_CORREO`), sin
  datos personales y como mucho uno por tipo de alerta y día.
- Umbrales iniciales de alerta: gasto del día > 2 USD y tasa de errores > 20 % en la última hora (con un
  mínimo de 5 llamadas). Se ajustan al medir.
- Los límites de ritmo se guardan en memoria del proceso de la API (un solo proceso). Si algún día hay
  varios, se mueven a Postgres.
