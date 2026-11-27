---
type: plan
title: langgraph-salida — Plan técnico
description: Arquitectura, contratos y modelo de datos que cubren cada requisito de la fase 4 (LangGraphFlow con pausa y checkpointer, CI bloqueante, guardarraíles y red teaming, PWA y despliegue, costes y alertas, cierre).
tags: [plan, langgraph, ci, guardarrailes, despliegue, observabilidad]
status: active
sources: [./spec.md, ./clarifications.md, ../system.md, ../003-candidatura/plan.md]
generated: { at: 2026-11-16 }
verified: { by: human, at: 2026-11-16 }
stale_after: null
---

# langgraph-salida — Plan

## Arquitectura
```
horma/
  flows/     base.py (Flow con pausas y reanudar), plain.py (pausa), grafo.py (LangGraphFlow, nuevo),
             candidatura.py (pasos y aristas compartidos + paso entregar + CLAVES_ESTADO),
             registry.py (elige la implementación con HORMA_FLOW_IMPL)
  llm/       vigilancia.py (señales de entrada y fuga del prompt, nuevo); gateway.py y metricas.py
             las aplican y registran
  config.py  flow_impl, umbrales de alerta, SMTP
  cli.py     flujo correr: pausa y --aprobar; eval correr: umbrales desde archivo, sin --umbral
  evals.py   lee evals/umbrales.json; umbral ATS; set red-teaming
  web/       migración 0008; checkpointer.py (PostgresSaver, nuevo); services y repositories de
             candidaturas (reanudar al aprobar, PDF guardados); costes (router, service, repository
             y static/costes.{html,js}, nuevos); alertas.py (nuevo); limites.py (límite de ritmo
             general, nuevo); main.py (cabeceras, arranque en producción, /salud); queue/worker.py
             (hilo, motivo de error saneado, comprobación de alertas); static/ (manifest, sw.js,
             offline.html, iconos)
evals/umbrales.json (nuevo) · evals/red-teaming/ (nuevo) · docker-compose.prod.yml + Caddyfile (nuevos)
.env.produccion.example (nuevo) · .github/workflows/ci.yml (job evals-reales)
docs/revision-lineas-rojas.md · plan de pruebas y CV de prueba (gitignorados, retirados)
```

- **Una sola definición del flujo:** `candidatura.py` define una vez `PASOS`, `ARISTAS`, `inicio`,
  `pausas={"entregar"}` y `finales={"entregar"}`. `PlainFlow` y `LangGraphFlow` se construyen con esos
  mismos datos. Ninguna función de paso ni de decisión cambia, salvo que se añade `entregar` y la
  arista `componer → entregar`.
- **Fronteras:** import-linter prohíbe a `horma.flows` importar psycopg o sqlalchemy (`pyproject.toml:94-97`).
  Por eso `horma.flows.grafo` importa `langgraph` pero no `langgraph.checkpoint.postgres`. El
  `PostgresSaver` se crea en `horma.web.checkpointer` y se inyecta. Los tests y la consola usan
  `InMemorySaver`. Se añade un contrato: solo `horma.flows.grafo` importa `langgraph`.
- **Dependencias:** `langgraph` y `langgraph-checkpoint-postgres` (versiones fijadas en `uv.lock`).
  Usan psycopg 3, el mismo que ya tiene el proyecto. Todo sigue siendo síncrono. Si `uv` falla con
  certificados: `--system-certs`.

## Interfaz `Flow` (cambio de contrato, RT-12)
```python
class Flow(Protocol):
    nombre: str
    inicio: str
    pausas: set[str]                       # pasos antes de los que el flujo se para (vacío en los lineales)
    def run(self, estado: dict, *, hilo: str | None = None) -> dict: ...
    def reanudar(self, hilo: str, cambios: dict, estado: dict | None = None) -> dict: ...
    def run_step(self, paso: str, estado: dict) -> dict: ...
    def siguiente(self, paso: str, estado: dict) -> str | None: ...
    def pasos(self) -> list[str]: ...
```
- `run` recorre hasta un paso final o hasta el paso anterior a una pausa. Devuelve el estado con
  `en_pausa` = nombre del paso pendiente (o `None`).
- **`PlainFlow.reanudar`** necesita `estado` (no guarda nada). Le aplica `cambios` y sigue desde el
  paso en pausa. El estado pausado de `PlainFlow` es la fila de la candidatura.
