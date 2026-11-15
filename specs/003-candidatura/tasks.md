---
type: tasks
title: candidatura — Desglose de tareas
description: Tareas pequeñas y comprobables derivadas del plan de la fase 3. Cada una empieza con un test que falla.
tags: [tareas, candidatura, seguimiento]
status: draft
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-15 }
verified: { by: null, at: null }
stale_after: null
---

# candidatura — Tareas

Orden de construcción, por bloques, parando entre bloques: contrato y código puro (A, T01-T04) →
agentes (B, T05-T07) → flujos y evals (C, T08-T11) → base de datos y worker (D, T12-T13) → API (E,
T14-T17) → pantallas (F, T18-T20) → consola y cierre (G, T21-T22). Cada tarea empieza con un test que
falla. Todo se prueba sin llamar al modelo (puerta simulada) salvo la medición real de T10 y T11.

### Bloque A · Contrato y código puro
- [ ] T01 — Esquemas de `horma/schemas/candidatura.py` (`Candidatura`, `EstadoCandidatura`, `EventoCandidatura`, `Hueco`, `Problema`, `TrazaFrase` movida aquí; enumerados de estado, preparación, canal, motivo de cierre y etiqueta) y funciones `transicion()` y `transicion_por_respuesta()` · test: transiciones permitidas y prohibidas (p. ej. `borrador → enviada` falla; `cerrada` desde cualquier estado con motivo; nada sale de `cerrada`); `enviada` exige fecha y canal; «otro» admite texto corto; cada etiqueta da su propuesta y una ilegal da «ninguna» · cubre: RF-3.1, RF-3.7, RF-3.8b, RF-3.9
- [ ] T02 — Herramienta `medir_ats` (se mueve `errores_ats` desde `evals.py`) · test: detecta tablas, imágenes y HTML como antes; cobertura correcta con requisitos y stack de una oferta inventada; separa las ausentes con origen de las que no lo tienen; el eval `cv-base` sigue en verde · cubre: RF-3.5
- [ ] T03 — `verificar_trazabilidad` con varias fuentes y fórmulas de cortesía · test: las llamadas de la fase 2 (un solo texto) dan el mismo resultado; un fragmento del CV base editado es válido; un fragmento de la oferta vale solo para la carta; el saludo y la despedida de la lista no piden traza; una fecha, cargo, empresa o titulación cambiados se rechazan al 100 % · cubre: RF-3.3, RF-3.6, RT-08
- [ ] T04 — Herramienta `generar_pdf` y dependencia `fpdf2` (con fuente TTF libre) · test: un Markdown con encabezados, listas y acentos («Señora», «Educación») da un PDF válido que `pypdf` vuelve a leer con el mismo texto · cubre: RF-3.8b

### Bloque B · Agentes
- [ ] T05 — Agentes `redactor-cv` y `juez-cv` · test: con la puerta simulada devuelven su esquema; el prompt del redactor exige la regla de los huecos, traza por frase y registrar instrucciones; el del juez prohíbe reescribir y pide la lista tipada; ambos en el registro y en el contrato «independence» · cubre: RF-3.2, RF-3.4, RF-3.6b, RT-01, RT-13
- [ ] T06 — Agentes `redactor-carta` y `juez-carta` · test: devuelven su esquema; el prompt del redactor prohíbe repetir el CV y usa las fórmulas cerradas; el juez tiene el problema `repite_cv`; registro e «independence» · cubre: RF-3.6, RF-3.6b, RT-01
- [ ] T07 — Agente `clasificador-respuesta` (modelo pequeño) · test: devuelve una de las 4 etiquetas; el prompt pide registrar las instrucciones y no obedecerlas; registro e «independence» · cubre: RF-3.9, RT-07

### Bloque C · Flujos y evals
- [ ] T08 — Flujo `candidatura` · test: con respuestas simuladas, un CV con error vuelve al redactor con la lista de errores; para en 3 redacciones del CV y 2 de la carta; la vuelta del ATS cuenta dentro de las del CV; las palabras sin origen van a huecos; termina en `lista` o `pendiente_de_ti`; un CV base rechazado o de otra usuaria corta en `elegir_cv_base`; cada paso valida `EstadoCandidatura`; pasa la suite de flujos parametrizada (RT-12) · cubre: RF-3.1, RF-3.1b, RF-3.2, RF-3.3, RF-3.5, RF-3.6
- [ ] T09 — Flujo `clasificar_respuesta` · test: «entrevista» propone `entrevista` solo desde `enviada`; «rechazo» propone `cerrada`; un correo con instrucciones no propone nada; el estado nunca cambia dentro del flujo · cubre: RF-3.9, RT-07
- [ ] T10 — Fixtures inventadas y eval `cv` (12 casos y fixtures de ana en `evals/cv/usuarias/ana/`) · test: el harness exige el 100 % de sembrados rechazados, datos idénticos al maestro, huecos en vez de inventar y adversaria sin efecto; registra la cobertura ATS sin umbral; con un tope bajo simulado se detiene y lo anota · cubre: RF-3.2 a RF-3.6b, RF-3.12, RT-11
- [ ] T11 — Fixtures y eval `respuestas` (15 correos, 3 adversarios) · test: etiqueta ≥ 0,9 y adversarios al 100 % sin efecto · cubre: RF-3.9, RF-3.12, RT-07, RT-11

