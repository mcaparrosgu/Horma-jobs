---
type: spec
title: langgraph-salida — Spec funcional
description: Requisitos funcionales de la fase 4 (flujo de candidatura sobre LangGraph con pausa para la aprobación, evals bloqueantes en CI, guardarraíles y red teaming, PWA y despliegue endurecido, costes y alertas, prueba final y revisión de líneas rojas), en notación EARS.
tags: [spec, langgraph, ci, guardarrailes, despliegue, observabilidad]
status: active
sources: [./clarifications.md, ../system.md, ../constitution.md, ../003-candidatura/spec.md, ../../docs/Horma v2_ requerimientos por fases.pdf]
generated: { by: claude-code, at: 2026-11-16 }
verified: { by: human, at: 2026-11-16 }
stale_after: null
---

# langgraph-salida — Especificación

## Contexto
La misma Horma, pero con la orquestación del flujo `candidatura` sobre LangGraph y lista para salir:
los evals bloquean el merge, hay guardarraíles por capas, la web se instala como PWA y se puede
desplegar con HTTPS, y los costes y errores se ven y avisan. **No entra ningún agente nuevo.**

Para la usuaria cambia poco. Prepara una candidatura igual que antes, pero ahora el flujo se queda en
pausa esperando su aprobación. Cuando pulsa «Aprobar y descargar», el flujo sigue y deja los dos PDF
fijos, tal como los aprobó.

Los requisitos transversales (RT-xx) están en [system.md](../system.md) y las respuestas del Clarify
en [clarifications.md](./clarifications.md) (se citan como P1…P9).

**Cambios sobre el PDF:** RF-4.8 lo hace Mar con 5 casos en lugar de con cinco personas (P8). El
destino del despliegue de RF-4.6 queda pendiente del profesor (P6).

## Requisitos (EARS)

### LangGraph (RF-4.1, RF-4.2)
- **RF-4.1** El sistema DEBERÁ incluir `LangGraphFlow` para `candidatura`: un `StateGraph` con el mismo
  estado (`EstadoCandidatura` más las claves internas del flujo), un nodo por paso que llama a la misma
  función de paso (el mismo `run()` del agente o la misma herramienta) y las mismas aristas
  condicionales (`tras_comprobar`, `tras_juzgar`), que mantienen la vuelta única. Los pasos y las
  aristas DEBERÁN definirse una sola vez y servir a las dos implementaciones. Ningún agente ni
  herramienta DEBERÁ cambiar.
- **RF-4.1b** `LangGraphFlow` DEBERÁ cumplir la interfaz `Flow` completa (`run`, `run_step`,
  `siguiente`, `pasos`), de modo que `horma flujo correr candidatura --paso-a-paso --traza <dir>` funcione
  igual con las dos implementaciones (RT-05).
- **RF-4.2** La suite de flujos (RT-12) y `evals/cv/` DEBERÁN pasar sin cambios en sus casos con
  `PlainFlow` y con `LangGraphFlow`. La implementación activa DEBERÁ elegirse por configuración
  (`HORMA_FLOW_IMPL`), sin tocar código. Con las mismas respuestas simuladas, las dos DEBERÁN dar el
  mismo estado final y el mismo número de llamadas al modelo (de 3 a 5).

### Pausa para la aprobación (RF-4.3)
- **RF-4.3** El flujo `candidatura` DEBERÁ pararse después de `componer`, antes del paso `entregar`, con
  su estado guardado en Postgres (checkpointer, identificado por la candidatura), y la candidatura DEBERÁ
  quedar en `borrador` con `preparacion` = `lista` o `pendiente_de_ti`, como hasta ahora (P2).
- **RF-4.3b** MIENTRAS el flujo esté en pausa, la usuaria DEBERÁ poder leer, editar y descartar la
  candidatura como en la fase 3 (RF-3.8). Editar NO DEBERÁ llamar al modelo ni reanudar el flujo.
- **RF-4.3c** CUANDO la dueña pulse «Aprobar y descargar», el sistema DEBERÁ pasar la candidatura a
  `aprobada` y reanudar el flujo con el texto que ella aprobó (con sus ediciones). `entregar` DEBERÁ
  generar los PDF del CV y de la carta y guardarlos tal cual; desde entonces, las descargas DEBERÁN
  servir esos PDF guardados. `entregar` NO DEBERÁ llamar al modelo.
- **RF-4.3d** SI la reanudación falla, ENTONCES la candidatura DEBERÁ seguir `aprobada` y las descargas
  DEBERÁN generar el PDF al momento, como en la fase 3; el fallo DEBERÁ quedar registrado sin texto de
  la usuaria. Nunca se pierde una aprobación.
