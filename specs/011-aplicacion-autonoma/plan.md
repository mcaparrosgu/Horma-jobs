---
type: plan
title: aplicacion-autonoma — Plan
description: Piezas y archivos de la parte 1 de la spec 011 — medición de destinos (bloque A) y mejoras pequeñas (bloque M). Sin modelo, sin migraciones y sin piezas nuevas de arquitectura.
tags: [plan, envio, medicion, frontend]
status: active
sources: [./spec.md, ../system.md]
generated: { by: claude-code, at: 2026-11-25 }
verified: { by: human, at: 2026-11-25 }
stale_after: null
---

# aplicacion-autonoma — Plan (parte 1)

Sin agentes, sin llamadas al modelo y sin tablas nuevas. Dos ramas, una por bloque: `envio-a` y `mejoras-m`.
Las rutas de archivo son las del 23-nov: se comprueban antes de tocar.

## Bloque A · Medición (RF-11.1)
- `assets/portales.json`: patrones de dirección por portal (Teamtailor, Personio, Greenhouse, Lever, Ashby,
  Workable, SmartRecruiters, Recruitee, Workday, SuccessFactors). Los vetados salen de
  `portales_vetados.json`, que ya existe.
- `tools/resolver_destino.py`: sigue las redirecciones con `tools/descargar.py` (solo `GET`, con su límite) y
  casa la dirección final. Código determinista con tests.
- `services/envios.py` (`medir_destinos`), `horma envios medir` (consola, por la API) y
  `GET /api/admin/envios/medicion` (solo admins): tabla portal · ofertas · exige cuenta.
- Simple primero: la medición se calcula al pedirla; no se guarda en ninguna tabla.

## Bloque M · Mejoras pequeñas (RF-11.25 a 11.28)
- **Aviso de dato personal:** `services/perfil.py` (`AVISO_DATO_PERSONAL`) ya lo genera; falta llevarlo hasta
  la respuesta de la API y pintarlo con `avisar()` en `perfil.js`. Primero, un test que reproduzca que no llega.
- **Fuente con 403:** en `flows/calificar_fuente.py` y `tools/descargar.py`, un 403 pasa a ser un resultado
  «no apta» con motivo, no una excepción.
- **Botones de archivo:** `estilo.css` (`input[type="file"]::file-selector-button`) y los botones de
  `ofertas.html` y `perfil.html`: la clase primaria y la secundaria de la guía.
- **Resaltado en «Añadir oferta»:** el borde del bloque seleccionado, en `ofertas.js` y `estilo.css`.
- **Barras sin borde:** quitar el `outline` de `.barra-compat` y de `.barra-avance .pista`; comprobar el
  contraste de la pista sin él, en claro y en oscuro.
- **Barra de rango:** componente nuevo en la guía (dos `input[type=range]` sobre una pista, con sus dos
  números); sustituye a las dos casillas en `ofertas.html` y `ofertas.js`. Sin librerías.

## Costes
0 USD: nada llama al modelo.
