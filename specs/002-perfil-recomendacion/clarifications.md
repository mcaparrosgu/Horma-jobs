---
type: clarifications
title: perfil-recomendacion — Aclaraciones
description: Preguntas abiertas de la fase 2 resueltas con la persona antes de escribir la spec, más los supuestos.
tags: [clarify, perfil, recomendacion]
status: active
sources: [../system.md, ../001-ofertas/plan.md, ../../docs/Horma v2_ requerimientos por fases.pdf]
generated: { by: claude-code, at: 2026-11-14 }
verified: { by: human, at: 2026-11-14 }
stale_after: null
---

# perfil-recomendacion — Aclaraciones

## Preguntas y respuestas
- P1: Las preferencias salen solo del CV (RF-2.3), pero el filtro duro usa también contrato, remoto, sueldo mínimo y nivel, que el CV no suele traer. → R: **la usuaria los rellena a mano**; un campo vacío no filtra.
- P2: ¿Qué pasa con una oferta a la que le falta un dato del filtro (p. ej. sin país)? → R: **pasa el filtro**; «sin descartar nada más».
- P3: ¿Formato de los CV base? → R: **Markdown en pantalla** en esta fase; la descarga en PDF llega en la fase 3.
- P4: ¿Cómo pasa una corrección de explicación (RF-2.9) al eval? → R: **se guarda en la base de datos**; un comando la convierte en caso del eval solo cuando Mar la revise, para que no entren datos reales en el repo.
- P5: ¿Cuántos datos de prueba? → R: **12 CV inventados** para `evals/perfil/` (2 con instrucciones escondidas) y **20 pares perfil-oferta** para `evals/recomendacion/`.
- P6: ¿Tope de gasto al medir con el modelo real? → R: **1 por ejecución de eval**, en la unidad en que mide `horma.llm` (por confirmar si es USD o EUR al escribir el plan).
- P7: Si la usuaria cambia el perfil (responde una pendiente, corrige un dato o sube otro CV), ¿qué pasa con CV base y notas? → R: **versión nueva del perfil + aviso**. Lo anterior queda guardado pero marcado como desfasado y se regenera solo cuando ella lo pide.
- P8: ¿Cómo se combinan varios CV? → R: **un único perfil con los datos fusionados**, cada dato con el CV del que sale. Si dos CV se contradicen, el dato va a `preguntas_pendientes`; no se elige por ella.
- P9: ¿Rango de compatibilidad por defecto? → R: **40-100**, editable por la usuaria. Ojo: es más amplio que el ejemplo del documento (60-100), así que el matcher puntuará más tandas y costará más.
- P10: ¿Sectores de los perfiles de prueba? → R: **los mismos 5 de la fase 0**: hostelería, sanidad, tecnología, administración y comercio.
- P11: ¿Dónde se guardan los CV subidos y el CV estético? → R: **volumen de Docker** de la API, con nombre aleatorio y descarga solo por la API.

- P12: ¿Cómo localiza la usuaria cada CV? → R: **ponerle el nombre que quiera** a cada CV (subido, base o estético), cambiable, sin repetir nombre en su cuenta (RF-2.1b).
- P13: ¿Cómo son los filtros de preferencias? → R: **como The Hub**: casillas para puestos, sector, contrato, nivel, país e idiomas; casilla de solo remoto y de solo con salario publicado; un campo para escribir el sueldo mínimo; contador de ofertas por casilla (RF-2.8, RF-2.8b). Referencia: https://thehub.io/jobs?countryCode=REMOTE&paid=true&sorting=newJobs (en esa página solo he podido leer los nombres de los filtros, no el tipo de control).
- P14: ¿Cómo es la pantalla de ofertas recomendadas? → R: **muy parecida a la maqueta** `dashboard.png` de Mar (pestañas, barra de filtros, contador, bloque plegable, tabla con cabeceras explicadas) (RF-2.15b).
- P15: ¿Qué hacemos con lo que queda fuera de alcance? → R: **que no se pierda**: se apunta y, si hay tiempo, se añade al final de la construcción de la fase.

- P16: País, contrato e idiomas de las ofertas son texto libre y no hay campo país. ¿Quién los normaliza? → R: **código sin IA, al guardar la oferta**, en columnas nuevas (toca una línea del guardado de la fase 1).
- P17: ¿Cómo se compara el sueldo mínimo? → R: **euros brutos al año, calculado en el servidor** (mensual × 12). **La pantalla muestra siempre el sueldo tal como lo dice la oferta.** Sin sueldo o en otra moneda: pasa el filtro como «no comparable».

## Decisiones derivadas
- `Preferencias` tiene dos grupos de campos: los que se rellenan desde el CV (puestos, países, idiomas, sector) y los que escribe la usuaria (contrato, remoto, sueldo mínimo, nivel), con `origen` distinto.
- `Perfil` lleva un número de versión. La caché del matcher es por (usuaria, oferta, versión del perfil) y los CV base se generan una vez por versión (RF-2.5, RF-2.8).
- `buscar_ofertas` trata el dato ausente de una oferta como «pasa»; el pre-orden por taxonomía y fecha sigue aplicándose.
- Los agentes no tocan disco (RT-01): guardar y servir archivos es cosa de la API y de `convertir_cv` fuera del agente.

## Supuestos (revisables)
- El tope de 1 por ejecución se aplica al set completo de evals de recomendación, no por caso.
- Con rango 40-100 y un catálogo pequeño, el matcher puede cubrir todo el rango en una o dos tandas de 30.
- Se reutiliza la taxonomía de `horma/schemas/taxonomia.py` sin cambios; si un perfil de prueba no encaja, se propone ampliarla en la spec, no se toca aquí.
- Límite de tamaño de CV subido y tipos permitidos (PDF, DOCX, Markdown): se fijan en la spec.
