---
type: tasks
title: candidatura — Desglose de tareas
description: Tareas pequeñas y comprobables derivadas del plan de la fase 3. Cada una empieza con un test que falla. Bloques A-G construidos; bloque H (simplificar la candidatura, 16-nov-2026) pendiente.
tags: [tareas, candidatura, seguimiento]
status: active
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-16 }
verified: { by: human, at: 2026-11-16 }
stale_after: null
---

# candidatura — Tareas

Orden de construcción, por bloques, parando entre bloques: contrato y código puro (A, T01-T04) →
agentes (B, T05-T07) → flujos y evals (C, T08-T11) → base de datos y worker (D, T12-T13) → API (E,
T14-T17) → pantallas (F, T18-T20) → consola y cierre (G, T21-T22) → simplificar (H, T23-T32, 16-nov-2026). Cada tarea empieza con un test que
falla. Todo se prueba sin llamar al modelo (puerta simulada) salvo la medición real de T10, T11, T27 y T32.
Los bloques A-G describen lo construido el 15-nov; lo que el bloque H quita o cambia se indica en
cada tarea H (los tests antiguos que dejen de aplicar se borran o se adaptan en la tarea H que toca
su código).

### Bloque A · Contrato y código puro
- [x] T01 — Esquemas de `horma/schemas/candidatura.py` (`Candidatura`, `EstadoCandidatura`, `EventoCandidatura`, `Hueco`, `Problema`, `TrazaFrase` movida aquí; enumerados de estado, preparación, canal, motivo de cierre y etiqueta) y funciones `transicion()` y `transicion_por_respuesta()` · test: transiciones permitidas y prohibidas (p. ej. `borrador → enviada` falla; `cerrada` desde cualquier estado con motivo; nada sale de `cerrada`); `enviada` exige fecha y canal; «otro» admite texto corto; cada etiqueta da su propuesta y una ilegal da «ninguna» · cubre: RF-3.1, RF-3.7, RF-3.8b, RF-3.9
- [x] T02 — Herramienta `medir_ats` (se mueve `errores_ats` desde `evals.py`) · test: detecta tablas, imágenes y HTML como antes; cobertura correcta con requisitos y stack de una oferta inventada; separa las ausentes con origen de las que no lo tienen; el eval `cv-base` sigue en verde · cubre: RF-3.5
- [x] T03 — `verificar_trazabilidad` con varias fuentes y fórmulas de cortesía · test: las llamadas de la fase 2 (un solo texto) dan el mismo resultado; un fragmento del CV base editado es válido; un fragmento de la oferta vale solo para la carta; el saludo y la despedida de la lista no piden traza; una fecha, cargo, empresa o titulación cambiados se rechazan al 100 % · cubre: RF-3.3, RF-3.6, RT-08
- [x] T04 — Herramientas `generar_pdf` (dependencia `fpdf2`, con fuente TTF libre) y `comparar_versiones` · test: un Markdown con encabezados, listas y acentos («Señora», «Educación») da un PDF válido que `pypdf` vuelve a leer con el mismo texto; `comparar_versiones` marca bien las líneas añadidas, quitadas e iguales, y dos textos idénticos no dan cambios · cubre: RF-3.8b, RF-3.8d

### Bloque B · Agentes
- [x] T05 — Agentes `redactor-cv` y `juez-cv` · test: con la puerta simulada devuelven su esquema; el prompt del redactor exige la regla de los huecos, traza por frase y registrar instrucciones; el del juez prohíbe reescribir y pide la lista tipada; ambos en el registro y en el contrato «independence» · cubre: RF-3.2, RF-3.4, RF-3.6b, RT-01, RT-13
- [x] T06 — Agentes `redactor-carta` y `juez-carta` · test: devuelven su esquema; el prompt del redactor prohíbe repetir el CV y usa las fórmulas cerradas; el juez tiene el problema `repite_cv`; registro e «independence» · cubre: RF-3.6, RF-3.6b, RT-01
- [x] T07 — Agentes `clasificador-respuesta` y `selector-cv-base` (modelo pequeño los dos) · test: el clasificador devuelve una de las 4 etiquetas; el selector devuelve un `cv_base_id` y un motivo de una frase; los dos prompts piden registrar las instrucciones y no obedecerlas; registro e «independence» · cubre: RF-3.1b, RF-3.9, RT-07

