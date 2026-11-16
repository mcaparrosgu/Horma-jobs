---
type: plan
title: candidatura — Plan técnico
description: Arquitectura, contratos y modelo de datos que cubren cada requisito de la fase 3.
tags: [plan, candidatura, seguimiento]
status: active
sources: [./spec.md, ./clarifications.md, ../system.md, ../002-perfil-recomendacion/plan.md]
generated: { by: claude-code, at: 2026-11-15 }
verified: { by: human, at: 2026-11-15 }
stale_after: null
---

# candidatura — Plan

## Arquitectura
Se añade a lo de las fases 0 a 2:

```
horma/
  schemas/   candidatura.py (Candidatura, EstadoCandidatura, EventoCandidatura, Hueco, Problema,
             enumerados Estado, Preparacion, Canal, MotivoCierre, EtiquetaRespuesta;
             transicion() y transicion_por_respuesta(): máquina de estados como funciones puras)
  agents/    selector_cv_base/ (pequeño), redactor_cv/ (mayor), juez_cv/ (mayor),
             redactor_carta/ (mayor), juez_carta/ (mayor), clasificador_respuesta/ (pequeño)
  tools/     medir_ats.py (nuevo), generar_pdf.py (nuevo), comparar_versiones.py (nuevo),
             verificar_trazabilidad.py (varias fuentes)
  flows/     candidatura.py, clasificar_respuesta.py
  cli.py     + flujo correr candidatura --oferta, eval correr cv|respuestas
  web/       migración 0006, routers/candidaturas.py, services/candidaturas.py,
             repositories/candidaturas.py, static/{candidaturas,candidatura}.{html,js},
             recomendadas.js (+ botón), comun.js (+ pestaña)
evals/cv/ (12 casos + fixtures de ana) · evals/respuestas/ (15 correos)
```

- **Camino de una candidatura:** la usuaria pulsa «Preparar candidatura» en Recomendadas →
  `POST /api/candidaturas` crea la fila en `borrador` con `preparacion = en_curso` y encola
  `candidatura` (solo el id) → el worker carga oferta, perfil, CV maestro y sus CV base válidos,
  ejecuta el flujo (que empieza eligiendo el CV base) y guarda el CV base elegido con su motivo, CV,
  carta, trazas, huecos y avisos con `preparacion = lista` o `pendiente_de_ti`.
- **Guardar encima del CV base:** desde la candidatura en `borrador`, la usuaria guarda su CV
  editado sobre el CV base del que partió (`cv_base.contenido` y `nombre`). Usa la misma regla que
  la edición de RF-2.9e: texto suyo, no se vuelve a comprobar contra el CV, nombre único.
- **Historial del CV base (RF-3.8d):** la función de editar del repositorio de `cv_base` copia
  primero la versión actual a `cv_base_versiones`, en la misma transacción. Así lo cubren a la vez
  guardar encima, la edición manual de la fase 2 y volver a una versión. Lo añadido y lo quitado se
  calcula al leer, línea a línea, con `difflib` (biblioteca estándar): herramienta pura
  `tools/comparar_versiones.py`.
- **Dos campos, dos máquinas:** `estado` es la de la candidatura (`borrador → aprobada → enviada →
  entrevista`, y `cerrada` desde cualquiera, P8); `preparacion` es el resultado del flujo (`en_curso`,
  `lista`, `pendiente_de_ti`, `error`). El flujo nunca cambia `estado`.
- **Fronteras (sin cambios):** agentes y herramientas sin base de datos ni disco; `generar_pdf`
  devuelve bytes y el router los sirve; la consola no abre la base de datos.
- **`Flow` y `PlainFlow` no cambian** (`horma/flows/base.py`, `plain.py`): el estado sigue siendo un
  `dict` y cada paso de `candidatura` lo valida con `EstadoCandidatura`, el mismo modelo que usará
  `LangGraphFlow` en la fase 4. No se toca ningún flujo de la fase 2.

