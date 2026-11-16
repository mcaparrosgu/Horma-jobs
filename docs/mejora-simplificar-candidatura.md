# Mejora pendiente: simplificar la candidatura (CV y carta)

Estado: **especificada como bloque H de la fase 3** (`specs/003-candidatura/`, P12-P17, T23-T32), sin construir. Decidido el 16-nov-2026: se aborda **antes** de la fase 4 (así LangGraph migra el flujo ya simplificado).

## Por qué
- **Pantalla:** hasta 9 decisiones antes de tener los PDF.
- **Motor:** 6 agentes y de 4 a 11 llamadas al modelo por candidatura.
- **Seguimiento:** pegar la respuesta de la empresa, esperar a que un agente la clasifique y confirmar.
- **Dos fallos:**
  - El tope de coste (1 USD) solo se comprueba si algo falla (`worker.py`, `procesar_una`).
  - Al editar el CV o la carta se borran los avisos del juez (`services/candidaturas.py`).

**Objetivo:** leer → (editar) → Aprobar y descargar. La seguridad no cambia: no se inventa nada.

## A. Pantalla: de 9 decisiones a 3
1. Una sola lista «Revisa esto» con huecos y avisos juntos, en lenguaje llano y sin prefijos técnicos. Cada aviso va junto a la frase que señala.
2. Quitar la casilla «He revisado los avisos». Pulsar Aprobar ya cuenta como revisarlos, y los avisos nunca bloquean.
3. Quitar la elección entre CV adaptado y CV estético: siempre se usa el adaptado.
4. Quitar «Guardar como mi CV base» de la candidatura. Lo que se edita se queda en esa candidatura; el CV base se cambia en su propia pantalla.
5. Plegar en «Detalles» el CV base elegido, el motivo de la elección y el % ATS.
6. Añadir un botón «Reintentar» cuando la preparación falla.

## B. Seguimiento
7. «Marcar como enviada» en un clic: la fecha es la de hoy y el canal, opcional.
8. Sustituir «pegar la respuesta» por dos botones: «Me han llamado» y «Me han rechazado». Así desaparecen el agente clasificador, `flows/clasificar_respuesta.py` y las tres rutas `/respuesta*`.

## C. Motor: de 4-11 llamadas a 3-5
9. Quitar el agente selector. El CV base se elige por código: se compara el sector y la familia de la oferta con los del CV base y, si empatan, gana el más reciente.
10. Un solo juez para el CV y la carta juntos, con una sola vuelta de corrección.
    - Orden: redactar CV → redactar carta → comprobar por código (trazabilidad, rasgos personales, ATS) → juez único → una vuelta si falla → componer.
11. Arreglar los dos fallos: comprobar el tope de coste también cuando todo sale bien, y conservar los avisos del juez sobre el documento que no se ha editado.

## Lo que no cambia
- Cada línea conserva su origen.
- Los estados siguen siendo `borrador → aprobada → enviada → entrevista` y `cerrada`.
- Los PDF solo se generan después de aprobar.
- Sigue habiendo una sola candidatura abierta por oferta.

## Riesgos y costes
- **Contradice aclaraciones ya cerradas de la fase 3:** la casilla de avisos, el CV estético, guardar sobre el CV base, clasificar la respuesta y el selector. Hay que reescribir a la vez `specs/003-candidatura/*`, `specs/index.md`, README, `docs/plan-pruebas-fase3.md` y `.env.example`.
- **Un solo juez con una vuelta corrige menos por su cuenta,** así que habrá más candidaturas con avisos. A cambio, cuesta menos y tarda menos.
- **Puede hacer falta una migración** si se quitan columnas (CV estético y origen «candidatura»). La otra opción es dejarlas sin usar.
- **Se borra código y tests ya hechos:** selector, clasificador y juez de la carta. Quedan en el historial de git.

## Archivos que se tocarán
- **Pantalla:** `horma/web/static/candidatura.js`, `candidaturas.js` y `recomendadas.js`.
- **API:** `horma/web/services/candidaturas.py` y `horma/web/routers/candidaturas.py`.
- **Motor:**
  - `horma/flows/candidatura.py`.
  - Agentes `selector_cv_base/`, `juez_cv/` y `juez_carta/`: los dos jueces se fusionan en uno.
  - `flows/clasificar_respuesta.py` y su agente se quitan.
  - `horma/web/queue/worker.py`.
- **Se reutilizan:** `tools/verificar_trazabilidad.py`, `rasgos_personales.py`, `medir_ats.py`, `generar_pdf.py` y `flows/plain.py`.

## Cómo se comprobará
- `uv run pytest`, con los tests `test_f3_*` adaptados.
- Los evals de CV y carta en modo simulado.
- Una candidatura real para medir el coste: como mucho 5 llamadas y menos de 1 USD.
- Mar recorre en el navegador: Recomendadas → Preparar → leer → editar → Aprobar y descargar → Me han llamado.
