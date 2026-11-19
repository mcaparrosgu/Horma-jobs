---
type: plan
title: candidatura — Plan técnico
description: Arquitectura, contratos y modelo de datos que cubren cada requisito de la fase 3. Regenerado el 16-nov-2026 con el cambio «simplificar la candidatura» (bloque H).
tags: [plan, candidatura, seguimiento]
status: active
sources: [./spec.md, ./clarifications.md, ../system.md, ../002-perfil-recomendacion/plan.md]
generated: { by: claude-code, at: 2026-11-16 }
verified: { by: human, at: 2026-11-16 }
stale_after: null
---

# candidatura — Plan

## Arquitectura
Estado tras el bloque H (lo que se quita está en «Qué cambia respecto a la versión construida»):

```
horma/
  schemas/   candidatura.py (Candidatura, EstadoCandidatura, EventoCandidatura, Hueco, Problema,
             Aviso, TrazaFrase; enumerados Estado, Preparacion, Canal, MotivoCierre,
             EtiquetaRespuesta; transicion() y transicion_por_respuesta(), funciones puras)
  agents/    redactor_cv/ (mayor), redactor_carta/ (mayor), juez_candidatura/ (mayor, nuevo),
             clasificador_respuesta/ (pequeño, solo consola)
  tools/     elegir_cv_base.py (nuevo), medir_ats.py, generar_pdf.py, comparar_versiones.py,
             verificar_trazabilidad.py, rasgos_personales.py
  flows/     candidatura.py (reescrito), clasificar_respuesta.py (sin cambios)
  llm/       metricas.capturar(tope=…) y TopeSuperado (arreglo del tope, RF-3.11)
  cli.py     agente correr juez-candidatura; sin selector ni jueces antiguos
  web/       migración 0007, services/ y routers/candidaturas.py, repositories/candidaturas.py,
             queue/worker.py, static/candidatura.{html,js}
evals/cv/ (14 casos, adaptados al juez único) · evals/respuestas/ (15 correos, sin cambios)
```

- **Camino de una candidatura:** «Preparar candidatura» en Recomendadas → `POST /api/candidaturas`
  crea la fila en `borrador` con `preparacion = en_curso` y encola `candidatura` → el worker carga
  oferta, perfil, CV maestro y sus CV base, ejecuta el flujo y guarda CV base elegido y motivo, CV,
  carta, trazas, huecos, avisos y `preparacion` (`lista`, `pendiente_de_ti` o `error`).
- **Dos campos, dos máquinas (sin cambios):** `estado` es la de la candidatura y solo la cambia ella;
  `preparacion` es el resultado del flujo. El flujo nunca cambia `estado`.
- **Fronteras (sin cambios):** agentes y herramientas sin base de datos ni disco; `generar_pdf`
  devuelve bytes y el router los sirve; la consola no abre la base de datos.
- **`Flow` y `PlainFlow` no cambian** (`flows/base.py`, `plain.py`): el estado sigue siendo un `dict`
  validado en cada paso con `EstadoCandidatura`, el mismo modelo que usará `LangGraphFlow`.

## Qué cambia respecto a la versión construida
| Se quita | Motivo |
|---|---|
| Agentes `selector_cv_base/`, `juez_cv/`, `juez_carta/` | P14 (elección por código) y P12 (juez único) |
| Ruta `POST /api/candidaturas/{id}/guardar-cv-base` y el origen «candidatura» del historial | P9b sustituida |
| `documento`, `cv_estetico_id` y `avisos_revisados` al aprobar; redirección al CV estético | CV estético y casilla quitados (P10) |
| Rutas `/respuesta`, `/respuesta/confirmar`, `/respuesta/descartar`; manejador `clasificar_respuesta` del worker; `tope_coste_respuesta` | P15, P17 (el agente y su flujo se quedan para la consola) |
| `PREFIJO_DESFASADO` y prefijos «CV:», «Carta:» en los avisos | Avisos estructurados (RF-3.6c) |

| Se añade | Requisito |
|---|---|
| `tools/elegir_cv_base.py` | RF-3.1b |
| `agents/juez_candidatura/` | RF-3.4 |
| Esquema `Aviso` | RF-3.6c, RF-3.8 |
| Ruta `POST /api/candidaturas/{id}/reintentar` | RF-3.8e |
| `metricas.capturar(tope=…)` + `TopeSuperado` en la puerta única | RF-3.11 |
| Migración 0007 | P16 |

