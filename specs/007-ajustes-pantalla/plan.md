---
type: plan
title: ajustes-pantalla — Plan técnico
description: Archivos y cambios que cubren cada requisito de la fase 7 — columna modalidad, filtro estricto, fantasma de ofertas propias, prompt del matcher y ajustes de Perfil, Ingesta y cabecera.
tags: [plan, frontend, extractor, matcher, migracion]
status: active
sources: [./spec.md, ./clarifications.md, ../system.md]
generated: { at: 2026-11-20 }
verified: { by: human, at: 2026-11-20 }
stale_after: null
---

# ajustes-pantalla — Plan

## Arquitectura
No hay agentes, flujos ni rutas nuevas. Se respetan RT-01, RT-02 y RT-12 (agentes sin estado; la
composición, en `horma/flows/`).

| Requisito | Dónde |
|---|---|
| RF-7.1 modalidad | migración `0019_fase7_modalidad.py`; `schemas/oferta.py`; `agents/extractor_oferta/prompt.md`; `tools/origen_oferta.py`; `repositories/ofertas.py` y `matches.py`; `evals.py` y `evals/ofertas/casos/` |
| RF-7.1c filtro | `tools/buscar_ofertas.py`; `tools/evaluar_condiciones.py`; `routers/recomendaciones.py` (rango de nota) |
| RF-7.1d-e pantalla | `preferencias.html`, `recomendadas.js`, `comun.js` |
| RF-7.2 propias | `queue/worker.py` (pasa `propia`); `flows/procesar_oferta.py` (`componer`); `recomendadas.js`, `anadir-oferta.js` |
| RF-7.3 segunda persona | `agents/matcher/prompt.md`; comprobación en `evals.py` |
| RF-7.4 nombres | `comun.js` (`nombrePais`, `nombreIdioma`); quien pinte países o idiomas |
| RF-7.5 Perfil | `perfil.html`, `perfil.js` |
| RF-7.6 Ingesta | `ingesta.html`, `ingesta.js` |
| RF-7.7 Admin | `comun.js` (`PESTANAS`), `index.html`, `app.js`, `ingesta.html`, `costes.html` |

## Modalidad (RF-7.1)
- **Base de datos:** columna `ofertas.modalidad text NULL CHECK (modalidad IN ('remoto','hibrido','presencial'))`.
  Sin rellenar las filas existentes (P1).
- **Esquema:** `OfertaExtraida.modalidad: Literal["remoto","hibrido","presencial"] | None`. `remoto` se queda
  por compatibilidad y lo **deriva el código** cuando hay modalidad: `remoto = modalidad == "remoto"`. Así,
  una híbrida deja de contar como remota también para `_pais` («REMOTO»).
- **Extractor:** el prompt sustituye la regla de `remoto` por la de `modalidad`, con los criterios de
  RF-7.1. Por ejemplo: «un día al mes en la oficina» → `hibrido`; «remoto, residencia en España» → `remoto`;
  «viajes ocasionales a clientes» → `hibrido` solo si son obligatorios y a una sede.
- **Origen (RT-08):** `origen_oferta` comprueba la línea de la modalidad como hoy hace con `remoto`.
- **Evals `ofertas`:** `modalidad` entra en los campos medidos y se añaden 4 casos: híbrida de un día al
  mes, remota con residencia obligatoria, presencial y sin dato.

## Filtro estricto (RF-7.1c)
- `buscar_ofertas`: con `solo_remoto`, la condición pasa a `modalidad = 'remoto'`. Se aplica también a las
  propias, igual que todos los filtros y el rango de nota (RF-7.1f): `recomendable` es lo único que no se les exige.
- `evaluar_condiciones`: `solo_remoto` se evalúa con `modalidad`; sin dato → «no cumple».

## Ofertas propias (RF-7.2)
- El worker añade `propia: True` al estado de `procesar_oferta` cuando la oferta tiene `usuaria_id`.
- `componer` no añade `sin_fecha` si `e.get("propia")`.
- Pantalla: si `propia` y no hay `fecha_publicacion`, Recomendadas y Añadir oferta dicen «No consta fecha
  de publicación» (se deja de usar `creada_en` como «Publicado»).

## Segunda persona (RF-7.3)
- El prompt del `matcher` añade una regla: explicación en segunda persona, sin el nombre de la usuaria.
- `evals.py`, set `recomendacion`: nueva comprobación de que la explicación no contiene el nombre del perfil
  del caso. Entra en la nota con el mismo umbral.

