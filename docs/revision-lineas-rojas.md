---
type: revision
title: Horma — Revisión de líneas rojas (fase 4, RF-4.8b)
description: Cada prompt de los 12 agentes activos y el flujo de aprobación frente a cada línea roja de la constitución, con su prueba y lo pendiente.
tags: [lineas-rojas, seguridad, rgpd]
status: draft
sources: [../specs/constitution.md, ../specs/004-langgraph-salida/spec.md]
generated: { by: claude-code, at: 2026-11-16 }
verified: { by: null, at: null }
stale_after: null
---

# Revisión de líneas rojas

Revisión hecha el 16-nov-2026 sobre los 12 `prompt.md` de `horma/agents/` y el flujo de candidatura.
**Claude revisa, Mar firma** (P9). Una celda con `✓` lleva su prueba; `n/a` lleva su motivo.

## Claves de las pruebas
- **P-NF / P-A9** — `tests/test_f4_t23_lineas_rojas.py`: el prompt trata el contenido como no fiable y
  dice «no las ejecutes»; prohíbe edad, nacionalidad y categorías especiales.
- **G** — la puerta del modelo (`llm/gateway.py` + `llm/vigilancia.py`) marca por código toda
  entrada con órdenes a la IA, acciones prohibidas, texto oculto o bloques codificados, y no
  bloquea (`test_f4_t12_vigilancia`). Esto cubre también a los agentes sin campo
  `instrucciones_embebidas`.
- **RT** — eval `red-teaming`, 20/20 en real (ofertas y correos, T14).
- **TR** — la trazabilidad la verifica el código: cada frase del CV o la carta cita un fragmento
  literal de sus fuentes (`test_f2_t03_trazabilidad`, `test_f3_t03_trazabilidad_fuentes`).
- **RP** — el código descarta rasgos personales (`tools/rasgos_personales.py`): del perfil y del CV
  maestro (`flows/perfilar.py`, `test_f2_t08_t10_flujos`), de la explicación del `matcher`
  (`test_f2_t08_t10_flujos`) y de CV y carta (`flows/candidatura.py`). El esquema del perfil
  no tiene campos para ellos (`test_f2_t01_esquemas`).

## Agentes frente a las líneas rojas

| Agente | Origen (no inventar) | Texto no fiable | Edad, nacionalidad, art. 9 |
|---|---|---|---|
| `extractor_oferta` | Prompt: «copia solo lo que aparece»; vacío si falta | P-NF, G, RT | P-A9 |
| `auditor_oferta` | `senales_fraude` copiadas literalmente (prompt) | P-NF, G, RT | P-A9 |
| `clasificador_oferta` | n/a: etiqueta con taxonomía cerrada (esquema) | P-NF, G, RT | P-A9 |
| `auditor_fuentes` | `citas` literales de las condiciones (prompt) | P-NF, G | P-A9 |
| `extractor_perfil` | Cita literal por dato; sin cita, no entra (prompt + código) | P-NF, G | P-A9, RP |
| `clasificador_postulante` | n/a: etiqueta con taxonomía cerrada | P-NF, G | P-A9, RP |
| `generador_cv_base` | TR (cada línea cita el maestro) | P-NF, G | P-A9; RP vía maestro + TR |
| `matcher` | Cita literal de perfil y oferta (prompt) | P-NF, G | P-A9, RP |
| `redactor_cv` | TR | P-NF, G, RT | P-A9, RP |
| `redactor_carta` | TR | P-NF, G | P-A9, RP |
| `juez_candidatura` | Su trabajo es señalar `sin_origen` e `inflado` (prompt) | P-NF, G | n/a: solo señala, no extrae ni guarda; RP retira lo de CV y carta |
| `clasificador_respuesta` | n/a: devuelve solo la etiqueta | P-NF, G, RT | P-A9 (añadida en T23) |

## Flujo de aprobación y líneas transversales

| Línea roja | Cómo se cumple | Prueba |
|---|---|---|
| Toda candidatura necesita la aprobación de la usuaria antes de cualquier envío | Horma **nunca envía**: no hay código de envío (el único SMTP es el de las alertas a admins). El flujo se **para** antes de `entregar`; solo el botón «Aprobar» de la usuaria reanuda y genera los PDF | `test_f4_t08_consola_pausa` (sin `--aprobar` no hay PDF), `test_f4_t07_aprobar_reanuda`, `test_f3_t14_t17_api::test_una_cerrada_sin_haber_sido_aprobada_no_da_pdf` |
| Las órdenes dentro de ofertas, CV o correos no cambian estados | Los agentes no tocan BD ni disco (RT-01) y devuelven solo datos; el estado solo cambia por la API de la usuaria | `test_f4_t13_aviso_oferta` (oferta adversaria: aviso y nada cambia de estado), RT |
| Nunca LinkedIn ni Indeed | `tools/dominio.py` las excluye por código antes de llamar al modelo y la API no las registra | `test_f1_t03_herramientas`, `test_f1_t04_t06_agentes_flujos::test_linkedin_e_indeed_se_excluyen_sin_llamar_al_modelo`, `test_f1_t10_t15_api_ingesta::test_no_se_registran_linkedin_ni_indeed…` |
| Datos de prueba inventados | Fixtures de `evals/` y `tests/` inventados; `pruebas-manuales/` y los planes de pruebas están en `.gitignore`; CI con gitleaks (`secretos`) | CI `secretos`. **No hay test que lo demuestre**: depende de que Mar use solo CV inventados (T24) |

## Hallazgos

| # | Hallazgo | Estado |
|---|---|---|
| 1 | `clasificador_respuesta` no prohibía edad, nacionalidad ni art. 9 en su prompt (solo «no repitas datos personales») | **Arreglado** en T23: línea añadida al prompt y test P-A9 para los 12 |
| 2 | `generador_cv_base`, `clasificador_oferta`, `clasificador_postulante` y `matcher` dicen «no las ejecutes» pero no tienen campo `instrucciones_embebidas` | **Aceptado:** la línea roja pide registrar; lo registra la puerta (G), solo el tipo de señal y sin texto |
| 3 | El set `red-teaming` cubre ofertas y correos; no cubre CV con órdenes ni ediciones de la usuaria | **Anotado:** los CV con órdenes los cubren los casos 11 y 12 del eval `perfil` y G; ampliar el set antes de usuarias reales |
| 4 | Los prompts no se comprueban con evals reales tras el cambio del hallazgo 1 | **Pendiente:** lo mide `evals-reales` en el PR de cierre (`respuestas` debe seguir ≥ umbral) |

## Firma

La revisión es mía; la responsabilidad de darla por buena es de Mar.

- [ ] Revisada y firmada por Mar: ____________________ (fecha: __________)