### Bloque C · Flujos y evals
- [x] T08 — Flujo `candidatura` · test: con respuestas simuladas, un CV con error vuelve al redactor con la lista de errores; para en 3 redacciones del CV y 2 de la carta; la vuelta del ATS cuenta dentro de las del CV; las palabras sin origen van a huecos; termina en `lista` o `pendiente_de_ti`; `elegir_cv_base` guarda el elegido y su motivo, no llama al modelo si solo hay un CV base válido, y corta con error si el selector devuelve un CV rechazado, de otra usuaria o que no estaba en la lista; un CV base desfasado deja un aviso; cada paso valida `EstadoCandidatura`; pasa la suite de flujos parametrizada (RT-12) · cubre: RF-3.1, RF-3.1b, RF-3.2, RF-3.3, RF-3.5, RF-3.6
- [x] T09 — Flujo `clasificar_respuesta` · test: «entrevista» propone `entrevista` solo desde `enviada`; «rechazo» propone `cerrada`; un correo con instrucciones no propone nada; el estado nunca cambia dentro del flujo · cubre: RF-3.9, RT-07
- [x] T10 — Fixtures inventadas y eval `cv` (12 casos, 2 casos de selección y fixtures de ana con 2 o 3 CV base de sectores distintos en `evals/cv/usuarias/ana/`) · test: el harness exige el 100 % de sembrados rechazados, datos idénticos al maestro, huecos en vez de inventar, adversaria sin efecto y el CV base del sector de la oferta en los casos de selección; registra la cobertura ATS sin umbral; con un tope bajo simulado se detiene y lo anota · cubre: RF-3.1b, RF-3.2 a RF-3.6b, RF-3.12, RT-11
- [x] T11 — Fixtures y eval `respuestas` (15 correos, 3 adversarios) · test: etiqueta ≥ 0,9 y adversarios al 100 % sin efecto · cubre: RF-3.9, RF-3.12, RT-07, RT-11

### Bloque D · Base de datos y worker
- [x] T12 — Migración 0006 (`candidaturas`, `candidatura_eventos`, `cv_base_versiones`, índice único parcial, RLS «propia») y `TRUNCATE` de los tests · test: tablas y columnas del esquema; una usuaria no lee las candidaturas, el historial ni las versiones de CV base de otra; no se pueden crear dos candidaturas no cerradas para la misma oferta; eliminar un CV base borra sus versiones · cubre: RF-3.7, RF-3.7b, RF-3.8d, RF-3.10
- [x] T13 — Worker con `candidatura` y `clasificar_respuesta` y topes de construcción en `config.py` · test: carga todos los CV base válidos de la usuaria; guarda el CV base elegido con su motivo, CV, carta, trazas, huecos, avisos y `preparacion`; un tope bajo deja `preparacion = error` con motivo; `respuesta_pendiente` queda vacío tras éxito y tras error · cubre: RF-3.9, RF-3.11, RT-14

### Bloque E · API
- [x] T14 — `POST/GET /api/candidaturas` y detalle · test: crear solo con `oferta_id` encola la tarea; sin ningún CV base válido → 409 que pide generarlo; segunda candidatura viva para la misma oferta → 409; si ya hubo una cerrada, 409 de aviso y con `repetir` se crea otra; el detalle muestra el CV base elegido, su motivo (sin aviso de desfasado: el redactor parte también del CV maestro); el tablero sale agrupado por estado · cubre: RF-3.1b, RF-3.7b, RF-3.10
- [x] T15 — Editar, guardar encima del CV base, aprobar, enviada, entrevista, cerrar e historial · test: editar solo en `borrador` y sin llamar al modelo; `guardar-cv-base` sobrescribe el texto y el nombre del CV base de la candidatura, rechaza un nombre repetido (409), solo en `borrador` y solo la dueña, y deja un evento; una candidatura nueva parte ya del CV base guardado; guardar encima y editar desde la pantalla de CV base (RF-2.9e) dejan la versión anterior en el historial; `GET /versiones` devuelve las líneas marcadas; restaurar deja el texto original idéntico y guarda antes la versión actual; otra usuaria no ve ni restaura versiones; aprobar con avisos sin marcarlos → 400; otra usuaria no aprueba (RLS); `enviada` sin aprobar → rechazada; cada transición deja un evento · cubre: RF-3.7, RF-3.8, RF-3.8b, RF-3.8c, RF-3.8d, RT-10
- [x] T16 — Descargas `cv.pdf` y `carta.pdf` · test: en `borrador` → 403; desde `aprobada` sale un PDF; con el estético elegido se sirve su archivo original; solo la dueña · cubre: RF-3.8b, RF-3.8c
- [x] T17 — Pegar la respuesta, confirmar y descartar la propuesta · test: el texto no queda en ninguna tabla tras clasificar; confirmar aplica la transición y deja el evento con la etiqueta; descartar no cambia nada · cubre: RF-3.9

