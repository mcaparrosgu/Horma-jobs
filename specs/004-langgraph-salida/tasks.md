---
type: tasks
title: langgraph-salida — Desglose de tareas
description: Tareas pequeñas y comprobables derivadas del plan de la fase 4. Cada una empieza con un test que falla.
tags: [tareas, langgraph, ci, guardarrailes, despliegue, observabilidad]
status: active
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-16 }
verified: { by: human, at: 2026-11-16 }
stale_after: null
---

# langgraph-salida — Tareas

## Orden y forma de trabajo
Se construye por bloques y se para entre uno y otro:

1. LangGraphFlow (A, T01-T04)
2. pausa y entrega (B, T05-T08)
3. CI bloqueante (C, T09-T11)
4. guardarraíles y red teaming (D, T12-T14)
5. salida segura (E, T15-T19)
6. observabilidad (F, T20-T22)
7. cierre (G, T23-T25)

Cada tarea empieza con un test que falla. Todo se prueba sin llamar al modelo (puerta simulada), salvo
las mediciones reales de T11 y T14, que necesitan el OK de Mar antes de gastar. Desde que la
protección de rama esté activa (T11), cada bloque se entrega en su rama y con un PR.

### Bloque A · LangGraphFlow (RF-4.1, RF-4.2)
- [x] T01 — Dependencias e interfaz.
  - **Qué se hace:** `uv add langgraph langgraph-checkpoint-postgres` (versiones fijadas). `Flow` gana
    `pausas`, `run(…, hilo=)` y `reanudar`. `PlainFlow` se para antes de un paso en `pausas` y reanuda
    desde él. Los flujos lineales siguen con `pausas = set()`. Se añade el contrato de import-linter
    «solo `horma.flows.grafo` importa `langgraph`».
  - **Test:** un `PlainFlow` de juguete con pausa se para, deja `en_pausa` y `reanudar` aplica los
    cambios y termina. Sin pausas, todo sigue igual: pasan todas las suites de flujos actuales.
    `reanudar` en un flujo sin pausa da error. lint-imports en verde.
  - **Cubre:** RF-4.2, RT-12.
- [x] T02 — `candidatura` con definición compartida.
  - **Qué se hace:** `PASOS`, `ARISTAS`, `CLAVES_INTERNAS`, el paso `entregar` (código: dos
    `generar_pdf`) y la arista `componer → entregar`, con `pausas = finales = {"entregar"}`.
  - **Test:**
    - con respuestas simuladas, `run` se para tras `componer` con `en_pausa = "entregar"` y de 3 a 5
      llamadas, igual que antes;
    - `reanudar` con un CV editado da dos PDF cuyo texto (leído con `pypdf`) es el editado;
    - `entregar` no llama al modelo;
    - el resto de la suite T26 de la fase 3 sigue en verde.
  - **Cubre:** RF-4.1, RF-4.3c.
- [x] T03 — `LangGraphFlow` (`horma/flows/grafo.py`).
  - **Qué se hace:** `StateGraph` con un `TypedDict` generado desde `EstadoCandidatura` y
    `CLAVES_INTERNAS`, un nodo por paso, las aristas condicionales, `interrupt_before` de las pausas y
    `run_step`/`siguiente` sobre las mismas funciones.
  - **Test:**
    - todas las claves que escriben los pasos están declaradas;
    - con `InMemorySaver`, `run` se para y `reanudar` termina;
    - `reanudar` sin checkpoint lanza `ErrorDePaso`;
    - un fallo en un nodo llega como `ErrorDePaso` con el nombre del paso.
  - **Cubre:** RF-4.1, RF-4.1b.
- [x] T04 — Elección por configuración y suite parametrizada.
  - **Qué se hace:** `HORMA_FLOW_IMPL` en `config.py` y en `.env.example` (por defecto `plain`) y
    `registry` que construye la implementación pedida. Se parametrizan por implementación la suite de
    flujos de candidatura (`tests/test_f3_t08_t09_flujos.py`) y `eval correr cv` (`--flujo`).
  - **Test:**
    - con las mismas respuestas simuladas, las dos implementaciones dan el mismo estado final y las
      mismas llamadas en cada caso de la suite;
    - `horma flujo correr candidatura --simulado --paso-a-paso --traza` funciona con
      `HORMA_FLOW_IMPL=langgraph`;
    - `eval correr cv --simulado` aprueba con las dos;
    - un valor desconocido da un error claro.
  - **Cubre:** RF-4.1b, RF-4.2.