## Pantallas
- **Nombres (RF-7.4):** `nombrePais` pasa de `recomendadas.js` a `comun.js`, y se añade `nombreIdioma`
  (`Intl.DisplayNames` con `type: "language"`). «REMOTO» → «Remoto (cualquier país)». Se usan en las casillas
  de `grupoCasillas`, en Recomendadas, Candidaturas y Perfil.
- **Perfil (RF-7.5):** se reordenan las secciones de `perfil.html`. Pendientes y Estilo se pliegan con el
  componente plegable que ya existe en la guía (RF-6.4); si no encaja, se añade antes a la guía (RF-6.9).
  En `perfil.js`, `resumirEstilo(guia)` pinta la frase, los dos «máx. 5» y el detalle.
- **Ingesta (RF-7.6):** buscador y `select` en una fila de rejilla (`--tap`); se filtra en el navegador
  sobre la lista ya cargada, normalizando con `NFD` para ignorar tildes.
- **Admin (RF-7.7):** `arrancar()` añade la pestaña «Admin» → `/ingesta` si `yo.admin`. Ingesta y Costes
  llevan una fila de subpestañas «Ingesta · Costes». En la portada, `ir-ingesta` pasa a «Admin».

## Correcciones de la prueba manual (RF-7.1d, RF-7.5c-f, RF-7.8)
Sin rutas, tablas ni migraciones nuevas. El esquema `GuiaEstilo` no cambia (`max_length=200`), para que las
guías ya guardadas sigan validando al editarlas.

| Requisito | Dónde |
|---|---|
| RF-7.5f botón y guardado | reproducir en el navegador; según la causa, `perfil.js` (`cargarEstilo`, `editorGuia`) o `routers/estilo.py` |
| RF-7.5e rasgos cortos | `agents/analizador_estilo/prompt.md`; criterio de longitud en `evals.py`, set `estilo` |
| RF-7.5c párrafo | `perfil.js`: `resumirEstilo()` en tres `<p>`; se borra `rasgos()` si nada más lo usa |
| RF-7.5d desplegables | `perfil.js`: `seccion()` envuelve esas cuatro en `details.grupo` con `summary > .estado`; `cargarPerfil()` guarda y restaura las abiertas |
| RF-7.1d Condiciones | `preferencias.html`: cada casilla y su ayuda en `.casilla-con-ayuda`; `estilo.css`: esa clase y `p.ayuda` |
| RF-7.8 totales | `costes.js`: `tabla()` añade `<tfoot>` «Total»; `estilo.css`: `tfoot` con tokens |

- **Bug del botón (P9):** el botón solo se deshabilita con `analizando || !hay_documentos` (`perfil.js`), y en
  la base no se daba ninguna de las dos. La guía constaba con `origen = modelo`, así que el `PUT` no guardó.
  Causa (20-nov): no se reproduce con el servidor; el `PUT` y el botón van bien. Una edición hecha mientras el
  worker analizaba la pisaba al terminar (guardaba con `origen = modelo`). Ahora el `PUT` da 409 mientras hay un
  análisis sin terminar y la pantalla oculta «Editar guía» hasta que acaba.
- **Totales:** errores = Σ(tasa × llamadas) / Σ llamadas; latencia = Σ(latencia × llamadas) / Σ llamadas.

## Tests
- Migración: la columna existe con su `CHECK`.
- `buscar_ofertas`: con `solo_remoto`, el SQL exige `modalidad = 'remoto'`, y una propia sin modalidad pasa.
- `OfertaExtraida`: `remoto` se deriva de `modalidad`.
- `procesar_oferta` simulado: propia sin fecha → sin `sin_fecha`; de catálogo sin fecha → con `sin_fecha`.
- Prompt del `matcher`: contiene la regla de segunda persona; el comprobador de `evals.py` suspende «Lucía tiene…».
- Estáticos:
  - Perfil en el orden de P3 y con el texto de P4 literal;
  - Ingesta con buscador y las 5 opciones;
  - `PESTANAS` sin Admin fijo;
  - ninguna pantalla define su propio `nombrePais`.
- Navegador: 1280 y 390 px, claro y oscuro, cada pantalla tocada.

## Coste
- Evals reales de `ofertas` (extractor, 29 casos) y de `recomendacion` (`matcher`, 21 casos): una pasada
  de cada una. El coste se mide antes y se pide el OK de Mar (T12).
- Correcciones: una pasada real de `estilo` (8 casos) y un «Volver a analizar» de Mar; céntimos. Se mide
  antes y se pide el OK de Mar (T17).
- Nada más llama al modelo.
