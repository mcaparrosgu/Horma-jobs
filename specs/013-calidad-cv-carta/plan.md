---
type: plan
title: calidad-cv-carta — Plan
description: Piezas, archivos y costes de la spec 013 (paso 3 del PRD) — varias citas, niveles de idioma y lector del PDF en código, contacto fuera de la IA, rúbricas y guías de cartas en redactores y juez, agentes lector-ia e ideas-logros, saludo a la persona de selección, relectura tras la vuelta, eliminatorios, diseños y editor con formato.
tags: [plan, cv, carta, pdf, panel, evals]
status: active
sources: [./spec.md, ./clarifications.md, ../system.md]
generated: { at: 2026-11-26 }
verified: { by: human, at: 2026-11-26 }
stale_after: null
---

# calidad-cv-carta — Plan

Dos agentes nuevos de modelo pequeño (`lector-ia` e `ideas-logros`), sin tablas nuevas y sin pantallas nuevas. Las rutas son las del
26-nov: se comprueban antes de tocar. Se construye después del paso 5 (D-095), con el paso 2 cerrado (spec 012 fusionada); la prueba propia del PDF
(DEP-05) está hecha (26-nov).

**Simple primero.** Descartado: tres agentes nuevos para el panel (F2-D1: el programa es código y la persona es el
juez); el `matcher` como lector IA (solo lee un perfil y lo rehace el paso 2, D-041); un agente solo para la carta
(F2-D5); cambiar el esquema del perfil para tareas y logros (D-040); una librería de editor (RES-01); listas de
verbos y de cargos (D-054); una tabla fija de ideas por familia de puestos (D-055: el agente da preguntas del puesto
concreto por ~0,001 USD).

## H · Hechos, PDF y contacto (RF-13.1, 13.2, 13.13, 13.20, 13.24, 13.25) — rama `calidad-h`, 0 USD
- **Niveles de idioma:** `tools/verificar_trazabilidad.py` gana la tabla de S1: un nivel de la línea vale si es el
  de la cita o su equivalente. Sin listas de verbos ni de cargos (D-054); las cabeceras, como hoy.
- **Varias citas:** `TrazaFrase` (`schemas/candidatura.py`) gana `fragmentos` (hasta 3); `fragmento` se conserva y
  las trazas guardadas siguen valiendo. El verificador comprueba cada cita y compara la línea con su unión. Los
  prompts que lo piden van en el bloque R.
- **Contacto:** esquema `Contacto` (correo, teléfono, ciudad, LinkedIn) y una columna JSON en la tabla de la usuaria
  (migración Alembic, con RLS), fuera del perfil y de las preferencias, que leen los agentes. API por su servicio;
  el correo se prellena con el de la identidad de Google (`web/auth/identidad.py`). Bloque «Tu nombre y contacto»
  en Perfil, junto al nombre (`perfil.js`).
- **Contacto fuera del modelo:** el worker pasa `contacto` al flujo solo para `entregar`; ninguna entrada de agente lo
  lleva. Test: una candidatura simulada con correo y teléfono no los tiene en ningún prompt (NFR-04).
- **PDF:** `generar_pdf` recibe `contacto` y lo escribe bajo el nombre como una línea de texto; en la carta, en la
  cabecera, y el nombre al pie.
- **Lector de programas:** `tools/leer_pdf.py` (código) recibe el PDF, su Markdown y el contacto, y devuelve los
  fallos (graves o no). Usa `pypdf`, que ya está: texto y orden comparados con las líneas del Markdown; color y
  tamaño de letra con los visitantes (la misma técnica que `convertir_cv` en la spec 012, RF-12.24, que se
  reutiliza); metadatos; fuentes incrustadas; peso. Graves: texto, orden, contacto, oculto y fuentes.
- **Aprobar:** el servicio de candidaturas compone y lee el PDF antes de reanudar el flujo; con un fallo grave
  responde con el motivo y no aprueba, y avisa por `web/alertas.py`. «Tu CV completo» (`tools/descargar.py`), igual.