### Bloque D · Base de datos y worker
- [ ] T12 — Migración 0006 (`candidaturas`, `candidatura_eventos`, índice único parcial, RLS «propia») y `TRUNCATE` de los tests · test: tablas y columnas del esquema; una usuaria no lee las candidaturas ni el historial de otra; no se pueden crear dos candidaturas no cerradas para la misma oferta · cubre: RF-3.7, RF-3.7b, RF-3.10
- [ ] T13 — Worker con `candidatura` y `clasificar_respuesta` y topes en `config.py` · test: guarda CV, carta, trazas, huecos, avisos y `preparacion`; un tope bajo deja `preparacion = error` con motivo; `respuesta_pendiente` queda vacío tras éxito y tras error · cubre: RF-3.9, RF-3.11, RT-14

### Bloque E · API
- [ ] T14 — `POST/GET /api/candidaturas` y detalle · test: crear encola la tarea; CV base ajeno o rechazado → rechazado; segunda candidatura viva para la misma oferta → 409; aviso si el CV base está desfasado; el tablero sale agrupado por estado · cubre: RF-3.1b, RF-3.7b, RF-3.10
- [ ] T15 — Editar, aprobar, enviada, entrevista, cerrar e historial · test: editar solo en `borrador` y sin llamar al modelo; aprobar con avisos sin marcarlos → 400; otra usuaria no aprueba (RLS); `enviada` sin aprobar → rechazada; cada transición deja un evento · cubre: RF-3.7, RF-3.8, RF-3.8b, RF-3.8c, RT-10
- [ ] T16 — Descargas `cv.pdf` y `carta.pdf` · test: en `borrador` → 403; desde `aprobada` sale un PDF; con el estético elegido se sirve su archivo original; solo la dueña · cubre: RF-3.8b, RF-3.8c
- [ ] T17 — Pegar la respuesta, confirmar y descartar la propuesta · test: el texto no queda en ninguna tabla tras clasificar; confirmar aplica la transición y deja el evento con la etiqueta; descartar no cambia nada · cubre: RF-3.9

### Bloque F · Pantallas
- [ ] T18 — Tablero `/candidaturas` y pestaña «Candidaturas» · test: página solo con sesión; JS sin `innerHTML`; columnas por estado con «Cerradas» plegada; marca «Te toca revisar»; en móvil, apilado · cubre: RF-3.10
- [ ] T19 — Pantalla de candidatura · test: CV y carta legibles y editables; huecos y avisos visibles; la casilla «He revisado los avisos» habilita aprobar; los botones cambian con el estado; historial visible · cubre: RF-3.8, RF-3.8b, RF-3.9, RF-3.10
- [ ] T20 — Botón «Preparar candidatura» en Recomendadas · test: abre el selector con el CV base del sector marcado; sin CV base pide generarlo; tras crearla lleva a la candidatura · cubre: RF-3.7b

### Bloque G · Consola y cierre
- [ ] T21 — Consola (`agente correr` de los 5 agentes, `flujo correr candidatura --usuaria --oferta`, `flujo correr clasificar_respuesta`, `eval correr cv|respuestas`) · test: cada comando corre en simulado; `--paso-a-paso` y `--traza` guardan un JSON por paso; `--oferta` funciona con `--ofertas f.json` sin API · cubre: RF-3.11, RT-04, RT-05
- [ ] T22 — CI, `.env.example` (topes nuevos), README, `specs/system.md` e `specs/index.md` (fase 3 construida) y plan de pruebas manuales (gitignorado) · test: CI corre los dos sets; el README documenta los comandos; import-linter incluye los agentes nuevos · cubre: RF-3.11, RF-3.12, RT-11

## Pendiente de la persona (no se puede hacer sin ti)
- Verificar aclaraciones, spec, plan y tareas (campo `verified` de cada documento) antes de T01.
- Instalar `fpdf2` si `uv` falla con certificados (T04).
- Lanzar los evals `cv` y `respuestas` con el modelo real (T10, T11).
- Prueba manual del recorrido completo en el navegador y corregir el tablero al verlo (P5).