### Bloque F · Pantallas
- [x] T18 — Tablero `/candidaturas` y pestaña «Candidaturas» · test: página solo con sesión; JS sin `innerHTML`; columnas por estado con «Cerradas» plegada; marca «Te toca revisar»; en móvil, apilado · cubre: RF-3.10
- [x] T19 — Pantalla de candidatura · test: muestra el CV base elegido y por qué; CV y carta legibles y editables; tras editar el CV aparece «Guardar como mi CV base» con el nombre propuesto editable y el aviso de que la versión anterior queda en el historial; huecos y avisos visibles; la casilla «He revisado los avisos» habilita aprobar; los botones cambian con el estado; historial visible · cubre: RF-3.8, RF-3.8b, RF-3.9, RF-3.10
- [x] T20 — Botón «Preparar candidatura» en Recomendadas e historial en la pantalla de CV base · test: crea la candidatura sin pedir CV base y lleva a ella; sin CV base pide generarlo; cada CV base tiene «Historial» plegado con sus versiones, las líneas añadidas y quitadas se distinguen sin depender solo del color, y «Volver a esta versión» funciona; JS sin `innerHTML` · cubre: RF-3.7b, RF-3.8d

### Bloque G · Consola y cierre
- [x] T21 — Consola (`agente correr` de los 6 agentes, `flujo correr candidatura --usuaria --oferta`, `flujo correr clasificar_respuesta`, `eval correr cv|respuestas`) · test: cada comando corre en simulado; `--paso-a-paso` y `--traza` guardan un JSON por paso; `--oferta` funciona con `--ofertas f.json` sin API · cubre: RF-3.11, RT-04, RT-05
- [x] T22 — CI, `.env.example` (topes nuevos, marcados como de construcción), README, `specs/system.md` e `specs/index.md` (fase 3 construida) y plan de pruebas manuales (gitignorado) · test: CI corre los dos sets; el README documenta los comandos; import-linter incluye los agentes nuevos · cubre: RF-3.11, RF-3.12, RT-11

### Bloque H · Simplificar la candidatura (cambio del 16-nov-2026, P12-P17)
Sub-bloques, parando entre ellos: H1 contrato y motor (T23-T27) → H2 base de datos y worker
(T28-T29) → H3 API y pantalla (T30-T31) → cierre (T32).

**H1 · Contrato y motor**
- [x] T23 — Esquemas: `Aviso` (`documento`, `frase`, `mensaje`) con la tabla de textos en llano por tipo de problema y de error; `Problema` con `documento`; `EstadoCandidatura` con `vuelta_hecha`, `redacciones_cv`, `redacciones_carta` y `problemas_juez` (salen `vueltas_cv` y `vueltas_carta`) · test: un `Aviso` sin prefijos técnicos para cada tipo; un `repite_cv` con `documento = cv` no valida; `transicion()` sin cambios · cubre: RF-3.4, RF-3.6c
- [x] T24 — Herramientas `elegir_cv_base` y `avisos_vigentes` · test: gana familia y sector, después familia, después sector, después el más reciente; a igualdad, el más reciente; ignora rechazados y ajenos; lista vacía → error; cada caso da su motivo en llano; `avisos_vigentes` conserva solo los problemas cuya frase sigue literal en el texto · cubre: RF-3.1b, RF-3.6c, RF-3.8
- [x] T25 — Agente `juez-candidatura` y baja de `selector-cv-base`, `juez-cv` y `juez-carta` (carpetas, registro, contrato «independence», tests T05-T07 adaptados) · test: con la puerta simulada devuelve su esquema; el prompt prohíbe reescribir, pide documento y frase en cada problema y conserva el criterio suavizado de `repite_cv`; `horma agente listar` ya no muestra los tres agentes quitados · cubre: RF-3.4, RT-01, RT-13
- [x] T26 — Flujo `candidatura` reescrito · test con respuestas simuladas: sin problemas, 3 llamadas; problemas solo en la carta, 4 (se rehace solo la carta); problemas en el CV, 5 (CV y después carta); solo palabras ATS con origen y juez aprobado, se usa la vuelta; nunca hay segundo juicio; las palabras sin origen van a huecos; `elegir_cv_base` no llama al modelo; `componer` deja avisos estructurados y vigentes y `lista` o `pendiente_de_ti`; cada paso valida `EstadoCandidatura`; pasa la suite parametrizada (RT-12) · cubre: RF-3.1, RF-3.1b, RF-3.3, RF-3.5, RF-3.6c
- [x] T27 — Eval `cv` adaptado (14 casos) · test: los sembrados pasan por `comprobar` + juez único y se rechazan al 100 %; los 2 de selección comprueban `elegir_cv_base` sin coste; los de flujo cuentan ≤ 5 llamadas; `respuestas` sigue igual · **medición real con OK de Mar** (≈ 0,5 USD) · cubre: RF-3.1 a RF-3.6c, RF-3.12
  _16-nov: medición real hecha: 14/14, todos los campos al 100 %, 0,43 USD; los 3 casos de flujo hacen 4 llamadas; cobertura ATS media 0,78._