## R · Redacción, lectores y eliminatorios (RF-13.3 a 13.12, 13.14 a 13.17, 13.21, 13.29 a 13.33) — rama `calidad-r`
- **Rúbricas en código:** `tools/rubrica_cv.py` y `tools/rubrica_carta.py`, llamadas desde `comprobar`. Devuelven
  errores (a la vuelta) y sugerencias (a la vuelta, sin forzar) según S3.
- **`medir_ats`:** las tres sugerencias de F2-D3; la cobertura queda como dato. Los genéricos de S17, en una lista
  junto a `_respaldada`.
- **Persona de selección:** `OfertaExtraida` gana `persona_seleccion` y `tratamiento_seleccion` (opcionales) y
  `agents/extractor_oferta/prompt.md`, la regla para sacar el nombre tal cual y el tratamiento solo si la oferta lo
  deja claro (D-060); el código la borra si no está literal en el texto de la oferta (S19). Sin migración
  si la oferta se guarda como JSON; si no, una columna nueva (se comprueba antes de tocar).
- **Tratamiento y carta que no se pide:** `tools/tratamiento.py` (tú o usted por la oferta, S6) y una regla que detecta
  «sin carta de presentación» y similares; con ella, el flujo salta `redactar_carta`.
- **Eliminatorios:** `tools/eliminatorios.py` (código) sobre los huecos y `oferta.requisitos` (S11). El estado de la
  candidatura gana `eliminatorios`; el detalle de la oferta en Ofertas los calcula al pedirlo, como las condiciones
  de RF-12.25.
- **Prompts:** `redactor-cv` (rúbrica, tareas y logros de D-040, varias citas y el ejemplo de viñeta de F2);
  `redactor-carta` (rúbrica, las reglas y los patrones de las guías de clarifications, D-056, el ejemplo ideal de F2
  en lugar del de hoy, saludo de RF-13.10 en lugar de los de hoy y tratamiento; sigue sin firmar: el nombre lo pone
  el código). La lista negra de las guías (K12) va a `tools/rubrica_carta.py`. `juez-candidatura`: E1-E10 y la forma flexible de
  D-054 (otras palabras para lo que la descripción respalda no es inventar). `SalidaJuezCandidatura` gana `persona`:
  pregunta, documento, sí o no y motivo.
- **`lector-ia`:** `agents/lector_ia/` (`prompt.md`, esquemas y `run`, `modelo = "pequeno"`), en el registro. Salida:
  criterios por orden, cada uno con `muestra`, `cita` y si la cita existe (lo comprueba `tools/verificar_citas.py`
  de la spec 012).
- **`ideas-logros`:** `agents/ideas_logros/` (`prompt.md`, esquemas y `run`, `modelo = "pequeno"`), en el registro.
  Entrada: cargo, sector y descripción de una experiencia (no fiables; sin nombre ni contacto). Salida: de 3 a 5
  preguntas. Las preguntas generales, en `tools/ideas_logros.py` (código). Un punto de la API por experiencia, que
  guarda la respuesta con la huella del cargo y la descripción, y la devuelve sin llamar al modelo si no cambian.
- **Flujo** (`flows/candidatura.py`): `redactar_cv` → `redactar_carta` (o se salta) → `comprobar` → `leer` →
  `juzgar` → vuelta única con lo del panel → `comprobar` → `leer` y `juzgar` solo lo rehecho → `componer` →
  `entregar`. De 3 a 6 llamadas al modelo mayor y 1 o 2 al pequeño (hoy, de 3 a 5). `CLAVES_INTERNAS` y las aristas
  de LangGraph, al día; la misma suite con `plain` y `langgraph`.
- **Extractor:** regla en `agents/extractor_perfil/prompt.md` (cada línea de la descripción, entera); métrica
  `lineas_conservadas` en el set `perfil` y un caso nuevo con el recorte del 22-nov.
- **Evals:** casos nuevos en `evals/cv/casos/` (RF-13.30); set `evals/lector-ia/` como `SetEval` en `horma/evals.py`,
  con sus métricas (`acierto`, `citas`, `adversarias`) en `evals/umbrales.json`; en `cv`, `cobertura_ats_media` deja
  de ser umbral (S16) y se añaden `ia_con_prueba` y `persona` (RF-13.32).
