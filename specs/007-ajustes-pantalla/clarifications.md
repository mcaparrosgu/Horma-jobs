---
type: clarifications
title: ajustes-pantalla — Aclaraciones
description: Preguntas abiertas de la fase 7 (ajustes de pantalla pedidos por Mar el 20-nov) y sus respuestas, antes de escribir la spec.
tags: [clarify, frontend, preferencias, perfil, ingesta, matcher]
status: active
sources: [../system.md, ../002-perfil-recomendacion/spec.md, ../005-correcciones-profesor/spec.md, ../006-rediseno-2c/spec.md]
generated: { by: claude-code, at: 2026-11-20 }
verified: { by: human, at: 2026-11-20 }
stale_after: null
---

# ajustes-pantalla — Aclaraciones

## Punto de partida
Mar probó la fase 6 y pidió ajustes de pantalla. Esta fase recoge los que no necesitan agentes nuevos.
Lo demás (portada, oferta original, entrevista, calidad de CV, ingesta automática) va en fases posteriores.

Comprobado en el código (20-nov):
- La oferta guarda `remoto` sí/no. El extractor marca `remoto` verdadero si el texto dice que se puede
  trabajar en remoto, así que **una híbrida puede quedar como remota**.
- `solo_remoto` (Preferencias y filtro de Recomendadas) deja pasar `remoto IS NULL`, `remoto` y
  `pais = 'REMOTO'`: se cuelan híbridas y ofertas sin dato.
- Una oferta sin fecha se marca `fantasma` con el motivo `sin_fecha` (`procesar_oferta.componer`),
  también si la ha pegado la usuaria. Recomendadas enseña `creada_en` como «Publicado» si falta la fecha.
- El `matcher` escribe la explicación en tercera persona («Lucía tiene…»).
- Recomendadas ya traduce el país con `nombrePais`; Preferencias y los filtros enseñan códigos.
- Perfil: Tus CV → Tu estilo → Preguntas pendientes → Tu perfil, todos abiertos. La guía de estilo
  enseña hasta 24 rasgos con su cita.
- Ingesta lista todas las fuentes sin buscador ni filtro.
- Ingesta y Costes ya exigen administradora en el servidor (`exigir_admin`, `HORMA_ADMINS`); en el menú
  solo la portada enseña «Ingesta», y Costes no tiene enlace.

## Preguntas y respuestas
- P1: ¿Las ofertas que ya hay se vuelven a procesar para sacar la modalidad? → R: **no**. Solo las nuevas
  la traen; las existentes quedan sin dato. Coste 0.
- P2: ¿Qué pasa con «fantasma» en las ofertas propias? → R: en las **propias** (pegadas o por URL), la falta
  de fecha deja de ser motivo de fantasma y se muestra «No consta fecha de publicación». «Repetida» y
  «genérica» se mantienen. Las de la ingesta, sin cambios.
- P3: ¿Orden de Perfil? → R: bloques separados, en este orden: Tus CV (abierto) · Mi perfil (abierto) ·
  Preguntas pendientes (desplegable, abierto solo si hay, con el número en el título) · Tu estilo de
  redacción (desplegable, cerrado).
- P4: Texto de Mi perfil → R: «**Horma escribe tus CV y cartas con lo que ves aquí.** Si corriges algo,
  Horma usará tu corrección aunque tu CV original diga otra cosa. Tu CV original no se toca: se queda
  tal como lo subiste.»
- P5: ¿Cómo se compacta el estilo? → R: solo la vista, sin tocar el agente: una frase (registro, persona,
  longitud, viñetas), «Usas» y «Evitas» con 5 rasgos como máximo y «Ver detalle» con todo y las citas.
  «Editar guía» se mantiene.
- P6: ¿Explicaciones en segunda persona también para las ya guardadas? → R: **no**, solo las nuevas; las
  guardadas cambian cuando la oferta se vuelve a puntuar.
- P7: ¿Remoto, híbrido y presencial? → R: **una sola casilla «Solo remoto», estricta**. Cualquier
  presencialidad obligatoria, aunque sea un día al mes, es híbrida. Con la casilla marcada solo pasan las
  ofertas con modalidad remota; las que no tienen el dato **no salen** (excepción a «si falta el dato,
  pasa»). Motivo de Mar: en otras webs «solo remoto» le cuela híbridas.
- P8: Resto de la fase → R: aceptado tal cual: idiomas y países con su nombre entero, buscador y filtro en
  Ingesta, pestaña «Admin» solo para administradoras.