- **RF-4.3e** CUANDO la candidatura se entregue o se cierre, el sistema DEBERÁ borrar su checkpoint
  (minimización: guarda CV y carta). Solo el worker y la API DEBERÁN leer o escribir los checkpoints.
- **RF-4.3f** La IA NUNCA DEBERÁ reanudar el flujo: solo lo reanuda la aprobación de la dueña con su
  sesión (RT-10).

### Evals bloqueantes en CI (RF-4.4)
- **RF-4.4** Los umbrales de los 7 sets de evals existentes y del nuevo `red-teaming` DEBERÁN estar
  fijados en un archivo versionado que lee el ejecutor de evals; desde la línea de comandos NO DEBERÁN
  poder rebajarse en CI.
- **RF-4.4b** El set `cv` DEBERÁ exigir una cobertura ATS media ≥ 0,75 en sus casos de flujo completo
  (P4); hasta ahora solo se medía.
- **RF-4.4c** En cada push, CI DEBERÁ correr tests, estilo, arquitectura y todos los evals en simulado.
  CUANDO se abra o actualice un PR a `main`, CI DEBERÁ correr además todos los evals con el modelo real
  y la implementación activa, con el tope de 1 USD por set; SI falta la clave, ENTONCES el job DEBERÁ
  fallar, no pasar a simulado (P3). Excepción: `recomendacion` no corre con el modelo real en CI
  hasta el plan del `matcher` (su `nota` no alcanza el umbral con el modelo real); sigue en simulado.
- **RF-4.4d** `main` DEBERÁ estar protegida para que un PR no se pueda fusionar si un job de CI falla.

### Guardarraíles y red teaming (RF-4.5)
- **RF-4.5** **Capa de entrada:** antes de cada llamada al modelo, el sistema DEBERÁ buscar con código
  señales de manipulación en la entrada (órdenes dirigidas a una IA, peticiones de enviar, aprobar o
  revelar instrucciones o datos, texto oculto con caracteres invisibles, bloques codificados largos).
  DEBERÁ registrar el tipo de cada señal, sin el texto, en la métrica de esa llamada, y NO DEBERÁ
  bloquear la llamada (P5).
- **RF-4.5b** CUANDO la oferta de una candidatura tenga señales de manipulación, la candidatura DEBERÁ
  mostrar un aviso en llano («Esta oferta contiene texto que intenta dar órdenes a la IA; no se ha
  obedecido»).
- **RF-4.5c** **Capa de salida:** además de lo que ya existe (esquema, `verificar_trazabilidad`, rasgos
  personales y juez), la puerta única DEBERÁ comprobar que la salida de un agente no reproduce
  fragmentos de su prompt de sistema; SI los reproduce, ENTONCES DEBERÁ tratarla como salida inválida
  (RT-03).
- **RF-4.5d** **Capa de aprobación:** obligatoria y sin excepciones. Ningún texto de una oferta, un CV o
  un correo DEBERÁ poder cambiar el estado de una candidatura ni reanudar el flujo (RT-10, RF-4.3f).
- **RF-4.5e** El set `evals/red-teaming/` DEBERÁ tener unas 10 ofertas y unos 10 correos inventados que
  intentan manipular a la IA, activar un envío o sacar datos (el prompt, datos de contacto que no están
  en las fuentes). Cada caso DEBERÁ dar 100 % sin efecto: la salida es la esperada, las instrucciones
  quedan en `instrucciones_embebidas`, la capa de entrada lo marca y el estado no cambia.

### Salida: PWA y despliegue (RF-4.6)
- **RF-4.6** La web DEBERÁ poder instalarse como PWA (manifest, iconos y service worker que guarda solo
  los archivos estáticos) y, sin red, DEBERÁ mostrar una página «Sin conexión». NUNCA DEBERÁ guardar en
  la caché respuestas de la API.
- **RF-4.6b** Horma DEBERÁ tener un perfil de producción de Docker Compose con: un proxy con HTTPS
  delante de la API, la API y la base de datos sin puertos publicados, contenedores sin root, reinicio
  automático y comprobación de salud.
- **RF-4.6c** En producción, la API DEBERÁ añadir HSTS y `Permissions-Policy` a las cabeceras de
  seguridad que ya envía, DEBERÁ fiarse solo de las cabeceras del proxy propio y DEBERÁ negarse a
  arrancar con secretos de desarrollo o vacíos (secretos distintos por entorno).
- **RF-4.6d** El sistema DEBERÁ limitar el ritmo, además de en `POST /ofertas`, en el login, la subida
  de CV y la creación y reintento de candidaturas, por usuaria o por IP, y responder 429 al pasarse.
  Los límites de tamaño actuales (64 KB por petición y `MAX_CV_BYTES`) se mantienen.