## Flujos
| Flujo | Pasos |
|---|---|
| `candidatura` | `elegir_cv_base` (selector-cv-base si hay más de un CV base válido; el código comprueba que el elegido es de la usuaria, no está rechazado y estaba en la lista, y anota el aviso si está desfasado) → `redactar_cv` (redactor-cv) → `verificar` (verificar_trazabilidad con fuentes = maestro + CV base) → `juzgar_cv` (juez-cv) → arista: vuelve a `redactar_cv` con errores y problemas si hay alguno y quedan vueltas → `medir_ats` → arista: vuelve a `redactar_cv` con las palabras que faltan con origen si quedan vueltas; las que no tienen origen van a `huecos` → `redactar_carta` (redactor-carta) → `verificar_carta` (verificar_trazabilidad con fuentes = maestro + CV base + oferta) → `juzgar_carta` (juez-carta) → arista: una vuelta a `redactar_carta` → `componer` (`lista` o `pendiente_de_ti`) |
| `clasificar_respuesta` | `clasificar` (clasificador-respuesta) → `proponer` (código: `transicion_por_respuesta(estado_actual, etiqueta)`; si la transición no es legal o hay instrucciones embebidas, la propuesta es «ninguna») → `componer` |

Contadores en el estado: `vueltas_cv` (máx. 3 redacciones: la primera y 2 vueltas, incluida la del
ATS) y `vueltas_carta` (máx. 2). El bucle copia el patrón de `flows/generar_cv_base.py:20-83`
(`MAX_INTENTOS`, `errores_previos`, decisión `tras_verificar`). Los dos flujos se añaden a `FLUJOS` y
`RESULTADO` de `flows/registry.py:11-17`.

## Contratos
**Agentes**
| Agente | Modelo | Entrada → salida |
|---|---|---|
| `selector-cv-base` | pequeño | `{oferta, cvs_base: [{id, nombre, sector, familia, contenido}]}` → `{cv_base_id, motivo (una frase), instrucciones_embebidas[]}` |
| `redactor-cv` | mayor | `{cv_base, cv_maestro, oferta, errores_previos[], problemas_previos[], palabras_sugeridas[]}` → `{contenido (Markdown ATS), traza: [{frase, fragmento}], huecos: [{requisito, propuesta}], instrucciones_embebidas[]}` |
| `juez-cv` | mayor | `{contenido, traza, cv_maestro, cv_base, oferta}` → `{veredicto: aprobado·corregir, problemas: [{tipo: sin_origen·inflado·promesa·rasgo_personal, frase, motivo}]}` |
| `redactor-carta` | mayor | `{cv_maestro, cv_adaptado, oferta, sector, problemas_previos[]}` → `{contenido, traza, instrucciones_embebidas[]}` |
| `juez-carta` | mayor | `{contenido, traza, cv_maestro, cv_adaptado, oferta}` → `{veredicto, problemas: [{tipo: …·repite_cv, frase, motivo}]}` |
| `clasificador-respuesta` | pequeño | `{texto}` → `{etiqueta: entrevista·rechazo·piden_informacion·otro, instrucciones_embebidas[]}` |

Los jueces nunca reescriben. `TrazaFrase` sale de `agents/generador_cv_base/schemas.py:12` a
`horma/schemas/candidatura.py` para compartirla sin que un agente importe a otro (RT-13). Cada agente
nuevo se añade a `agents/registry.py:11-14` y al contrato «independence» de `pyproject.toml:67-79`.

**Herramientas (código puro con tests)**
- `verificar_trazabilidad(contenido, traza, fuentes)`: `fuentes` pasa a aceptar un texto o una lista
  de textos (compatibilidad con la llamada de la fase 2). Para la carta, `formulas_cortesia` (lista
  cerrada de saludos y despedidas) queda exenta de traza.
- `medir_ats(contenido, oferta, fuentes)`: devuelve `{errores_formato[], cobertura (0-1),
  presentes[], ausentes_con_origen[], ausentes_sin_origen[]}`. Las palabras clave salen de
  `oferta.requisitos` y `taxonomia.stack`. `errores_formato` es el actual `errores_ats`
  (`horma/evals.py:141-156`), que se mueve aquí y `evals.py` lo importa.
- `comparar_versiones(anterior, siguiente)`: devuelve las líneas con su marca (`igual`, `añadida`,
  `quitada`), con `difflib`.
- `generar_pdf(markdown, titulo) -> bytes`: Markdown sencillo (encabezados, listas, párrafos) a PDF
  con `fpdf2` y una fuente con acentos. Sin imágenes ni tablas.
- `transicion(estado, destino, motivo?)` y `transicion_por_respuesta(estado, etiqueta)` en
  `schemas/candidatura.py`: lanzan `TransicionInvalida` o devuelven la propuesta.