- **Etiquetado ciego del set `lector-ia`:** tres subagentes de Claude Code con papeles distintos, como en la spec 012.
  No gastan la API de Horma.
- **Evals de los agentes pequeños:** set `evals/ideas-logros/` (~10 puestos; métricas por código: `preguntas`,
  `sin_datos_suyos`, `adversarias`) y dos casos nuevos en `evals/ofertas/` (con y sin persona de selección).
- **`system.md`:** `lector-ia` e `ideas-logros` entran en la lista de agentes en uso (de 9 a 11).

## D · Lo que ve ella (RF-13.18, 13.19, 13.22, 13.23, 13.26 a 13.28, 13.34, 13.35) — rama `calidad-d`
- **«Cómo lo leerán» y eliminatorios:** `candidatura.js`, `textos.js` y `estilo.css`, con un componente de la guía
  (primero en la guía). La línea de eliminatorios en el detalle de Ofertas (`ofertas.js`). «Detalles» deja el %.
- **Diseños:** `generar_pdf` gana `diseno` con tres temas (tipografía, color de acento y espaciado). Dos familias OFL
  más en `horma/assets/fuentes/` (por ejemplo, Source Serif 4 e IBM Plex Sans), con su licencia. La elección va en la
  petición de aprobar y en la de «Tu CV completo», y se guarda junto al contacto, no en las preferencias. Tras
  aprobar, los PDF quedan fijos, como hoy.
- **«Ideas para medirlo»:** en el aviso «Sin cifras» de `perfil.js`, un botón por experiencia que abre las preguntas
  generales al momento y las del puesto al llegar, con el texto «Solo cuenta lo que escribas en tu experiencia».
  Componente de la guía (primero en la guía).
- **Papelería de la carta:** `_carta` escribe la cabecera del diseño, ciudad y fecha larga, el destinatario si consta
  y el nombre al pie.
- **Editor:** `static/editor.js` (sin librerías): zona editable, botones Negrita, Lista y Título en el CV, ninguno en
  la carta; pegar sin formato; Ctrl+B; conversión al Markdown de siempre (`#`, `##`, `-`, `**`). Sustituye al cuadro
  de texto de `candidatura.js`. Primero en la guía, con 44 px y uso con teclado.
- **Landing** (`index.html`): solo lo que funciona; el mensaje (F7-D1) pasa al paso 9 (D-066).

## Costes
Base: el eval `cv` real del 22-nov (33 casos, 1,74 USD: ~0,053 por caso). Con el lector y la relectura, ~0,06-0,065
por caso. Los evals reales suelen costar más de lo estimado: cada gasto se confirma con Mar antes.

| Qué | Modelo | Estimación |
|---|---|---|
| Set `lector-ia`: una pasada (~20 casos) y repetir los que fallan | pequeño | ~0,1-0,2 USD |
| Eval `perfil` con el caso del recorte (19 casos) | mayor y pequeño | ~0,3-0,6 USD |
| Eval `cv`: casos nuevos y los que fallan, por tandas | mayor y pequeño | ~0,5-1 USD |
| Eval `cv` entero (~45 casos), puerta | mayor y pequeño | ~2,5-3 USD |
| Set `ideas-logros` (~10 casos) y set `ofertas` (2 casos nuevos y una pasada entera) | pequeño | ~0,1-0,2 USD |
| **Total del paso** | | **~3,6-5,2 USD, en varias veces** |

- **El tope de 1 USD por ejecución (RF-2.17) no basta para el `cv` entero:** se pide a Mar subirlo para esa ejecución,
  como el 22-nov.
- **Por candidatura:** de 0,12-0,18 a unos 0,14-0,22 USD (lector: ~0,005 por lectura; relectura del juez, solo con
  vuelta). Dentro de NFR-06 (≤ 1 USD por candidatura).
- **Ideas para medirlo:** ~0,001 USD por experiencia, solo cuando ella lo pide, y gratis al repetir.
