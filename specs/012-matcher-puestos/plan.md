---
type: plan
title: matcher-puestos — Plan
description: Piezas, archivos y costes de la spec 012 (paso 2 del PRD) — set de evals de puestos, puerta por niveles en código, eval de recomendación ampliado con tres ejecuciones, orden y equidad, citas verificadas, veredicto, condiciones al lado de la nota y correcciones de la usuaria.
tags: [plan, matcher, puestos, recomendacion, evals]
status: active
sources: [./spec.md, ./clarifications.md, ../system.md]
generated: { at: 2026-11-25 }
verified: { by: human, at: 2026-11-25 }
stale_after: null
---

# matcher-puestos — Plan

Sin tablas ni pantallas nuevas. Un agente de producto nuevo, `sinonimos-puestos` (modelo pequeño, D-061; su set de
evals, en el bloque N, D-068), con una columna en `preferencias` (migración 0031), y un agente solo para el eval (el
revisor). Las rutas son las del 25-nov: se comprueban antes de tocar.

**Simple primero.** Descartado: ESCO (medido en F4: 0,41 de cobertura), embeddings como puerta (MAP ~0,5 en
español) y un verificador con modelo en producción (F4-D1: solo si el código no llega). Las condiciones y la nota
de la usuaria se calculan al pedir la lista, sin guardar nada nuevo.

## P · Puestos (RF-12.1 a 12.10) — rama `matcher-p`
- **Set `puestos`:** `evals/puestos/casos/<id>/entrada.json` (perfil) y `esperado.json` (etiqueta por puesto e
  imprescindibles). Se añade a `horma/evals.py` como `SetEval` y a `evals/umbrales.json` con sus métricas propias
  (`ajenos_marcados`, `precision_marcados`, `precision_sin_marcar`, `cobertura`, `equidad`).
- **Etiquetado ciego:** tres subagentes de Claude Code con papeles distintos (estricta, candidata, reclutadora),
  como en 9a. No gastan la API de Horma. Se guarda quién etiquetó y si hubo unanimidad.
- **Medir primero (RF-12.2):** una pasada real del `clasificador_postulante` actual guarda las respuestas en
  `evals/puestos/respuestas/`; las variantes de la puerta se miden sobre ellas en tests, a 0 USD.
- **Puerta por niveles:** `tools/puestos_del_perfil.py` decide el nivel por el campo de donde sale el `dato`
  (igualdad normalizada con el campo entero, no un trozo). `PuestoSugerido` (`schemas/preferencias.py`) gana
  `nivel` (1 o 2) y `tipo_dato` (puesto, titulación o certificación). Las preferencias son JSON: sin migración;
  los puestos ya guardados sin nivel se tratan como nivel 2 hasta que el perfil se rehaga.
- **`relacion` (S1):** `PuestoCandidato` gana `relacion: "mismo" | "afin"`, y el prompt del clasificador la pide y
  deja de proponer puestos que solo justifica una habilidad. Cambia el prompt: eval `perfil` de regresión y
  segunda pasada del set `puestos`.
- **Tope de nivel y genéricos:** listas cortas en código, en `tools/normalizar_titulo.py`. El genérico se filtra
  con la familia en `tools/buscar_ofertas.py` (SQL) y en `casa_con_puestos`, que hoy hacen la frase completa.
- **Set de 9a:** `tests/fixtures/titulos_puestos.json`, con ~50 pares nuevos y la firma de Mar en los dudosos.
- **Sinónimos (D-061):** tabla en `tools/sinonimos_puestos.py` y agente `sinonimos-puestos`, pedido en el worker.
- **CI (D-064):** `puestos` se repite con las respuestas reales grabadas, sin gasto.
- **Pantalla «Qué buscas»** (`ofertas.html`, `ofertas.js`): el nivel 2 sin marcar, con su porqué en texto suave
  bajo la casilla. Primero en la guía.

## G · Copia ciega (RF-12.30 a 12.32)
- **Léxico:** `tools/lexico_genero.py` (`a_copia`, `en_genero`), lista cerrada. Arranca con los puestos y
  titulaciones de los sets `puestos`, `perfil` y 9a; cada palabra nueva entra con su test.
- **Copia:** `PerfilCiego` (`extra="forbid"`) y `copia_ciega(perfil)`; es lo único que reciben el clasificador
  (rama `matcher-p`) y el `matcher` (rama `matcher-n`).
- **Clasificador:** `flows/clasificar_perfil.py`, `flows/perfilar.py`, `tools/puestos_del_perfil.py` y
  `tools/huella_perfil.py`.