**API** (sesión; escritura con CSRF; RLS «propia»)
| Ruta | Qué hace |
|---|---|
| `POST /api/candidaturas` | `{oferta_id}`. Comprueba que tenga al menos un CV base válido (si no, 409 con «genera un CV base primero»), que no haya otra candidatura no cerrada para esa oferta (409), que no haya una cerrada sin confirmar (409 «Ya preparaste…»; con `repetir: true` se crea otra) y encola `candidatura` |
| `GET /api/candidaturas` · `GET /api/candidaturas/{id}` | Tablero (agrupado por estado) y detalle con CV, carta, huecos, avisos e historial |
| `PATCH /api/candidaturas/{id}` | Solo en `borrador`: edita CV o carta; vuelve a pasar `verificar_trazabilidad` (sin modelo) y actualiza los avisos |
| `POST /api/candidaturas/{id}/guardar-cv-base` | Solo en `borrador`: `{nombre}`. Sobrescribe el `cv_base` de la candidatura con su CV adaptado actual y el nombre (409 si el nombre ya existe en su cuenta). Guarda antes la versión anterior y lo registra en el historial de la candidatura |
| `GET /api/cv-base/{id}/versiones` | Historial del CV base: cada versión con fecha, origen, nombre y sus líneas marcadas (añadida·quitada·igual) respecto a la siguiente |
| `POST /api/cv-base/{id}/versiones/{version_id}/restaurar` | Vuelve a esa versión; guarda antes la actual en el historial |
| `POST /api/candidaturas/{id}/aprobar` | `{documento: adaptado·estetico, cv_estetico_id?, avisos_revisados}`. 400 si hay avisos y no están revisados |
| `POST /api/candidaturas/{id}/enviada` · `/entrevista` · `/cerrar` | Transiciones con `transicion()`: `{fecha, canal, canal_otro?}` · `{}` · `{motivo}` |
| `GET /api/candidaturas/{id}/cv.pdf` · `/carta.pdf` | Solo desde `aprobada`; si eligió el estético, redirige a `GET /api/cv/{id}/archivo` |
| `POST /api/candidaturas/{id}/respuesta` · `/respuesta/confirmar` · `/respuesta/descartar` | Guarda el texto en `respuesta_pendiente` y encola `clasificar_respuesta`; confirmar aplica la propuesta; descartar la borra |
| `GET /candidaturas`, `/candidaturas/{id}` | Páginas con pestañas comunes |

Los cuerpos caben en `MAX_CUERPO` (64 KB). La CSP no cambia: los PDF se descargan, no se enmarcan.

**Pantallas** (marco Passe-Partout, `nodo()` y `textContent`; diseño con la skill `frontend`)
- **Tablero** (`/candidaturas`, pestaña nueva en `PESTANAS`, `static/comun.js:6-11`): columnas
  borrador, aprobada, enviada, entrevista y «Cerradas» (plegada); tarjeta con puesto, empresa, fecha
  del último cambio y marca «Te toca revisar». En móvil, columnas apiladas.
- **Candidatura** (`/candidaturas/{id}`): qué CV base eligió Horma y por qué; CV y carta como
  documento legible (como RF-2.9d), con «Editar»; tras editar el CV, «Guardar como mi CV base» con
  el nombre propuesto (editable) y el aviso «La versión anterior queda en el historial»; huecos con
  su propuesta; avisos; botones según el estado (aprobar con la casilla «He
  revisado los avisos» y la elección de CV; descargar; marcar enviada con canal y fecha; pegar
  respuesta y confirmar la propuesta; cerrar con motivo); historial.
- **Recomendadas**: botón «Preparar candidatura» en cada fila (`filaOferta`,
  `static/recomendadas.js:122-157`) que crea la candidatura y lleva a ella; sin CV base, enlaza a
  generarlo.
- **CV base** (`static/cv-base.js`): «Historial» en cada CV base, plegado. Lista de versiones (fecha,
  origen, nombre); al abrir una, sus líneas añadidas en verde y quitadas en rojo y tachadas (con
  texto «añadido»/«quitado» para lectores de pantalla), y «Volver a esta versión».
  Recomendadas y CV base son las dos únicas pantallas de la fase 2 que cambian.

**Consola**
- `horma agente correr selector-cv-base|redactor-cv|juez-cv|redactor-carta|juez-carta|clasificador-respuesta --entrada f [--simulado]`
- `horma flujo correr candidatura --usuaria ana --oferta 123 [--paso-a-paso --traza dir]`: con
  `--usuaria` carga los fixtures `evals/cv/usuarias/ana/` (perfil, CV maestro y sus CV base); la oferta
  sale de `GET /api/catalogo` o de `--ofertas f.json`. `--entrada caso.json` sigue valiendo. En
  local; no guarda nada.