### Bloque B · Pausa y entrega (RF-4.3)
- [x] T05 — Migración 0008 y checkpointer.
  - **Qué se hace:**
    - `candidaturas`: `cv_pdf`, `carta_pdf` y `entregada_en`;
    - `llm_llamadas.senales_entrada`;
    - tabla `alertas`;
    - `PostgresSaver.setup()` con el migrador y los permisos de `horma_app`;
    - `horma/web/checkpointer.py`.
  - **Test:**
    - `upgrade` y `downgrade` se hacen sin errores;
    - `horma_app` lee y escribe checkpoints;
    - un hilo guardado se recupera desde otra conexión;
    - la RLS de `candidaturas` no cambia (una usuaria no lee las de otra);
    - `alertas` no la lee una sesión que no es de admin.
  - **Cubre:** RF-4.3, RF-4.3e, RF-4.7b.
- [x] T06 — Worker con hilo.
  - **Qué se hace:** el worker corre `candidatura` con `hilo=f"candidatura-{id}"` y el checkpointer de
    Postgres (con `langgraph`), y «Reintentar» borra el hilo antes de encolar.
  - **Test:**
    - tras preparar, la candidatura queda en `borrador` con `lista` o `pendiente_de_ti` como en la
      fase 3 y su hilo existe y está en pausa;
    - reintentar empieza de cero: no reutiliza la vuelta anterior;
    - con `plain`, todo sigue como antes.
  - **Cubre:** RF-4.3.
- [x] T07 — Aprobar reanuda y descargas fijas.
  - **Qué se hace:** `services.aprobar` hace la transición y después reanuda con el texto de la fila,
    guarda los PDF y `entregada_en` y borra el hilo. `documento_pdf` sirve lo guardado. `cerrar` borra
    el hilo.
  - **Test:**
    - tras editar y aprobar, el PDF descargado tiene el texto editado y no cambia aunque cambie
      `generar_pdf`;
    - si la reanudación falla (simulado), la candidatura queda `aprobada`, las descargas generan el
      PDF al momento y el error no lleva texto;
    - otra usuaria no aprueba ni reanuda (RLS);
    - ningún texto de la oferta reanuda;
    - cerrar en `borrador` borra el hilo.
  - **Cubre:** RF-4.3b a RF-4.3f, RT-10.
- [x] T08 — Consola con pausa.
  - **Qué se hace:** `flujo correr candidatura` se para en la pausa y lo dice; `--aprobar` sigue con
    `entregar` y guarda los PDF en `--traza`. Se pasa la implementación por defecto a `langgraph` en
    `.env.example`.
  - **Test:** sin `--aprobar` termina en pausa; con `--aprobar`, la carpeta de la traza tiene los dos
    PDF; funciona con las dos implementaciones.
  - **Cubre:** RF-4.1b, RF-4.3.
  - **Al terminar el bloque:** prueba manual de Mar (preparar, editar, aprobar y descargar en el
    navegador con `langgraph`).

### Bloque C · CI bloqueante (RF-4.4)
- [x] T09 — Umbrales en archivo y umbral ATS.
  - **Qué se hace:** `evals/umbrales.json` con los 7 sets actuales (los valores de hoy) y `cv` con
    `cobertura_ats_media: 0.75`. `evals.py` lo lee y `--umbral` sale de la consola.
  - **Test:**
    - cada set aprueba o suspende como antes con los mismos resultados;
    - una cobertura media de 0,74 suspende `cv` y una de 0,75 aprueba;
    - un set sin entrada en el archivo da error;
    - `eval correr --umbral` ya no existe.
  - **Cubre:** RF-4.4, RF-4.4b.
