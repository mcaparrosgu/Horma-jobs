---
type: clarifications
title: matcher-puestos — Aclaraciones
description: Decisiones que sostienen la spec 012 (paso 2 del PRD) — las ya tomadas en F4, F7 y F1, las dos que Mar cerró el 25-nov (D-026 y D-027) y los supuestos de Opus, aceptados por Mar al firmar (25-nov).
tags: [clarify, matcher, puestos, recomendacion]
status: active
sources: [../prd.md, ../002-perfil-recomendacion/spec.md, ../009-cv-maestro-entrevista/spec.md, ../010-simplificacion/spec.md]
generated: { by: claude-code, at: 2026-11-25 }
verified: { by: human, at: 2026-11-25 }
stale_after: null
---

# matcher-puestos — Aclaraciones

## Decisiones ya tomadas (no se repreguntan)
Están en los informes F4 (`docs/investigacion/f4-puestos-afines.md`, apartado 8), F7 (`comparativas.md`) y F1
(documentos de trabajo, fuera del repo). Aquí solo se citan.

| Decisión | Qué dice |
|---|---|
| F4-D1 | Puerta de puestos por niveles de evidencia, en código. El verificador con modelo, solo si no llega al umbral |
| F4-D2 | Solo llega marcado el nivel 1; lo afín, sin marcar y con su porqué |
| F4-D3 | Cambiada por Mar: un puesto genérico casa solo con ofertas de su misma familia |
| F4-D4 | Tope de nivel por código en la sugerencia; el filtro de ofertas no cambia |
| F4-D5 | Se mide antes de construir: set de 30 CV y umbrales del apartado 6 del informe. Mar da el OK al gasto y repasa los dudosos |
| F4-D6 | Sin ESCO ni embeddings ahora. Si la cobertura del set ampliado baja de 0,90, lo primero que se prueba son los embeddings, solo para proponer candidatos |
| F4-D7 | Junior sin ninguna experiencia: los puestos por titulación llegan marcados |
| F4-D8 | El envío automático usa solo puestos de nivel 1 o marcados por ella (se construye en la spec 011, parte 2) |
| F4-D9 | Mar repasa los pares sin unanimidad del set de 9a y se añaden ~50 pares de sinónimos |
| F7-D5 | Veredicto en palabras junto a la nota, puesto por código y por franjas |
| F1-E6 | `matcher` en el modelo pequeño si pasa el eval: se decide con la medición |

## Preguntas a Mar (25-nov)
- **Punto 3: ¿cómo entran las condiciones en la nota?** Dato traído: LinkedIn, Indeed y Jobright no las meten en
  la nota; las enseñan aparte (Indeed destaca «cumple tu sueldo»). → **D-026: como los rivales.** La nota mide
  solo experiencia y formación; al lado, una línea corta dice la condición que falta o no se cumple, y a igual
  nota va antes la que cumple todo.
- **Correcciones: ¿cambian la lista de quien corrige y quién las revisa?** Dato traído: Indeed deja ocultar al
  momento lo que no te interesa; ningún rival deja corregir una nota. → **D-027: su nota manda en su lista**, y
  (añadido por Mar) ella puede leer el motivo que escribió para recordar por qué subió o bajó la nota. Mar las
  revisa antes de cada medición del eval.

## Supuestos (Opus; aceptados por Mar al firmar, 25-nov)
- **S1 · Cómo distingue el código el nivel 1 del 2.** El código mira de qué campo sale el `dato` (puesto,
  titulación, certificación u otro). Además, el modelo dice en la misma llamada si el título es el mismo puesto
  que el dato (traducido, en otro género o con sinónimo) o uno afín (`relacion`). Esa marca solo baja de nivel:
  un dato que no es un puesto entero nunca da nivel 1. Motivo: F4 pone traducciones y sinónimos en el nivel 1,
  y el código solo no las distingue de un puesto distinto.
- **S2 · Familia de los genéricos:** la del perfil. Si el set de 30 CV falla con perfiles de dos oficios, se
  añade la familia de cada puesto en la misma llamada.
- **S3 · Imprescindibles del set de 30 CV:** los proponen los etiquetadores y Mar repasa solo los que no tienen
  unanimidad (F4-D5 limita su trabajo a los dudosos).
- **S4 · Junior (F4-D7):** el título no lleva «junior» (estrecharía el filtro por frase: «Analista de datos
  junior» no casa con «Analista de datos»). El porqué lo dice: «Para empezar, por tu grado en…».
- **S5 · Franjas del veredicto:** 70-100, 50-69, 30-49 y 0-29.
- **S6 · Cita que no existe:** se pide otra vez, una sola, para esas ofertas. Si vuelve a fallar, la explicación
  se retira y la nota se conserva con un aviso (plan del `matcher`, 15-nov).
- **S7 · Orden:** casos de un perfil con cinco ofertas. Acierta si la mejor esperada sale primera y ningún par
  con 20 o más puntos de diferencia esperada sale al revés.
- **S8 · Notas esperadas de los casos nuevos:** la mediana de tres etiquetadores ciegos, como en 9a. Mar repasa
  los casos con más de 10 puntos entre etiquetadores. La nota esperada de un caso existente solo cambia con su
  OK y su motivo escrito: si no, se maquilla el eval.
- **S9 · La corrección vale por oferta,** no por versión del perfil, hasta que ella la quite.
- **S10 · Revisor del eval:** modelo pequeño. No entra en ningún flujo.
- **S11 · Sin `temperature` (D-048):** los modelos de Horma no la admiten. La respuesta se reutiliza por la huella
  de la copia y la variación se mide (RF-12.30e).
- **S12 · La lista blanca se cumple por esquema** (`PerfilCiego`).

## Copia ciega (26-nov)
Requisito de Mar: el género no influye en los puestos sugeridos ni en la nota (D-047). Decisiones D-043 a D-052.

## Fuera de alcance
- ESCO y otras taxonomías (F4-D6). Embeddings, salvo la prueba condicionada de F4-D6.
- Homónimos («Camarera» casa con «Camarera de pisos»): F4 propone sugerir el término excluido; no está decidido.
  Va a `docs/mejoras-futuras.md`.
- Quitar nombre, correo y teléfono antes del modelo (F7-D7): para el clasificador y el `matcher`, ya en la
  012 (RF-12.30); para el resto de agentes, paso 4, spec 015.
- Usar solo el nivel 1 en el envío y gestionar esos puestos en «Configuración» (F4-D8): spec 011, parte 2.
- El embudo filtros → embeddings → modelo: rechazado por Mar.
- Que `analizador-oferta` escriba el puesto normalizado de cada oferta: solo si la familia no basta (F4-D3,
  segundo paso), y como cambio de esta spec.