- `horma flujo correr clasificar_respuesta --entrada correo.json`
- `horma eval correr cv|respuestas [--tope-coste 1.0]`

## Requisito → componente
| Requisito | Componente | Notas |
|---|---|---|
| RF-3.1 | `flows/candidatura.py`, `schemas/candidatura.py` (`EstadoCandidatura`) | Máx. 3 redacciones de CV y 2 de carta |
| RF-3.1b | `agents/selector_cv_base/`, paso `elegir_cv_base` | La elige el agente; el código valida (P9) |
| RF-3.2 | `agents/redactor_cv/` | Regla de los huecos en el prompt |
| RF-3.3 | `tools/verificar_trazabilidad.py` (varias fuentes) | Reutiliza `linea_con` y `literales` |
| RF-3.4 | `agents/juez_cv/` | Nunca reescribe |
| RF-3.5 | `tools/medir_ats.py` | Sin umbral (RF-4.4) |
| RF-3.6 | `agents/redactor_carta/`, `agents/juez_carta/`, paso `verificar_carta` | Sin carta base (P1) |
| RF-3.6b | prompts, `instrucciones_embebidas`, `tools/rasgos_personales.py` | Casos adversarios en `evals/cv/` |
| RF-3.7 | `transicion()`, tabla `candidatura_eventos` | `cerrada` con motivo (P8) |
| RF-3.7b | `POST /api/candidaturas`, `static/recomendadas.js` | Índice único parcial |
| RF-3.8 | `PATCH`, `/guardar-cv-base` y `/aprobar`, `static/candidatura.*` | Avisos revisados (P10); sobrescribir pide confirmación (P9b) |
| RF-3.8d | tabla `cv_base_versiones`, repositorio de `cv_base`, `tools/comparar_versiones.py`, rutas `/versiones`, `static/cv-base.js` | Ningún texto se pierde |
| RF-3.8b | `tools/generar_pdf.py`, rutas `.pdf`, `/enviada` | Canal ampliable (P3) |
| RF-3.8c | rutas `.pdf` y `/enviada` comprueban el estado | RT-10 |
| RF-3.9 | `agents/clasificador_respuesta/`, `flows/clasificar_respuesta.py`, rutas `/respuesta` | El texto se borra (P11) |
| RF-3.10 | `static/candidaturas.*`, `GET /api/candidaturas` | Por descripción (P5) |
| RF-3.11 | worker (`candidatura`), `cli.py` | Traza `NN-paso.json` |
| RF-3.12 | `horma/evals.py` | Tope 1 USD, solo en construcción |

## Modelo de datos (migración 0006)
| Tabla | Campos | RLS |
|---|---|---|
| `candidaturas` | `id`, `usuaria_id`, `oferta_id`, `cv_base_id` (nulo hasta que lo elige el flujo), `cv_base_motivo`, `perfil_version`, `estado` (borrador·aprobada·enviada·entrevista·cerrada), `motivo_cierre`, `preparacion` (en_curso·lista·pendiente_de_ti·error), `motivo_error`, `cv_contenido`, `cv_traza` jsonb, `carta_contenido`, `carta_traza` jsonb, `huecos` jsonb, `avisos` jsonb, `cobertura_ats`, `vueltas_cv`, `vueltas_carta`, `instrucciones_embebidas` jsonb, `documento` (adaptado·estetico), `cv_estetico_id`, `canal`, `canal_otro`, `enviada_en`, `respuesta_pendiente` (texto temporal), `respuesta_propuesta` jsonb, `creado_en`, `actualizado_en` | propia |
| `candidatura_eventos` | `id`, `usuaria_id`, `candidatura_id`, `de`, `a`, `motivo`, `canal`, `origen` (usuaria·respuesta), `tipo` (transicion·nota·cv_base_guardado), `etiqueta_respuesta`, `creado_en` | propia |
| `cv_base_versiones` | `id`, `usuaria_id`, `cv_base_id` (borrado en cascada), `nombre`, `contenido`, `origen` (candidatura·edicion·restauracion), `candidatura_id` (nulo si no viene de una), `creado_en` | propia |

