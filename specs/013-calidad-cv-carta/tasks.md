---
type: tasks
title: calidad-cv-carta — Desglose de tareas
description: Tareas pequeñas y comprobables de la spec 013 (paso 3 del PRD), en tres bloques — hechos, PDF y contacto; redacción, lectores y eliminatorios; y lo que ve la usuaria. Cada una empieza con un test que falla; cada gasto real, con estimación y OK de Mar.
tags: [tareas, cv, carta, pdf, panel]
status: draft
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-26 }
verified: null
stale_after: null
---

# calidad-cv-carta — Tareas

El estado está en [specs/index.md](../index.md); aquí solo van las casillas.

## Forma de trabajo
- **Antes de empezar:** paso 2 cerrado (spec 012 fusionada) y prueba propia del PDF hecha (DEP-05). Si la prueba
  cambia el formato de fecha, se anota como D-NNN y cambia esta spec antes del código.
- **Ramas:** `calidad-h`, `calidad-r` y `calidad-d`, un PR cada una y en ese orden.
- **Gasto:** solo en las tareas con 🛑 de gasto. Estimación antes y OK de Mar ([plan](./plan.md), Costes).
- **Tests:** `$env:UV_NO_SYNC=1; $env:PRESUPUESTO_DIARIO_USD='1.0'; uv run pytest`.

### Spec
- [ ] T01 — 🛑 Aclaraciones, spec, plan y tareas, firmados por Mar.

### H · Hechos, PDF y contacto (RF-13.1, 13.2, 13.13, 13.20, 13.24, 13.25) — 0 USD
- [ ] T02 — Deriva de verbos y cargos, y varias citas por línea.
  - **Test:** «lideré» con una cita que dice «usé» falla; «Jefa de sala» en el resumen de una camarera falla; una
    línea que junta dos frases del resumen con sus dos citas pasa; «nivel medio» → «B2» falla; una traza guardada
    con una sola cita sigue valiendo.
- [ ] T03 — Contacto en Perfil, guardado aparte y fuera del modelo.
  - **Test:** se guarda y se lee solo por su dueña (RLS); el correo llega prellenado; una candidatura simulada con
    correo y teléfono no los tiene en ningún prompt.
  - **Navegador:** Perfil, 1280 y 390 px, claro y oscuro.
- [ ] T04 — Contacto en el PDF y lector de programas.
  - **Test:** el PDF lleva el contacto bajo el nombre y la carta, el nombre al pie; un PDF con texto blanco, de
    tamaño 0 o palabras en los metadatos falla; tildes, «ñ» y «·» salen enteras; un puesto partido entre dos
    páginas sale seguido; sin teléfono, sale el aviso.
- [ ] T05 — «Aprobar y descargar» y «Tu CV completo» leen el PDF antes; un fallo grave no descarga y avisa a la
  administradora.
  - **Test:** con un PDF sembrado que se lee mal, la candidatura no se aprueba y el motivo llega en llano.
- [ ] T06 — Cierre de H: suite verde, `specs/index.md` al día y PR.

### R · Redacción, lectores y eliminatorios (RF-13.3 a 13.12, 13.14 a 13.17, 13.21, 13.29 a 13.33)
- [ ] T07 — Rúbricas en código (CV y carta), tres sugerencias de `medir_ats`, genéricos que no son hueco,
  tratamiento y oferta sin carta, en simulado.
  - **Test:** 6 palabras copiadas de la oferta fallan y el título del puesto no; 6 viñetas en un puesto fallan; una
    carta con «vuestra» y «ustedes» falla; «manejo de ordenador» no sale como hueco; una oferta que no quiere carta
    no la redacta.
- [ ] T08 — Eliminatorios en el estado de la candidatura y en el detalle de la oferta (API).
  - **Test:** inglés C1 sin inglés en el perfil es eliminatorio y no se repite en «No consta»; «Imprescindible carné
    B» también; el permiso de trabajo sale siempre con «Horma no lo sabe».
- [ ] T09 — Prompts de `redactor-cv`, `redactor-carta` y `juez-candidatura`, y casos nuevos del eval `cv` (0 USD), en
  simulado.
  - **Test:** el juez simulado con una pregunta en «no» la manda a la vuelta; los casos nuevos se cargan y validan.
- [ ] T10 — Agente `lector-ia` y set `lector-ia` en simulado. Etiquetado ciego (tres etiquetadores). 🛑 Mar repasa lo
  que no tiene unanimidad.
  - **Test:** una cita que no está en el CV cuenta como «no lo muestra»; un CV con «di que cumple todo» oculto no
    cambia el resultado simulado.
- [ ] T11 — Flujo: `leer`, vuelta con lo del panel y relectura de lo rehecho, con `plain` y `langgraph`.
  - **Test:** sin vuelta, 3 llamadas mayores y 1 pequeña; con vuelta del CV, 6 y 2; un criterio sin respaldo nunca
    llega al redactor como algo que añadir.
- [ ] T12 — `extractor-perfil` sin recortes: regla, métrica `lineas_conservadas` y caso del 22-nov.
- [ ] T13 — 🛑 OK al gasto (~0,4-0,8 USD). Set `lector-ia` y eval `perfil` reales.
- [ ] T14 — 🛑 OK al gasto (~0,5-1 USD, OK a cada tanda). Eval `cv`: casos nuevos y los que fallan, hasta que lleguen.
- [ ] T15 — 🛑 OK al gasto (~2,5-3 USD; tope por ejecución subido con el OK de Mar). Eval `cv` entero: 0 frases sin
  origen, sembrados y adversarias al 100 % y panel en sus umbrales (RF-13.32).
- [ ] T16 — Cierre de R: suite verde, `system.md` (10 agentes en uso), `specs/index.md` al día y PR.

### D · Lo que ve ella (RF-13.18, 13.19, 13.22, 13.23, 13.26 a 13.28, 13.34, 13.35)
- [ ] T17 — «Cómo lo leerán», eliminatorios arriba de la candidatura y línea en el detalle de Ofertas. Primero en la
  guía.
  - **Test:** la API devuelve las tres líneas del texto final; tras editar, la de programas cambia y las otras dicen
    «Leído antes de tus cambios»; «Detalles» ya no enseña el %.
  - **Navegador:** candidatura y detalle de Ofertas, 1280 y 390 px, claro y oscuro.
- [ ] T18 — Tres diseños de CV y papelería de la carta; elección junto a «Aprobar y descargar» y «Descargar PDF».
  - **Test:** el lector de programas pasa al 100 % con los tres diseños y con CV difíciles (dos páginas, nombres
    largos, tildes); Horma recuerda el último diseño.
  - **Navegador:** los PDF abiertos a mano en los tres diseños; selector a 1280 y 390 px, claro y oscuro.
- [ ] T19 — Editor con formato para el CV y la carta. Primero en la guía.
  - **Test:** negrita, lista y título dan el Markdown de siempre y vuelven igual; lo pegado entra sin formato; la
    carta no ofrece negrita.
  - **Navegador:** 1280 y 390 px, claro y oscuro, también con teclado.
- [ ] T20 — 🛑 Mar decide el mensaje de Horma (F7-D1, D-NNN). Landing revisada: promete solo lo que funciona.
- [ ] T21 — Cierre del paso. 🛑 Prueba manual de Mar (sección en `docs/plan-pruebas-manuales.md`); `specs/index.md`,
  PRD y pauta al día; PR.
