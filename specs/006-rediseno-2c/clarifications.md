---
type: clarifications
title: rediseno-2c — Aclaraciones
description: Preguntas abiertas del rediseño visual «Editorial» (dirección 2c) de todas las pantallas, resueltas con la persona antes de escribir la spec.
tags: [clarify, frontend, diseno, accesibilidad, tokens]
status: active
sources: [../system.md, ../constitution.md, ../002-perfil-recomendacion/spec.md, ../003-candidatura/clarifications.md, ../005-correcciones-profesor/spec.md]
generated: { by: claude-code, at: 2026-11-19 }
verified: { by: human, at: 2026-11-19 }
stale_after: null
---

# rediseno-2c — Aclaraciones

## Punto de partida
Mar ha elegido la dirección visual 2c «Editorial» para sustituir el aspecto actual (marco
Passe-Partout, paleta cuero y latón, Georgia), que el propio CSS marcaba como provisional.
- El diseño está cerrado solo para **Recomendadas**: escritorio de 1280 px y móvil de 390 px, en claro y en oscuro.
- El resto de pantallas se rediseña con los mismos tokens y componentes.
- El material de diseño original queda fuera del repo; al repo solo va lo técnico.

Comprobado en el código (19-nov):
- La web son HTML, CSS y JS planos en `horma/web/static/`. Hay un solo `estilo.css` y `comun.js` hace de librería de componentes.
- La CSP es estricta (`default-src 'self'`; `style-src 'self'`): no admite estilos en línea ni hojas externas, así que Google Fonts no carga.
- Los tests fijan el marco `class="pp"`, varios ids y textos literales, y la ausencia de «Condiciones» (RF-5.2).
- No hay layout compartido: la cabecera se copia a mano en cada HTML.

## Preguntas y respuestas
- P1: El diseño 2c muestra la columna «Condiciones», que el profesor pidió quitar (RF-5.2). ¿Qué
  se hace? → R: **sin «Condiciones»**. Se mantienen RF-5.2 y su test; fuera también el icono de barras.
- P2: El diseño tiene 5 pestañas y Horma 6, porque incluye «Añadir oferta» (RF-5.3b). ¿Qué se
  hace? → R: **se mantienen las 6**. El menú del móvil pasa a 6 columnas (y, por pedido de Mar el 20-nov, va arriba).
- P3: ¿Cómo se garantiza que las pantallas nuevas usen el diseño 2c y no un estilo por defecto? →
  R: con **`tokens.css` como única fuente de valores de diseño**, esta spec como guía técnica de
  componentes y una regla en `AGENTS.md`. Los `.dc.html`, el prompt y las capturas no se suben.

## Supuestos que Mar revisa al leer
No se han preguntado uno a uno:
- **Fuentes autoalojadas.** Familjen Grotesk y DM Mono se sirven desde `/static/fuentes/` (woff2 con la licencia OFL). No se relaja la CSP.
- **Los filtros conservan sus campos.** Siguen saliendo de Preferencias (`/api/preferencias/opciones`), con el sueldo en €/año como hoy y con el orden. Del diseño se toma el aspecto, no los campos de ejemplo (Sector, Contrato, Nivel, País, Idiomas).
- **«Recomendar» sigue siendo un solo botón**, junto al contador, que puntúa todas las ofertas pendientes. En la fila sin nota se ve «Sin puntuar», sin botón propio. Un botón por fila haría creer que solo puntúa esa oferta.
- **«Modificar» pasa a llamarse «Corregir explicación»** y va en la fila desplegada, junto a «Preparar candidatura», que deja de ser una columna.
- **Cabecera:**
  - A la derecha, el nombre del perfil con su inicial en un círculo. Si no hay nombre, no sale nada. Nunca foto.
  - Un botón de tema claro/oscuro.
  - «Salir».
- **Las pantallas de admin** (`/ingesta`, `/costes`) usan los tokens y la cabecera, sin las pestañas de usuaria.
- **Se conservan las funciones, los ids y los textos** que fijan los tests. Solo cambian el marcado y el estilo. Los tests que piden el marco Passe-Partout pasan a pedir `tokens.css`.

## Fuera de alcance
- Funciones nuevas: el rediseño no añade ni quita nada de lo que hace cada pantalla.
- Logotipo: la marca sigue siendo el cuadrado lima con la palabra «Horma».
- Los PDF generados (CV y carta) no cambian de aspecto.