Índice único parcial `(usuaria_id, oferta_id) WHERE estado <> 'cerrada'` (RF-3.7b). Las tres tablas se
añaden al `TRUNCATE` de `tests/conftest.py:83-85`. Ningún archivo de las fases anteriores cambia salvo
los registros, `recomendadas.js`, `cv-base.js` (historial), el router de `cv-base` (rutas de versiones), `comun.js`, `paginas.py`, `config.py`, `evals.py` (importa
`errores_ats`), la firma compatible de `verificar_trazabilidad` y el repositorio de `cv_base`, que
reutiliza su función de editar (RF-2.9e) para guardar encima y le añade la copia al historial.

## Worker
Dos manejadores nuevos en `MANEJADORES` (`horma/web/queue/worker.py:178-181`):
- `candidatura`: `cargar` (oferta, perfil vigente, maestro, CV base válidos de la usuaria) → flujo →
  `guardar` (CV base elegido y motivo, todo lo del flujo y `preparacion`); `marcar_error` deja `preparacion = error` con el motivo.
- `clasificar_respuesta`: lee `respuesta_pendiente`, guarda `respuesta_propuesta` y **borra
  `respuesta_pendiente` en `guardar` y en `marcar_error`**.

Topes nuevos en `horma/config.py`: `tope_coste_candidatura = 1.00` y `tope_coste_respuesta = 0.05` (USD).
Son valores de construcción: el tope de uso real se fija al medir el coste, antes de usuarias reales.

## Evals
| Set | Casos | Mide | Umbral |
|---|---|---|---|
| `cv` | 12: 9 con un error sembrado (cifra inventada, cargo subido, fecha cambiada, empresa cambiada, titulación inventada, rasgo personal, promesa, inflado, carta que repite el CV) que pasan por el verificador y el juez; 3 de flujo completo (uno adversario: oferta con instrucciones) | Sembrados rechazados; fechas, cargos, empresas y titulaciones idénticos; lo que falta va a huecos; adversaria sin efecto; cobertura ATS registrada | 100 % en todo; ATS sin umbral |
| `respuestas` | 15 correos inventados (3 con instrucciones escondidas) | Etiqueta; ningún efecto en los adversarios | ≥ 0,9 etiqueta; adversarios 100 % |

Se registran como `SetEval` en `NUEVOS` (`horma/evals.py:41-50`, `:223-243`); el tope de 1 USD de
construcción ya se aplica en `:326`. El set `cv` añade 2 casos de selección (`selector-cv-base`
elige el CV base del sector de la oferta entre 2 o 3), sin contar en los 12 de errores sembrados. CI añade los dos sets a `.github/workflows/ci.yml`.

## Decisiones del plan (revisables)
- PDF con `fpdf2` (Python puro, sin GTK); corrige la redacción de P2.
- La vuelta que pide `medir_ats` cuenta dentro de las 2 del CV.
- Solo se edita en `borrador`; no hay «reabrir».
- Tope de 1 USD por candidatura durante la construcción: como mucho 6 llamadas al modelo mayor para
  el CV (3 redacciones y 3 juicios), 4 para la carta (2 y 2) y 1 al pequeño para elegir el CV base.
- El selector usa el modelo pequeño: elegir entre pocos CV es una tarea corta.
- Historial con copia completa de cada versión, sin límite de versiones: un CV base son unos pocos KB.
  Lo añadido y lo quitado no se guarda; se calcula al mostrarlo.
- La edición manual de la fase 2 también deja versión, porque comparte la función del repositorio.
- Dependencia nueva: `fpdf2`.

## Riesgos
- **Instalación:** `uv` falla con certificados en esta red; puede hacer falta `--system-certs` o
  instalar `fpdf2` a mano y usar `UV_NO_SYNC=1`.
- **Coste:** una candidatura que agota las vueltas hace 10 llamadas al modelo mayor (estimado, sin
  medir: 0,30-0,60 USD); el tope la corta en 1 USD.
- **Selector equivocado:** si elige un CV base de otro sector, el CV adaptado sale peor. La
  candidatura muestra cuál eligió y por qué, y los 2 casos de selección del eval lo vigilan.
- **Juez demasiado estricto:** si `juez-cv` marca casi todo, la mayoría de candidaturas acabarán en
  `pendiente_de_ti`. Se vigila con los 3 casos de flujo completo y la prueba manual.
- **Acentos en el PDF:** las fuentes básicas de `fpdf2` no cubren todo Unicode; se incluye una fuente
  TTF libre en el paquete.