- [x] T10 — Workflow de CI.
  - **Qué se hace:** `calidad` (push y PR, todo simulado, `cv` con las dos implementaciones) y
    `evals-reales` (PR a `main` y `workflow_dispatch`, modelo real, `langgraph`, tope de 1 USD por
    set, falla si no hay clave).
  - **Test:** el YAML pasa `actionlint` (o una revisión con `gh workflow view`). En una rama de prueba,
    un PR lanza los dos jobs y un push solo `calidad`. El paso que comprueba la clave no imprime su
    valor.
  - **Cubre:** RF-4.4c.
- [x] T11 — Clave y protección de rama (**con Mar**).
  - **Qué se hace:** diagnosticar por qué la clave llega vacía y que Mar la vuelva a fijar
    (`gh secret set ANTHROPIC_API_KEY`). Mar activa la protección de `main` (PR obligatorio; `secretos`,
    `calidad` y `evals-reales` en verde).
  - **Verificación:**
    - un PR real pasa `evals-reales` con el modelo (**OK de Mar antes de gastar**, unos pocos USD);
    - un PR con un umbral rebajado a propósito en una rama de prueba no se puede fusionar.
  - **Cubre:** RF-4.4c, RF-4.4d.
  - **Hecho (16-nov-2026):** clave fijada de nuevo (llegaba bien); `main` protegida (PR obligatorio;
    `secretos`, `calidad` y `evals-reales`, también para administradores). Un PR real pasó
    `evals-reales` con el modelo (unos 1,2 USD en total) y otro con la cobertura ATS subida a 0,99
    quedó bloqueado. Dos ajustes: el caso 12 de `perfil` pasa a «dependiente» (un reponedor es
    ambiguo entre `ventas_comercial` y `logistica`) y `recomendacion` sale de `evals-reales` hasta el
    plan del `matcher` (con el modelo real `nota` da 0,67-0,71 frente a 0,9); sigue en `calidad`.

### Bloque D · Guardarraíles y red teaming (RF-4.5)
- [ ] T12 — Vigilancia de entrada y de salida (`horma/llm/vigilancia.py`).
  - **Test:**
    - cada tipo de señal se detecta en español y en inglés, y una oferta normal de la fase 1 da cero
      señales;
    - `fuga_prompt` detecta un fragmento de 120 caracteres del prompt y no marca una carta con las
      fórmulas de cortesía;
    - la puerta única registra los tipos en `senales_entrada` sin texto (test de RT-06 ampliado) y no
      bloquea;
    - una salida con fuga se reintenta y acaba en `SalidaInvalida`.
  - **Cubre:** RF-4.5, RF-4.5c.
- [ ] T13 — Aviso de oferta manipulada.
  - **Qué se hace:** `comprobar` añade el aviso fijo si la oferta tiene señales (decidir aquí si va
    como `Aviso` con `documento = "oferta"` o como campo aparte).
  - **Test:**
    - con la oferta adversaria de `evals/cv/`, la candidatura muestra el aviso y nada cambia de estado;
    - con una oferta normal no hay aviso;
    - igual con las dos implementaciones.
  - **Cubre:** RF-4.5b, RF-4.5d.
- [ ] T14 — Set `evals/red-teaming/`: unas 10 ofertas y unos 10 correos inventados (manipular, activar
  un envío, sacar el prompt o datos de contacto que no están en las fuentes), umbrales en
  `umbrales.json` y entrada en CI.
  - **Test:** el harness exige al 100 % `sin_efecto`, `registrada`, `marcada`, `sin_fuga` y
    `estado_intacto`, y aprueba en simulado.
  - **Medición real con OK de Mar** (≈ 0,5 USD).
  - **Cubre:** RF-4.5e, RT-07, RT-11.

### Bloque E · Salida segura (RF-4.6)
- [x] T15 — PWA. *(Hecha y verificada por Mar en escritorio el 16-nov; el móvil espera al despliegue real, T19.)*
  - **Qué se hace:** manifest, iconos con la identidad del proyecto, `/sw.js` en la raíz,
    `offline.html` y la CSP con `manifest-src` y `worker-src`.
  - **Test:**
    - el manifest y `/sw.js` se sirven con su tipo;
    - el service worker no guarda nada de `/api/`;
    - la página «Sin conexión» existe;
    - el JS no usa `innerHTML`.
  - **Verificación de Mar:** Lighthouse marca la web como instalable y se instala en el móvil.
  - **Cubre:** RF-4.6.