- **Búsqueda:** pares irregulares en `tools/normalizar_titulo.py`.
- **Huella de compatibilidad:** con migración, en `matcher-n`.
- **Fuera:** `extractor_perfil`, `generador_cv_base` y `analizador-oferta` (necesitan el original o no leen el
  perfil), lo que ve la empresa, quitar edad y huecos (D-044) y `temperature` (D-048).

## N · Nota y explicación (RF-12.11 a 12.24) — rama `matcher-n`
- **Eval ampliado:** casos nuevos en `evals/recomendacion/casos/`. Los de orden llevan varias ofertas
  (`entrada.json` con `ofertas`); los de equidad van en pareja (`pareja` en `esperado.json`). `horma/evals.py`
  gana las métricas `orden`, `equidad`, `citas` y `revisor`, y `horma eval correr` gana `--veces 3`, con la
  variación por caso en el resultado.
- **Revisor:** `agents/revisor_explicacion/` (prompt, esquemas y `run`, modelo pequeño), llamado solo por el
  harness. Su propio control: casos sembrados con una explicación que no se apoya en su cita.
- **Prompt del `matcher`:** la frase por franjas (RF-12.18), no nombrar las instrucciones embebidas y citas
  literales. Los tramos de la nota que ya están no cambian.
- **Citas verificadas:** `tools/verificar_citas.py` (código: texto normalizado, la cita dentro del perfil o de la
  oferta). En `flows/recomendar.py`, tras cada tanda: las ofertas con una cita que no existe se piden otra vez
  en una sola llamada; si vuelven a fallar, `retirada` con su motivo, como ya se hace con los rasgos personales.
- **Texto invisible:** en `tools/convertir_cv.py`, PDF con los visitantes de `pypdf` (color de relleno y tamaño
  de letra) y DOCX con `w:vanish` y el color blanco. Sin dependencias nuevas; si no basta, se dice antes de
  añadir una.
- **Modelo pequeño:** el eval se corre con `modelo = "pequeño"` sin tocar el agente (opción del harness).
- **CI:** al pasar la puerta, `recomendacion` vuelve a la lista de `evals-reales` en `.github/workflows/ci.yml`.

## V · Lo que ve la usuaria (RF-12.25 a 12.29) — rama `matcher-v`
- **Veredicto:** `veredicto(nota)` en `schemas/match.py`, por código. La API de la lista (`services/
  recomendaciones.py`, `listar`) lo devuelve; no se guarda.
- **Condiciones:** `evaluar_condiciones` devuelve además la lista de faltas («No dice el sueldo»); `listar` la
  calcula con las preferencias actuales. El orden de empate se hace en `ofertas.js`.
- **Corrección de la usuaria:** `listar` toma la última corrección de esa oferta, de cualquier versión del perfil
  (columna `matches.correccion`, sin migración), y devuelve `nota_usuaria` y su motivo. `ofertas.js` ordena,
  filtra y pone el veredicto con ella. «Quitar mi nota» borra la corrección por la API. El texto de ayuda de
  «Corregir explicación» cambia (RF-10.15e).
- **Pantalla:** fila y detalle de Ofertas (`ofertas.js`, `estilo.css`). La línea de condiciones y «Tu nota»,
  primero en la guía.
- **Landing:** se revisa lo que dice de la compatibilidad.

## Costes
Estimación con la última medición real (21 casos, 0,26-0,33 USD: ~0,0125-0,016 por caso). Los evals reales
suelen costar más de lo estimado: cada gasto se confirma con Mar antes.

| Qué | Modelo | Estimación |
|---|---|---|
| Set `puestos`: pasada actual (30 CV y 10 pares de equidad) | pequeño | ~0,1 USD |
| Set `puestos`: segunda pasada con `relacion` | pequeño | ~0,1 USD |
| Eval `perfil`, regresión del clasificador (18 casos) | mayor y pequeño | ~0,3-0,6 USD |
| Eval `recomendacion`, una ejecución entera (~60 casos y revisor) | mayor y pequeño | ~0,8-1 USD |
| Repetir solo los casos que fallan, 3 a 5 veces | mayor | ~0,5-1,5 USD |
| Puerta: 3 ejecuciones seguidas | mayor | ~2,4-3 USD |
| Modelo pequeño: 3 ejecuciones | pequeño | ~0,15-0,3 USD |
| Set `puestos`, 3 pasadas (estabilidad, T27) | pequeño | ~0,15 USD |
| Eval `perfil`, regresión con la copia (T27) | mayor y pequeño | ~0,35-0,45 USD |
| **Total del paso** | | **~5-7,3 USD, en varias veces** |

- **El tope de 1 USD por ejecución (RF-2.17) queda justo** para ~60 casos. Si salta, el eval se para sin daño y
  se pide a Mar subirlo para esa ejecución.
- **`evals-reales` en la CI** pasa de ~2 a ~3 USD por ejecución manual.