## Flujos
| Flujo | Pasos |
|---|---|
| `candidatura` | `elegir_cv_base` (código: `tools/elegir_cv_base`) → `redactar_cv` (redactor-cv) → `redactar_carta` (redactor-carta) → `comprobar` (código: `verificar_trazabilidad` del CV con fuentes = maestro + CV base y de la carta con fuentes = maestro + CV base + oferta; `rasgos_personales` de los dos; `medir_ats` del CV) → `juzgar` (juez-candidatura) → arista `tras_juzgar`: si `vuelta_hecha` es falso y el CV tiene errores, problemas, errores de formato o palabras con origen → `redactar_cv`; si solo la carta tiene errores o problemas → `redactar_carta`; si no → `componer`. Tras `redactar_cv` en la vuelta se pasa siempre por `redactar_carta`. Tras `comprobar` en la vuelta → `componer` (arista `tras_comprobar`, que mira `vuelta_hecha`) |
| `clasificar_respuesta` | Sin cambios: `clasificar` → `proponer` → `componer`. Solo consola |

Estado: `vuelta_hecha` (booleano) sustituye a `vueltas_cv` y `vueltas_carta`; se guardan
`redacciones_cv` y `redacciones_carta` (1 o 2) para el tablero de métricas. `problemas_juez` guarda
la lista del único juicio; `componer` y el servicio de edición filtran los que siguen vigentes con
la misma función pura `avisos_vigentes(contenido, problemas)` (frase literal en el texto).

## Contratos
**Agentes**
| Agente | Modelo | Entrada → salida |
|---|---|---|
| `redactor-cv` | mayor | Sin cambios: `{cv_base, cv_maestro, oferta, errores_previos[], problemas_previos[], palabras_sugeridas[]}` → `{contenido, traza, huecos, instrucciones_embebidas[]}` |
| `redactor-carta` | mayor | Sin cambios: `{cv_maestro, cv_adaptado, oferta, sector, problemas_previos[]}` → `{contenido, traza, instrucciones_embebidas[]}`. En la vuelta recibe también los errores de `comprobar` como problemas `sin_origen` |
| `juez-candidatura` | mayor | `{cv, cv_traza, carta, carta_traza, cv_maestro, cv_base, oferta}` → `{veredicto_cv, veredicto_carta: aprobado·corregir, problemas: [{documento: cv·carta, tipo: sin_origen·inflado·promesa·rasgo_personal·repite_cv, frase, motivo}]}`. Un `repite_cv` con `documento = cv` no valida |
| `clasificador-respuesta` | pequeño | Sin cambios |

El prompt de `juez-candidatura` une los de `juez-cv` y `juez-carta` (prohíbe reescribir, pide la
lista tipada, es menos estricto con `repite_cv` como se ajustó en el bloque C). Se registra en
`agents/registry.py` y en el contrato «independence» de `pyproject.toml`; salen los tres agentes
quitados.

**Herramientas (código puro con tests)**
- `elegir_cv_base(oferta, cvs_base) -> (cv_base, motivo)`: filtra los de la usuaria con `estado =
  hecho`; ordena por (familia y sector coinciden, familia coincide, sector coincide, `creado_en`,
  `id`) y devuelve el primero con un motivo fijo en llano («Coincide en puesto y sector con la
  oferta», «Coincide en el puesto», «Coincide en el sector», «Ninguno coincide; es el más
  reciente»). Lista vacía → `ValueError`.
- `avisos_vigentes(documento, contenido, problemas) -> list[Aviso]`: devuelve los problemas de ese
  documento cuya `frase` sigue literalmente en `contenido`.
- Las demás (`verificar_trazabilidad`, `medir_ats`, `rasgos_personales`, `generar_pdf`,
  `comparar_versiones`) no cambian.

**`Aviso`**: `{documento: cv·carta, frase: str | None, mensaje: str}`. `mensaje` en lenguaje llano y
sin prefijos; lo escribe el código a partir del tipo de problema o del error (una tabla de textos en
`schemas/candidatura.py`). La pantalla pinta cada aviso junto a su frase.

**Puerta única (arreglo del tope, RF-3.11)**: `metricas.capturar(tope: float | None = None)`. Antes
de cada llamada, `completar` suma el coste de las llamadas ya capturadas en ese bloque y, si supera
el tope, lanza `TopeSuperado` sin llamar al modelo. El worker abre `capturar(tope=tope_coste -
coste_acumulado)`; `TopeSuperado` no se reintenta y deja la tarea en `error` con el motivo «tope de
coste superado». Vale para todas las tareas, no solo la candidatura.