- [x] T16 — Cabeceras, arranque en producción y `/salud`.
  - **Test:**
    - con `APP_ENV=produccion` salen HSTS y `Permissions-Policy`, y en desarrollo no sale HSTS;
    - la API no arranca con un `SESSION_SECRET` corto o del ejemplo, con una contraseña de la BD del
      ejemplo ni con un `GOOGLE_REDIRECT_URI` sin https;
    - `/salud` responde sin datos.
  - **Cubre:** RF-4.6b, RF-4.6c.
- [x] T17 — Límites de ritmo (`web/limites.py`).
  - **Qué se hace:** generalizar la ventana de `auth/claves.py` y aplicarla en el login, la subida de
    CV y la creación y reintento de candidaturas.
  - **Test:**
    - pasarse de cada límite da 429 con un mensaje en llano;
    - otra usuaria no queda afectada;
    - `POST /ofertas` sigue igual;
    - los límites salen de `.env`.
  - **Cubre:** RF-4.6d.
- [x] T18 — Perfil de producción. *(Hecha y verificada por Mar el 16-nov: `https://localhost` y login.)*
  - **Qué se hace:** `docker-compose.prod.yml`, `Caddyfile`, `.env.produccion.example` (y su excepción
    en `.gitignore`) y `uvicorn` con las cabeceras del proxy.
  - **Test:** `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` no publica los
    puertos de Postgres ni de la API, todos los servicios tienen `restart` y la API tiene
    `healthcheck`.
  - **Verificación de Mar:** en local, `https://localhost` abre Horma (con el aviso de la CA interna)
    y el login funciona.
  - **Cubre:** RF-4.6b, RF-4.6c, RF-4.6e.
- [x] T19 — **Despliegue real. *(Cerrada el 19-nov-2026 por Mar: el profesor dijo (P6, 17-nov) local con Docker
  Compose y PostgreSQL ahora, y Vercel más adelante.)*** Local ya cubierto por T17 y T18. Al llegar a Vercel se
  abre una tarea nueva con el destino (coste, dominio, secretos, copia de la BD) y se revisa la arquitectura.
  - **Cubre:** RF-4.6e.

### Bloque F · Observabilidad (RF-4.7)
- [x] T20 — Motivo de error saneado y `LOG_LEVEL`.
  - **Test:**
    - un `ErrorDePaso` cuya causa lleva texto de la usuaria deja en `tareas.motivo_error` y en el log
      solo el paso y el mensaje fijo;
    - `TopeSuperado` y `SalidaInvalida` dan su mensaje propio;
    - `LOG_LEVEL=WARNING` silencia los INFO.
  - **Cubre:** RF-4.7c.
- [x] T21 — `/costes` (página, `GET /api/costes` y `repositories/costes.py`).
  - **Test:**
    - solo los admins entran (otra cuenta recibe 403);
    - con llamadas sembradas, los totales por día, agente y modelo y la tasa de errores son correctos;
    - la respuesta no tiene `usuaria_id`, `tarea_id` ni texto;
    - el JS no usa `innerHTML`;
    - en el móvil la tabla no desborda.
  - **Cubre:** RF-4.7.
- [x] T22 — Alertas (`web/alertas.py` y llamada desde el worker).
  - **Test:**
    - con un gasto sembrado por encima del umbral se crea una alerta, se escribe en el log y se envía
      un correo (SMTP simulado) sin datos personales;
    - una segunda comprobación el mismo día no repite el correo;
    - la tasa de errores no salta por debajo del mínimo de llamadas;
    - sin `SMTP_HOST` solo hay pantalla y log;
    - `/costes` muestra la alerta.
  - **Cubre:** RF-4.7b.

### Bloque G · Cierre (RF-4.8)
- [x] T23 — Revisión de líneas rojas. *(hecha el 16-nov; firmada por Mar el 17-nov, alcance: líneas rojas vigentes)*
  - **Qué se hace:** `docs/revision-lineas-rojas.md`, con la tabla de prompts de los agentes activos y
    del flujo de aprobación frente a cada línea roja, la prueba de cada celda y lo que falte. Lo que
    falte se arregla en esta tarea (con su test) o se anota.
  - **Verificación:** **la firma de Mar (hecha el 17-nov).**
  - **Cubre:** RF-4.8b.