**H2 · Base de datos y worker** (hecho el 16-nov; hasta H3 fallan 23 tests de `test_f3_t14_t17_api.py`, que usan lo que 0007 quita)
- [x] T28 — Migración 0007 (P16) · test: `upgrade` quita y añade las columnas del plan, convierte los avisos de texto a `Aviso` y los orígenes `candidatura`/`respuesta`; `downgrade` vuelve a dejar el esquema de 0006; RLS sin cambios (una usuaria no lee lo de otra) · cubre: RF-3.8d, P16
- [x] T29 — Tope de coste en la puerta única y worker · test: `capturar(tope=…)` lanza `TopeSuperado` antes de una llamada cuando lo acumulado supera el tope y no llama al proveedor; una tarea que no falla pero supera el tope queda en `error` con motivo y sin reintento (cualquier tipo de tarea); sale el manejador `clasificar_respuesta`; `cargar` da `creado_en` de cada CV base · cubre: RF-3.11, RT-14

**H3 · API y pantalla**
- [ ] T30 — API · test: `/aprobar` sin casilla ni documento aprueba con avisos; `/guardar-cv-base` y `/respuesta*` dan 404; `PATCH` del CV conserva los avisos del juez sobre la carta y los del CV cuya frase sigue, y viceversa; `/reintentar` solo con `preparacion = error` (si no, 409) y encola; `/enviada` sin fecha usa la de hoy y el canal es opcional; «Me han llamado» (`/entrevista`) y «Me han rechazado» (`/cerrar` con `rechazo`) solo cuando son legales; los PDF siempre del CV adaptado; editar un CV base sigue dejando versión (orígenes `edicion`/`restauracion`) · cubre: RF-3.8 a RF-3.9, RT-10
- [ ] T31 — Pantalla de candidatura · test: «Revisa esto» une huecos y avisos, cada aviso junto a su frase y sin prefijos; «Detalles» plegado con CV base, motivo y % ATS; «Aprobar y descargar» sin casilla; «Marcar como enviada» con canal opcional; dos botones de respuesta según el estado; «Reintentar» solo con error; no quedan «Guardar como mi CV base», elección de CV ni «pegar la respuesta»; JS sin `innerHTML`; textos de Recomendadas y CV base sin selector ni CV estético · cubre: RF-3.8, RF-3.8a, RF-3.8b, RF-3.8e, RF-3.9

**Cierre**
- [ ] T32 — Consola, CI y documentos · test: `agente correr juez-candidatura` en simulado; los comandos de los agentes quitados fallan con un mensaje claro; `flujo correr clasificar_respuesta` sigue; CI corre `cv` y `respuestas`; import-linter sin los agentes quitados. Se actualizan `.env.example` (sin `tope_coste_respuesta`), README, `specs/system.md` (agentes de la fase 3), `specs/index.md`, `docs/plan-pruebas-fase3.md` (gitignorado) y `docs/mejora-simplificar-candidatura.md` (hecha). Una candidatura real medida (≤ 5 llamadas, < 1 USD, con OK de Mar) · cubre: RF-3.9b, RF-3.11, RF-3.12, RT-04, RT-11

## Pendiente de la persona (no se puede hacer sin ti)
- Verificar aclaraciones, spec, plan y tareas (campo `verified` de cada documento) antes de T01.
- Instalar `fpdf2` si `uv` falla con certificados (T04).
- Lanzar los evals `cv` y `respuestas` con el modelo real (T10, T11).
- Prueba manual del recorrido completo en el navegador y corregir el tablero al verlo (P5).
- Bloque H: ~~verificar aclaraciones, spec, plan y tareas~~ (hecho el 16-nov); OK antes de gastar en T27 y T32; prueba manual con el plan de pruebas actualizado.