**API** (sesión; escritura con CSRF; RLS «propia»)
| Ruta | Qué hace |
|---|---|
| `POST /api/candidaturas` | Sin cambios (RF-3.7b, `repetir`) |
| `GET /api/candidaturas` · `GET /api/candidaturas/{id}` | Tablero y detalle; el detalle trae `avisos` estructurados, `huecos` y un bloque `detalles` (CV base, motivo, cobertura ATS) |
| `PATCH /api/candidaturas/{id}` | Solo en `borrador`: edita CV o carta; vuelve a pasar `comprobar` por código y recalcula los avisos con `avisos_vigentes` para los dos documentos (arregla que se borraran los del juez) |
| `POST /api/candidaturas/{id}/aprobar` | `{}`. Sin casilla ni elección de documento |
| `POST /api/candidaturas/{id}/reintentar` | Solo con `preparacion = error` y en `borrador`: vuelve a `en_curso` y encola `candidatura`. 409 si no está en error |
| `POST /api/candidaturas/{id}/enviada` | `{canal?, canal_otro?}`; la fecha la pone el servidor (hoy) |
| `POST /api/candidaturas/{id}/entrevista` · `/cerrar` | Sin cambios; «Me han llamado» usa `/entrevista` y «Me han rechazado», `/cerrar` con `motivo = rechazo` |
| `GET /api/candidaturas/{id}/cv.pdf` · `/carta.pdf` | Solo desde `aprobada`; siempre el CV adaptado |
| `GET /api/cv-base/{id}/versiones` · `POST …/restaurar` | Sin cambios |

**Pantallas** (marco Passe-Partout, `nodo()` y `textContent`)
- **Candidatura** (`static/candidatura.js`): CV y carta como documento legible con «Editar»; lista
  «Revisa esto» (huecos con su propuesta y avisos junto a su frase, en llano); «Detalles» plegado
  (CV base, motivo, % ATS); «Aprobar y descargar» (aprueba y descarga los dos PDF); «Marcar como
  enviada» (canal opcional); «Me han llamado» y «Me han rechazado» según el estado; «Reintentar»
  con el motivo si la preparación falló; cerrar con motivo; historial. Se quitan «Guardar como mi CV
  base», la casilla, la elección de CV y «pegar la respuesta».
- **Tablero**, **Recomendadas** y **CV base**: sin cambios de comportamiento; solo se revisan los
  textos que nombren el selector, el CV estético o «guardar encima».

**Consola**
- `horma agente correr redactor-cv|redactor-carta|juez-candidatura|clasificador-respuesta --entrada f [--simulado]`
- `horma flujo correr candidatura --usuaria ana --oferta 123 [--paso-a-paso --traza dir]` (sin cambios)
- `horma flujo correr clasificar_respuesta --entrada correo.json` (sin cambios)
- `horma eval correr cv|respuestas [--tope-coste 1.0]`

## Requisito → componente
| Requisito | Componente | Notas |
|---|---|---|
| RF-3.1 | `flows/candidatura.py`, `schemas/candidatura.py` | 3-5 llamadas; vuelta única |
| RF-3.1b | `tools/elegir_cv_base.py`, paso `elegir_cv_base` | Sin modelo (P14) |
| RF-3.2 | `agents/redactor_cv/` | Sin cambios |
| RF-3.3 | paso `comprobar` | Reúne verificar, rasgos y ATS |
| RF-3.4 | `agents/juez_candidatura/` | Nunca reescribe |
| RF-3.5 | `tools/medir_ats.py`, arista `tras_juzgar` | Palabras dentro de la vuelta (P13) |
| RF-3.6, RF-3.6b | `agents/redactor_carta/`, prompts | Sin cambios |
| RF-3.6c | `componer`, `avisos_vigentes`, `Aviso` | Lenguaje llano |
| RF-3.7, RF-3.7b | `transicion()`, `POST /api/candidaturas` | Sin cambios |
| RF-3.8 | `PATCH`, `static/candidatura.*` | Avisos del juez conservados |
| RF-3.8a | `/aprobar` | Sin casilla (P10) |
| RF-3.8b, RF-3.8c | `/enviada`, rutas `.pdf` | Fecha de hoy, canal opcional |
| RF-3.8d | `cv_base_versiones`, repositorio de `cv_base`, `static/cv-base.js` | Orígenes `edicion`·`restauracion` |
| RF-3.8e | `/reintentar` | Mismo tope |
| RF-3.9 | `/entrevista`, `/cerrar`, `static/candidatura.js` | Dos botones (P15) |
| RF-3.9b | `agents/clasificador_respuesta/`, `flows/clasificar_respuesta.py`, `evals/respuestas/` | Solo consola y CI (P17) |
| RF-3.10 | `static/candidaturas.*` | Sin cambios |
| RF-3.11 | worker, `llm/metricas.py`, `llm/gateway.py`, `cli.py` | Corte antes de cada llamada |
| RF-3.12 | `horma/evals.py` | Sin cambios |