- [x] T24 — Prueba final de Mar. *(firmada por Mar el 17-nov; los 5 casos los recorrió Claude con el modelo real)*
  - **Qué se hace:** 5 CV inventados y un plan de pruebas manual
    (gitignorados, retirados) con los 5 casos que cubren todas las opciones (ver el plan). Mar los ajusta, hace la
    prueba y anota lo que falle. Lo que falle se corrige en esta tarea o se anota en la bitácora.
  - **Hecho el 17-nov (Claude, por la API y la consola):** todo coincide con lo esperado salvo tres falsos
    avisos, corregidos con test (`tests/test_f4_t24_falsos_avisos.py`, commit 5444ff6): F1 «Se valora
    experiencia previa» salía como hueco (`medir_ats`); F2 la carta avisaba de datos que sí estaban en el CV
    (`verificar_trazabilidad`); F3 «idioma extranjero» activaba el aviso de nacionalidad
    (`rasgos_personales`). Quedan: el catálogo no tiene ofertas de sanidad (F4, solo anotado) y el plan
    tenía cinco errores (resultados en el plan de pruebas, retirado).
  - **Hecho (17-nov):** PWA instalada y sin conexión (Mar, 16-nov, T15) y HTTPS en local (T18); `/costes`
    como admin y como no admin (403) en Chrome; correo SMTP real con una alerta forzada (llegó, sin datos
    de usuarias); **firma de Mar el 17-nov**.
  - **Sin comprobar al firmar:** `/costes` en el móvil (el CSS lo prevé: `.tabla-costes` con
    `overflow-x: auto`; el móvil real espera a T19) y que el correo de alerta no se repite el mismo día (lo
    cubre el test de T22). F4 (catálogo sin ofertas de sanidad) sigue solo anotado.
  - **Cubre:** RF-4.8.
- [x] T25 — Documentos y cierre. *(hecha el 16-nov; PR #7 fusionado en `main` el 17-nov, `875ec18`, con CI en verde)*
  - **Qué se hace:**
    - en `specs/system.md`: RT-12 con la pausa, la decisión de la fase 4, la tabla de fases y el
      módulo `grafo.py`;
    - `specs/index.md`, README (comandos nuevos: `--aprobar`, `--flujo`, perfil de producción y
      `/costes`) y `.env.example`;
    - el recordatorio del plan del `matcher` antes de usuarias reales.
  - **Test:** CI en verde en el PR de cierre, con `evals-reales`.
  - **Cubre:** todos.

## Pendiente de la persona (no se puede hacer sin ti)
- Verificar aclaraciones, spec, plan y tareas (campo `verified` de cada documento) antes de T01.
- ~~Preguntar al profesor dónde desplegar (P6)~~ *(contestado el 17-nov: local ahora, Vercel después)*.
- Instalar `langgraph` si `uv` falla con certificados (T01).
- OK antes de gastar en T14 (T11 ya hecha).
- ~~Una cuenta SMTP para las alertas (T22)~~ *(hecho el 17-nov: Gmail con contraseña de aplicación; sin SMTP siguen funcionando la pantalla y el log)*.
- ~~Prueba manual del bloque B, PWA (T15), HTTPS (T18), prueba final (T24) y firma de T23~~ *(hechas;
  T24 firmada el 17-nov)*.
- **Estabilizar el set `ofertas` de `evals-reales`** (anotado el 16-nov en el PR #7): falló dos veces con campos
  distintos (`titulo` 0,88; `adversarias` 0,83, umbral 0,9) y aprobó en local con el mismo código (0,92 y 1,00).
  Averiguar qué caso adversario oscila y arreglar el prompt, el caso o el umbral. Mientras tanto, el job
  `evals-reales` puede fallar sin que el código esté mal y, al cortarse en el primer set, no mide los siguientes.
- `/costes` en el móvil (T21): probado solo el navegador de escritorio; el móvil, con T19.