- **RF-4.6e** El despliegue real en un servidor DEBERÁ esperar a la respuesta del profesor sobre el
  destino (P6). Hasta entonces, el perfil de producción DEBERÁ probarse en local con HTTPS.

### Observabilidad (RF-4.7)
- **RF-4.7** Una pantalla `/costes`, solo para admins (`HORMA_ADMINS`), DEBERÁ mostrar a partir de
  `llm_llamadas` el coste y el número de llamadas por día (últimos 30), por agente y por modelo, la tasa
  de errores por agente y las tareas en error por tipo. NO DEBERÁ mostrar ningún dato personal ni
  ningún id de usuaria.
- **RF-4.7b** CUANDO el gasto del día supere `ALERTA_GASTO_DIA_USD` o la tasa de errores de la última
  hora supere `ALERTA_TASA_ERRORES` (con un mínimo de llamadas), el sistema DEBERÁ crear una alerta,
  mostrarla en `/costes`, escribirla en el log y enviar un correo a `ALERTAS_CORREO`, como mucho uno
  por tipo de alerta y día. Ni la alerta ni el correo DEBERÁN llevar datos personales.
- **RF-4.7c** El motivo de error de una tarea y los registros (log) NO DEBERÁN contener texto de la
  usuaria: solo el paso, el tipo de error y un mensaje fijo. `LOG_LEVEL` DEBERÁ aplicarse.

### Cierre (RF-4.8)
- **RF-4.8** Antes de cerrar la fase, Mar DEBERÁ hacer la prueba final con 5 CV inventados y 5 casos que
  entre todos recorren todas las opciones de Horma (P8), siguiendo una guía con lo que se espera en cada
  paso, y anotar lo que falle.
- **RF-4.8b** Antes de cerrar la fase DEBERÁ existir `docs/revision-lineas-rojas.md`: cada prompt de los
  agentes activos y el flujo de aprobación frente a cada línea roja de la constitución, con su prueba y lo
  pendiente. La firma Mar (P9).

## Criterios de aceptación (puerta de salida)
- [ ] La suite de flujos y `evals/cv/` pasan con `PlainFlow` y con `LangGraphFlow` (simulado), y con la
      implementación activa con el modelo real en un PR.
- [ ] `horma flujo correr candidatura --usuaria ana --oferta 123 --paso-a-paso --traza trazas/` funciona
      con `HORMA_FLOW_IMPL=langgraph`.
- [ ] Una candidatura se para tras `componer`; al aprobar, los PDF descargados coinciden con el texto
      aprobado (también tras editar) y el checkpoint se borra (test). Si la reanudación falla, la
      candidatura sigue aprobada y las descargas funcionan (test).
- [ ] Un PR con un umbral en rojo no se puede fusionar (se comprueba una vez a propósito); el umbral ATS
      0,75 está en el archivo de umbrales.
- [ ] `horma eval correr red-teaming`: 100 % sin efecto, en simulado y con el modelo real.
- [ ] Lighthouse marca la web como instalable; sin red se ve «Sin conexión».
- [ ] El perfil de producción arranca en local con HTTPS, sin puertos de API ni de base de datos
      publicados, y la API se niega a arrancar con secretos de desarrollo (test).
- [ ] Pasarse de un límite de ritmo da 429 (test).
- [ ] `/costes` muestra coste y errores sin datos personales; una alerta forzada se ve, se registra y
      envía su correo (test con SMTP simulado).
- [ ] Ningún motivo de error ni registro contiene texto de la usuaria (test).
- [ ] Prueba final de Mar con los 5 casos hecha y anotada; revisión de líneas rojas firmada.
- [ ] Despliegue real: **bloqueado hasta la respuesta del profesor** (P6). No impide cerrar el resto de la
      fase, pero la fase no se da por cerrada del todo hasta hacerlo o hasta que se descarte.

## Riesgos
- **Gasto:** cada PR con el modelo real cuesta unos pocos USD (tope de 1 USD por set, 8 sets).
- **Forma de trabajar:** con la protección de rama ya no se puede hacer push directo a `main`; todo va
  por PR.
- **Datos en el checkpoint:** guarda CV y carta mientras dura la pausa; por eso se borra al entregar o
  cerrar (RF-4.3e).
- **Despliegue real:** coste mensual y Horma expuesta a internet; queda a la espera del profesor (P6).
- **Falsos positivos de la capa de entrada:** marca pero no bloquea, así que un falso positivo solo
  produce un aviso de más.

## Fuera de alcance
Ver [clarifications.md](./clarifications.md#fuera-de-alcance-anotado-no-se-construye-aquí).