## Modelo de datos (migración 0007, reversible)
| Tabla | Cambio |
|---|---|
| `candidaturas` | Quita `documento`, `cv_estetico_id`, `respuesta_pendiente`, `respuesta_propuesta`, `vueltas_cv`, `vueltas_carta`. Añade `redacciones_cv`, `redacciones_carta` (smallint) y `problemas_juez` (jsonb, `[]`). `avisos` pasa a guardar objetos `Aviso` (los antiguos, texto, se convierten a `{documento: cv, frase: null, mensaje: texto}`) |
| `candidatura_eventos` | Quita `etiqueta_respuesta`; `origen` solo `usuaria` (las filas `respuesta` pasan a `usuaria`); `tipo` sin `cv_base_guardado` (esas filas se borran: son de prueba) |
| `cv_base_versiones` | `origen` solo `edicion`·`restauracion` (las `candidatura` pasan a `edicion`); quita `candidatura_id` |

`downgrade` vuelve a crear las columnas y los `CHECK` antiguos (vacías o con su valor por defecto).
Las tablas siguen en el `TRUNCATE` de `tests/conftest.py`.

## Worker
- `candidatura`: igual que ahora; `cargar` añade `creado_en` a cada CV base (para desempatar).
- Sale el manejador `clasificar_respuesta` de `MANEJADORES`.
- `procesar_una` abre `metricas.capturar(tope=…)`; `TopeSuperado` va directo a `error` sin reintento.
- `config.py` y `.env.example`: sale `tope_coste_respuesta`; `tope_coste_candidatura` sigue en 1 USD
  (construcción).

## Evals
| Set | Casos | Cambio |
|---|---|---|
| `cv` | 14: 9 sembrados, 3 de flujo completo (uno adversario), 2 de selección | Los sembrados pasan por `comprobar` + `juez-candidatura`; los de selección comprueban `elegir_cv_base` (código, coste 0); el harness cuenta las llamadas de los casos de flujo (≤ 5). Umbrales sin cambios: 100 % |
| `respuestas` | 15 correos (3 adversarios) | Sin cambios; sigue en CI |

## Decisiones del plan (revisables)
- «Más reciente» = `creado_en` más nuevo (a igualdad, `id` mayor). Editar un CV base no lo hace más
  reciente; si molesta, se cambia por la fecha de su última versión.
- Tras la vuelta no se vuelve a juzgar: los problemas que siguen vigentes se detectan con código
  (frase literal). Un problema reformulado a medias puede quedar sin aviso; los errores duros (fecha,
  cargo, empresa, titulación, rasgo) los sigue cazando `comprobar`.
- El arreglo del tope vive en la puerta única y vale para todas las tareas del worker.
- Los textos de los avisos los escribe el código, no el modelo: son estables y se pueden traducir.
- «Aprobar y descargar» descarga los dos PDF desde el navegador tras aprobar (dos peticiones).

## Riesgos
- **Más avisos:** con un solo juicio y una vuelta, más candidaturas quedarán en `pendiente_de_ti`.
  Se vigila con los 3 casos de flujo y la prueba manual.
- **Juez único con dos documentos:** la entrada es más larga y puede confundir de qué documento es
  cada problema; el esquema lo obliga y un `repite_cv` en el CV no valida.
- **Migración:** borra datos de prueba (eventos `cv_base_guardado`, respuestas pendientes). Antes de
  aplicarla, `docker compose` con la base de datos de desarrollo; nunca hay datos reales.
- **Tope en la puerta única:** toca `horma/llm`, que usan todos los flujos; la suite completa lo cubre.
- **Coste de medir:** eval `cv` real ≈ 0,5 USD y una candidatura real < 1 USD; se pide OK a Mar antes.
- **Instalación:** `uv` puede fallar con certificados; usar `--system-certs` y `UV_NO_SYNC=1`.
