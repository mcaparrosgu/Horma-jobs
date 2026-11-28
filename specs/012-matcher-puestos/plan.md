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
  harness. Ve la copia del perfil y la oferta enteras (D-078). Su propio control: casos sembrados con afirmaciones
  que no están en ellas, también entre otras ciertas.
- **Prompt del `matcher`:** no escribe la frase por franjas (la antepone el código, RF-12.18, D-080), marca cada
  requisito y la relación con el puesto (RF-12.34), no nombra las instrucciones embebidas y cita literal. Los tramos
  de la nota no cambian, salvo que sale «De 90 a 100 solo si además encaja en nivel y sector».
- **Nota acotada (RF-12.35 a 12.37):** función pura `acotar_nota`; el aviso de nivel, por código; `matches` guarda
  nota del modelo, marcas y relación (migración 0033, D-090).
- **Citas verificadas:** `tools/verificar_citas.py` (código: texto normalizado, la cita dentro del perfil o de la
  oferta). En `flows/recomendar.py`, tras cada tanda: las ofertas con una cita que no existe se piden otra vez
  en una sola llamada; si vuelven a fallar, `retirada` con su motivo, como ya se hace con los rasgos personales.
- **Texto invisible:** `tools/texto_invisible.py`. PDF: se dibuja la página con `pypdfium2` (ya instalado) y se quita la
  letra cuyo recuadro sale de un solo color; así el blanco sobre una banda de color se conserva. DOCX: marcas de
  oculto, tamaño 0 y blanco sin fondo. Sin dependencias nuevas.
- **Modelo pequeño:** el eval se corre con `modelo = "pequeño"` sin tocar el agente (opción del harness).
- **CI:** al pasar la puerta, `recomendacion` vuelve a la lista de `evals-reales` en `.github/workflows/ci.yml`.

## V · Lo que ve la usuaria (RF-12.25 a 12.29) — rama `matcher-v`
- **Veredicto:** `veredicto(nota)` en `schemas/match.py`, por código. La API de la lista (`services/
  recomendaciones.py`, `listar`) lo devuelve; no se guarda.
- **Condiciones:** `evaluar_condiciones` devuelve además la lista de faltas («No dice el sueldo»); `listar` la
  calcula con las preferencias actuales. El orden de empate se hace en `ofertas.js`.
- **Corrección de la usuaria:** `listar` toma la última corrección de esa oferta, de cualquier versión del perfil
  (columna `matches.correccion`, sin migración), y devuelve `nota_usuaria` y su motivo. `ofertas.js` ordena,
  filtra y pone el veredicto con ella. «Quitar la mía» borra por la API la corrección de la oferta en todas sus
  versiones (D-118); una corrección sin número hereda la nota anterior (D-119). El texto de ayuda de
  «Corregir explicación» cambia (RF-10.15e).
- **Pantalla:** fila y detalle de Ofertas (`ofertas.js`, `estilo.css`). La línea de condiciones y «La tuya»,
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
| Eval `recomendacion`, una ejecución entera (60 casos, 3 pasadas y revisor; D-077) | mayor y pequeño | ~2,4-3 USD |
| Repetir solo los casos que fallan, 3 a 5 veces | mayor | ~0,5-1,5 USD |
| Puerta: 3 ejecuciones seguidas | mayor | ~2,4-3 USD |
| Modelo pequeño: 3 ejecuciones | pequeño | ~0,15-0,3 USD (T16: 0,305, cortada por el tope en 56 de 60 casos) |
| Set `puestos`, 3 pasadas (estabilidad, T27) | pequeño | ~0,15 USD |
| Eval `perfil`, regresión con la copia (T27) | mayor y pequeño | ~0,35-0,45 USD |
| Prueba de la corrección: 27 casos, dos tandas como mucho (T14f) | mayor | hasta 0,45 USD cada una |
| Ejecución completa de la corrección (T14g; vale como T15, D-086) | mayor y pequeño | ~2,3-2,8 USD (tope 3,0) |
| Cierre de T14 por etapas (D-100): pasada 1 (T14m, 0,76 USD; no llegó) | mayor y pequeño | ~0,79 USD |
| Cierre de T14, tres pasadas nuevas (D-113): pasada 1 y, si pasa, pasadas 2 y 3 (T14t y T14u) | mayor y pequeño | ~0,76 + ~1,52 USD (tope del cierre, 3,1; gastado: 0,755 + 1,522) |
| **Total del paso** | | **~5-7,3 USD, en varias veces** |

- **Corrección de T14 (D-086):** hasta 3,9 USD más, sobre 2,19 ya gastados en T14. El total del paso puede pasar de
  lo previsto (gastado en T14f y T14g: 3,09 USD; T14g no pasó); si T14g pasa, se ahorran los ~2,4-3 USD de T15.
  El cierre de T14 tiene su propio tope: 3,1 USD (D-113; era 2,6 con D-100). Gastado: 3,04 (T14m, T14t y T14u).
- **El tope de 1 USD por ejecución (RF-2.17) queda justo** para ~60 casos. Si salta, el eval se para sin daño y
  se pide a Mar subirlo para esa ejecución.
- **`evals-reales` en la CI** pasa de ~2 a ~3 USD por ejecución manual.