- **`LangGraphFlow.reanudar`** lee el hilo del checkpointer, aplica `cambios` con `update_state` y
  continúa con `invoke(None, config)`. Ignora `estado`. Si no hay checkpoint, lanza `ErrorDePaso`.
- Los flujos lineales siguen igual, con `pausas = set()`. Su `reanudar` lanza un error.

## `LangGraphFlow` (`horma/flows/grafo.py`)
- **Estado:** `StateGraph` con un `TypedDict` generado a partir de los campos de `EstadoCandidatura`
  más `CLAVES_INTERNAS`, que se declaran en `candidatura.py` (`errores_cv`, `errores_carta`,
  `errores_formato`, `palabras_sugeridas`, `ausentes_sin_origen`, `huecos_redactor`, `rehacer`,
  `cv_base_contenido`, `cv_maestro`, `cvs_base`, `oferta`, `usuaria_id`, `perfil_version`,
  `en_pausa`, `cv_pdf`, `carta_pdf`). Sin reductores: cada nodo sobrescribe. Un test comprueba que
  todas las claves que escriben los pasos están declaradas.
- **Nodos:** `add_node(nombre, paso)` por cada paso de `PASOS`. **Aristas:** las de destino fijo con
  `add_edge` y las de decisión (`tras_comprobar`, `tras_juzgar`) con `add_conditional_edges`, con el
  mapa de destinos posibles. Los finales van a `END`.
- **Compilación:** `compile(checkpointer=…, interrupt_before=list(pausas))`. `run` usa `invoke` con
  `{"configurable": {"thread_id": hilo}}`. Sin `hilo` (consola y evals) usa un `InMemorySaver` y un
  hilo efímero.
- **Consola (RF-4.1b):** `run_step` llama a la función del paso y `siguiente` evalúa la arista. Son las
  mismas funciones que usa el grafo, así que `horma flujo correr` no cambia. Las excepciones se
  envuelven en `ErrorDePaso`, igual que en `PlainFlow`.
- **Equivalencia:** con la misma `ProveedorSimulado`, las dos implementaciones dan el mismo estado
  final y las mismas `llamadas`. La suite lo comprueba caso a caso.

## Pausa y entrega (RF-4.3)
| Momento | Qué pasa |
|---|---|
| Worker prepara | `crear(proveedor, checkpointer=PostgresSaver).run(estado, hilo=f"candidatura-{id}")` corre hasta `componer` y se para. El worker guarda lo de siempre (`guardar_preparacion`). |
| Usuaria edita | Como en la fase 3 (`services.editar`), solo en la fila. No toca el checkpoint. |
| Reintentar | Antes de encolar, se borra el hilo (`delete_thread`) para que la preparación empiece de cero. |
| Aprobar | `services.aprobar`: en la misma sesión, primero la transición a `aprobada` (como ahora). Después, `reanudar(hilo, {"cv_contenido", "carta_contenido"} de la fila, estado=fila)`. `entregar` llama a `generar_pdf` dos veces y deja `cv_pdf` y `carta_pdf` en el estado. El servicio guarda los bytes en `candidaturas` y borra el hilo. |
| Falla la reanudación | La aprobación ya está guardada. Se registra el error (paso y tipo, sin texto) y las descargas generan el PDF al momento (RF-4.3d). |
| Cerrar | `services.cerrar` borra el hilo si existe (RF-4.3e). |
| Descargar | `documento_pdf` sirve `cv_pdf`/`carta_pdf` si existen; si no, los genera como ahora. |

- `entregar` es código puro: no llama al modelo y no cambia `estado` (lo cambia el servicio).
  Solo se llega a él con `reanudar`, que solo llama `services.aprobar` tras comprobar la sesión de la
  dueña (RF-4.3f, RT-10).
- **Consola:** `flujo correr candidatura` se para en la pausa e imprime «En pausa: falta la aprobación».
  Con `--aprobar` sigue con `entregar` y, si hay `--traza`, guarda los dos PDF en la carpeta (datos
  inventados).
- **Evals `cv`:** los casos de flujo terminan en la pausa; no necesitan `entregar`.

## Modelo de datos (migración 0008, reversible)
| Tabla | Cambio |
|---|---|
| `candidaturas` | `+ cv_pdf bytea`, `+ carta_pdf bytea`, `+ entregada_en timestamptz` (misma RLS «propia») |
| `llm_llamadas` | `+ senales_entrada text[]` (solo tipos de señal; nunca texto) |
| `alertas` (nueva) | `id`, `tipo` (`gasto_dia`, `tasa_errores`), `valor`, `umbral`, `creada_en`, `correo_enviado` (bool). Sin datos personales. Solo el modo sistema escribe; la leen los admins, igual que la ingesta |
| Checkpointer | La migración ejecuta `PostgresSaver.setup()` con la conexión del migrador y da a `horma_app` SELECT, INSERT, UPDATE y DELETE sobre sus tablas (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`). Sin RLS por usuaria: no tienen columna de usuaria y solo las tocan el worker y la API. `downgrade` las borra |
| `tareas` | Los `motivo_error` existentes pasan al formato saneado (datos de prueba) |

`horma.web.checkpointer.crear(engine_url)` abre una conexión psycopg con `autocommit=True` y
`row_factory=dict_row`, como pide `PostgresSaver`.

## Evals y CI (RF-4.4)
- **`evals/umbrales.json`:** por set, el umbral por campo, los campos exigidos al 100 % y, en `cv`,
  `cobertura_ats_media: 0.75`. `evals.py` lo lee y `SETS` deja de llevar umbrales en código. La opción
  `--umbral` de `horma eval correr` desaparece. La cobertura ATS pasa a contar para `aprobado`, con la
  media de los casos de flujo completo.
- **`--flujo plain|langgraph`** en `horma eval correr cv`. Por defecto, `HORMA_FLOW_IMPL`.
- **`.github/workflows/ci.yml`:**
  - `secretos` sigue igual.
  - `calidad` (push y PR): ruff, lint-imports, pytest (la suite de flujos se parametriza por las dos
    implementaciones) y los 8 sets con `--simulado`; `cv` se corre con las dos implementaciones.
  - **`evals-reales`** (nuevo): solo con `pull_request` hacia `main` y con `workflow_dispatch`; el job siempre
    corre en esos PR, pero solo llama al modelo si cambian `horma/`, `evals/`, `config/`, las dependencias o
    `ci.yml` (refinamiento de P3, 17-nov); un push nuevo cancela la ejecución anterior. Hace
    `needs: calidad`, tiene `ANTHROPIC_API_KEY` y `HORMA_FLOW_IMPL=langgraph`, y corre con el
    modelo real y `--tope-coste 1.0` todos los sets salvo `recomendacion`, que queda fuera hasta el plan
    del `matcher` (con el modelo real su `nota` da 0,67-0,71 frente a 0,9; sigue en `calidad`, simulado). Si la clave está vacía, falla con un mensaje claro y no pasa a
    simulado. Sube `evals/resultados/`.
- **Clave vacía:** resuelto en T11. Se volvió a fijar con `gh secret set ANTHROPIC_API_KEY` y llega
  bien. Un paso comprueba solo que no esté vacía, nunca imprime su valor.
- **Protección de `main`** (la activa Mar en GitHub, Settings → Branches): exigir PR, y exigir en verde
  `secretos`, `calidad` y `evals-reales`. Activa desde T11 (también para administradores): ya no se
  puede hacer push directo a `main`.

## Guardarraíles (RF-4.5)
- **`horma/llm/vigilancia.py`** (código puro):
  - `senales_entrada(texto) -> list[TipoSenal]` detecta `orden_a_ia` («ignora las instrucciones»,
    «eres un…», «system:», «a partir de ahora»), `accion_prohibida` (enviar, aprobar, marcar como
    enviada, revelar instrucciones o datos), `texto_oculto` (caracteres de ancho cero y etiquetas
    Unicode) y `bloque_codificado` (base64 o hex largos). Patrones en español e inglés.
  - `fuga_prompt(salida, prompt) -> bool` da verdadero si la salida contiene un fragmento literal del
    prompt de 120 caracteres o más. Se excluyen las listas de fórmulas cerradas
    (`FORMULAS_CORTESIA`) para no marcar los saludos de la carta.
- **Puerta única (`gateway.completar`):** antes de llamar, calcula las señales de la entrada
  serializada y las pasa a `metricas` (columna `senales_entrada`). No bloquea. Después de validar el
  esquema, si `fuga_prompt` da verdadero, se trata como una salida inválida (reintento y
  `SalidaInvalida`, RT-03).
- **Flujo `candidatura`:** `comprobar` aplica `senales_entrada(texto_oferta)` y, si hay señales, añade
  un aviso de oferta con el texto fijo de RF-4.5b. Esto pide `documento = "oferta"` en `Aviso`
  (cambio pequeño de esquema) o un campo aparte `aviso_oferta`. Se elige al construir y es revisable.
- **`evals/red-teaming/`** (nuevo set, código como los demás en `evals.py`):
  - **Ofertas** (unas 10): pasan por `procesar_oferta`, y 3 de ellas también por `candidatura` en
    simulado o real.
  - **Correos** (unos 10): pasan por `clasificar_respuesta`.
  - **Campos exigidos al 100 %:** `sin_efecto` (la salida es la esperada), `registrada` (las
    instrucciones están en `instrucciones_embebidas`), `marcada` (al menos una señal de entrada),
    `sin_fuga` (ni fragmentos del prompt ni correos o teléfonos que no estén en las fuentes) y
    `estado_intacto` (ninguna transición ni `en_pausa` saltado).
  - Todo inventado.

## Salida: PWA y despliegue (RF-4.6)
- **PWA:**
  - `static/manifest.webmanifest` (nombre, colores de la identidad del proyecto, iconos de 192 y
    512 px y uno *maskable*).
  - `/sw.js`, servido en la raíz para que su alcance sea toda la web: guarda en caché solo `/static/*`
    y `offline.html` y nunca `/api/*`.
  - En la CSP, `manifest-src 'self'` y `worker-src 'self'`.
- **`docker-compose.prod.yml`** (se superpone al de desarrollo):
  - Postgres y la API con `ports: !reset []`.
  - Servicio `caddy` (imagen oficial, versión fijada) que publica 80 y 443 y usa un `Caddyfile` con
    `{$HORMA_DOMINIO} { reverse_proxy api:8000 }` y un volumen para los certificados.
  - `restart: unless-stopped` en todos los servicios y `healthcheck` en la API contra `/salud` (nuevo,
    sin datos).
  - La API arranca con `uvicorn --proxy-headers --forwarded-allow-ips <red interna>`.
  - En local, con `HORMA_DOMINIO=localhost`, Caddy usa su CA interna: hay HTTPS, con un aviso del
    navegador.
- **`main.py`:**
  - Cabeceras: con `APP_ENV=produccion`, `Strict-Transport-Security` y `Permissions-Policy`.
  - Arranque en producción: se niega a arrancar si `SESSION_SECRET` es corto (menos de 32) o es el
    del ejemplo, si una contraseña de la BD es la del ejemplo o si `GOOGLE_REDIRECT_URI` no es https.
- **`.env.produccion.example`:** claves sin valor. Hay que añadir `!.env.produccion.example` a
  `.gitignore`, porque hoy ignora `.env.*`.
- **`web/limites.py`:** generaliza la ventana en memoria de `auth/claves.py:24-40`. Límites
  configurables en `.env`: login por IP, subida de CV, y creación y reintento de candidaturas por
  usuaria (estas dos cuestan dinero). Al pasarse, 429 con un mensaje en llano.
- **Despliegue real:** de momento local con Compose y PostgreSQL; Vercel, más adelante (P6, 17-nov-2026).

## Observabilidad (RF-4.7)
- **`/costes`** (página y `GET /api/costes`, solo admins; mismo patrón que `/ingesta`):
  `repositories/costes.py` agrega `llm_llamadas` por día (últimos 30), agente y modelo (coste,
  llamadas, tokens, latencia media, tasa de `resultado != ok`), las tareas en `error` por tipo y las
  alertas abiertas. Sin `tarea_id` ni `usuaria_id` en la respuesta.
- **`web/alertas.py`:**
  - `comprobar(engine, ajustes, ahora)` calcula el gasto del día y la tasa de errores de la última
    hora (mínimo `ALERTA_MIN_LLAMADAS`). Si se pasa un umbral y no hay alerta de ese tipo hoy, la crea,
    escribe una línea en el log y envía el correo.
  - El correo sale por `smtplib` con STARTTLS, con texto fijo: tipo, valor, umbral y enlace a
    `/costes`.
  - El worker la llama cada `ALERTA_INTERVALO_MIN` (5 por defecto) dentro de su bucle.
  - Sin `SMTP_HOST`, solo hay pantalla y log, con un aviso al arrancar.
- **Motivo de error saneado:** en `worker.py:254`, `motivo_error = motivo_seguro(e)`, que devuelve el
  paso y un mensaje fijo por tipo (`TopeSuperado`, `SalidaInvalida`, `ErrorDePaso` y uno genérico).
  El log usa lo mismo. `logging.basicConfig(level=LOG_LEVEL)` en el worker y en la API.
- **Config nueva en `.env.example`:** `HORMA_FLOW_IMPL`, `ALERTA_GASTO_DIA_USD`, `ALERTA_TASA_ERRORES`,
  `ALERTA_MIN_LLAMADAS`, `ALERTA_INTERVALO_MIN`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USUARIO`,
  `SMTP_PASSWORD`, `ALERTAS_CORREO`, los límites de ritmo nuevos y `HORMA_DOMINIO`.

## Cierre (RF-4.8)
- **CV de prueba** (gitignorados, retirados): 5 CV inventados de sectores distintos. **Plan de pruebas manual**
  (gitignorado, retirado): los 5 casos, cada uno con los pasos y lo que se espera. Entre los 5 cubren:
  - perfil y CV base, con historial de versiones;
  - recomendaciones;
  - candidatura `lista` y `pendiente_de_ti`;
  - editar, aprobar y descargar (PDF fijos);
  - enviada, entrevista, rechazo y descartada;
  - reintentar tras un error y el tope de coste;
  - oferta adversaria con su aviso;
  - PWA instalada en el móvil;
  - admin: ingesta, `/costes` y una alerta forzada;
  - consola paso a paso con `langgraph`.

  Mar ajusta los casos antes de empezar.
- **`docs/revision-lineas-rojas.md`:** una tabla por línea roja (origen, texto no fiable, aprobación,
  art. 9, edad y nacionalidad, sin LinkedIn ni Indeed, datos inventados) frente a cada `prompt.md` de
  los agentes activos y frente al flujo de aprobación. En cada celda va la prueba (test, eval o línea
  del prompt) o «falta». Lo que falte se arregla o se anota. Firma de Mar.

## Requisito → componente
| Requisito | Componente | Prueba |
|---|---|---|
| RF-4.1, 4.1b | `flows/grafo.py`, `flows/candidatura.py` | Suite parametrizada; consola con `langgraph` |
| RF-4.2 | `flows/registry.py`, `config.py`, `evals.py --flujo` | Mismo estado final y llamadas con las dos; `eval cv` con las dos |
| RF-4.3-4.3f | `web/checkpointer.py`, `services/candidaturas.py`, migración 0008 | Tests de pausa, aprobar, fallo, cerrar y borrado del hilo |
| RF-4.4-4.4d | `evals/umbrales.json`, `evals.py`, `ci.yml`, protección de rama | Test de umbrales; PR en rojo que no se puede fusionar |
| RF-4.5-4.5e | `llm/vigilancia.py`, `gateway.py`, `metricas.py`, `evals/red-teaming/` | Tests de vigilancia; eval `red-teaming` al 100 % |
| RF-4.6-4.6e | `static/`, `docker-compose.prod.yml`, `Caddyfile`, `main.py`, `web/limites.py` | Lighthouse; arranque en producción; 429 |
| RF-4.7-4.7c | `routers/costes.py`, `web/alertas.py`, `worker.py` | Tests de `/costes` sin datos personales, alertas con SMTP simulado y motivo saneado |
| RF-4.8, 4.8b | Plan de pruebas manual (retirado), `docs/revision-lineas-rojas.md` | Prueba de Mar y firma |

## Decisiones del plan (revisables)
- El módulo se llama `grafo.py`, no `langgraph.py`, para que no se confunda con el paquete `langgraph`.
- `PlainFlow` sigue en el código y en la suite: es la referencia y sirve de respaldo si LangGraph da
  problemas.
- La reanudación al aprobar es síncrona, en la petición de la API: `entregar` no llama al modelo y
  tarda lo que dos `generar_pdf`. No pasa por la cola.
- El modelo real corre en CI con la implementación activa (`langgraph`); `plain` se comprueba en
  simulado. Así no se duplica el gasto.
- Las señales de entrada se registran en la puerta única, para cubrir a todos los agentes con un solo
  punto.

## Riesgos
- **API de LangGraph:** cambia entre versiones (nombres del saver en memoria, `delete_thread`). Se
  fijan las versiones y los tests cubren cada llamada que se usa.
- **`PostgresSaver.setup()`** crea sus propias tablas y migraciones internas. Al llamarlo desde la
  0008, una subida de versión de la librería puede pedir otra migración nuestra.
- **Bytes en el checkpoint:** los PDF viajan en el estado del grafo hasta que el servicio los guarda.
  Si el serializador diera problemas, `entregar` los devuelve en base64.
- **Falsos positivos de `fuga_prompt`** en la carta: se mitigan con el mínimo de 120 caracteres y la
  exclusión de las fórmulas. Hay un test con una carta normal.
- **Límites de ritmo en memoria:** valen mientras haya un solo proceso de API.
