---
type: plan
title: rediseno-2c — Plan técnico
description: Archivos, tokens, componentes CSS y cambios de tests que cubren cada requisito del rediseño 2c, sin tocar la API, los agentes ni la CSP.
tags: [plan, frontend, diseno, tokens, css, accesibilidad]
status: active
sources: [./spec.md, ./clarifications.md, ../system.md]
generated: { by: claude-code, at: 2026-11-19 }
verified: { by: human, at: 2026-11-19 }
stale_after: null
---

# rediseno-2c — Plan

## Arquitectura
Solo cambia `horma/web/static/` y los tests de pantallas. Quedan igual:
- la API, los routers, los servicios y los agentes;
- la CSP de `horma/web/main.py`, porque `default-src 'self'` ya cubre las fuentes propias.

```
horma/web/static/
  tokens.css        (nuevo) única fuente de valores: :root claro, oscuro por @media y [data-theme], @font-face
  estilo.css        (reescrito) componentes de RF-6.4; sin colores ni familias propias, solo var(--…)
  tema.js           (nuevo) aplica el tema guardado antes de pintar y gestiona el botón (try/catch)
  comun.js          cabecera común (marca, pestañas, persona, tema, Salir) y helpers de componentes
  fuentes/          (nuevo) familjen-grotesk-latin-wght.woff2, dm-mono-latin-400.woff2, dm-mono-latin-500.woff2, OFL.txt
  *.html            sin <div class="pp">; enlazan tokens.css → estilo.css; tema.js en <head>
  recomendadas.js   tabla 2c, fila desplegable, tarjetas móviles, ayuda «?»
  resto de *.js     solo cambian clases y estructura de nodos; misma lógica y mismas llamadas a la API
  manifest.webmanifest, sw.js, offline.html   colores 2c y precarga de tokens y fuentes
```

## Tokens (RF-6.1, RF-6.2)
- **Nombres en `tokens.css`:** los del diseño, para que la guía y el código hablen igual.
  - Color: `--bg`, `--surface`, `--surface-2`, `--ink`, `--muted`, `--line`, `--line-strong`, `--accent`, `--on-accent`, `--accent-text`, `--btn-border`, `--bar-track`, `--bar-fill`, `--tab-active-bg`, `--tab-active-fg`, `--panel-border`, `--error`.
  - Tipografía: `--f-head`, `--f-body`, `--f-mono`, `--fs`, `--fs-title`, `--fs-h1`, `--fs-h1-m`, `--fs-num`, `--fs-label`, `--ls-head`, `--ls-label`, `--fw-head`, `--fw-num`.
  - Medidas: `--radius: 0`, `--bw`, `--pad-page`, `--pad-page-m`, `--row-py`, `--col-gap`, `--bar-h`, `--tap: 44px`, `--focus`.
  - Etiquetas de puesto: `--tag-l` y `--tag-c`.
- **Error:** `#a3201a` en claro (contraste de unos 6:1 sobre `#f6f6f2`) y `#ff8f87` en oscuro (unos 8:1 sobre `#0a0a0a`). Se confirma con axe en T17.
- **Oscuro:** se escribe dos veces, en `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }` y en `:root[data-theme="dark"]`, como ya hace hoy `estilo.css`. No hay preprocesado.
- **Etiquetas de puesto:**
  - El color sale de `oklch(var(--tag-l) var(--tag-c) var(--tono))`.
  - `--tono` lo pone una clase `.tono-0…5` que asigna `comun.js` según la familia, con un mapeo fijo; hoy son los `--etq-0..5`. Tonos: 45, 160, 255, 320, 100 y 10.
  - Los navegadores sin `oklch` reciben `color: var(--ink)`.
- **Fuentes:** woff2 del subconjunto latino, sacadas de los paquetes `@fontsource-variable/familjen-grotesk` y `@fontsource/dm-mono` (licencia OFL, `OFL.txt` junto a ellos). `font-display: swap` y la pila de sistema como respaldo (RF-6.2b).

## Cabecera común y tema (RF-6.3, RF-6.1d)
- **El HTML** de cada pantalla con sesión deja `<header id="cabecera" class="cabecera"></header>` y
  `<nav id="pestanas" aria-label="Principal"></nav>`. Se conserva `id="pestanas"` porque lo piden los
  tests. Sale el `<h1>Horma</h1>` del logo: el h1 pasa a ser el título de la pantalla.
- **`arrancar(activa)`** de `comun.js`:
  - pinta la marca, las pestañas (las `PESTANAS` actuales), la persona, el botón de tema y «Salir»;
  - saca el nombre de `GET /api/perfil` (`perfil.nombre`). Sin nombre, no pinta nada. El
    `/api/yo` no cambia;
  - sigue devolviendo `yo` y fijando `csrf`.
- **Móvil (< 900 px):** el `nav` pasa a `position: fixed; bottom: 0` en una rejilla de 6 columnas, y
  `body` reserva su alto con `padding-bottom`. Si a 390 px no caben las etiquetas, se avisa (riesgo
  de la spec).
- **`tema.js`** se carga sin `defer` en `<head>`:
  - lee `localStorage["horma-tema"]` dentro de try/catch y pone `data-theme` en `<html>` antes de
    pintar, para que no parpadee;
  - expone `alternarTema()`, que usa el botón de la cabecera. El botón lleva `aria-pressed` y una
    etiqueta clara («Tema oscuro» / «Tema claro»).
- **Admin** (`ingesta.js`, `costes.js`) y **portada** (`app.js`) no usan `comun.js`. Llevan una cabecera
  mínima en su HTML (marca, tema y Salir) y `tema.js`. Así no se mezclan sus helpers con los de
  `comun.js`.

## Componentes CSS (RF-6.4)
- **Clases nuevas en `estilo.css`**, una por componente de la guía:
  - Títulos y textos: `.titulo-pantalla` + `.entradilla`, `.etiqueta-mono`.
  - Botones: `button` / `.boton` (primario por defecto), `.secundario`, `.boton-texto`.
  - Contenedores: `.panel`, `.panel-desplegado`.
  - Listas: `.lista-editorial` y `.fila-desplegable` + `.chevron` (girado con `[aria-expanded="true"]`).
  - Datos: `.etiqueta-puesto.tono-N`, `.barra-compat` (con `role="meter"` desde el JS), `.ayuda` + `.ayuda-globo`.
  - Avisos y documentos: `.aviso` / `.error`, `.tabla-datos`, `.cv-hoja`.
- **Se reutilizan los nombres de clase actuales cuando encajan** para reducir el cambio en el JS:
  `.secundario`, `.suave` (alias de `--muted`), `.lista`, `.fila`, `.tablero`, `.cv-hoja`,
  `.linea-anadida`, `.linea-quitada`, `.tabla-costes`, `.solo-lector`, `.estado`.
  Salen `.pp`, `.tarjeta` con sombra y los radios.
- **Cortes:**
  - un solo corte principal a `900px` (tabla ↔ tarjetas, barra inferior);
  - se mantiene el `@media (max-width: 760px)` que contiene `.tablero`, porque lo exige el test de
    candidaturas;
  - `prefers-reduced-motion` apaga transiciones y giros.
- **Foco:** `:focus-visible { outline: var(--focus); outline-offset: 2px }` para todo lo interactivo.

## Recomendadas (RF-6.5)
- **HTML:**
  - h1 y entradilla;
  - `<form id="filtros" role="search">` como `.panel`, con los mismos ids (`grupos`, `solo-remoto`, `solo-salario`, `sueldo-minimo`, `rango-min`, `rango-max`, `orden`, `buscar`) y el botón `#mas-filtros`, que solo se ve en móvil;
  - barra con `#contador` (`aria-live="polite"`) y `#recomendar`;
  - `<details class="leer">` con «Cómo leer las recomendaciones», que el test exige;
  - `<table id="tabla" class="tabla-ofertas">`.
- **`recomendadas.js`:**
  - **Columnas:** `COLUMNAS`/`AYUDA` sin «Candidatura» (pasa a la fila desplegada) y sin
    «Condiciones».
  - **Filas:** cada oferta da un `<tr class="fila-oferta">` con sus celdas `data-etiqueta` más un
    `<tr class="fila-detalle" id="detalle-N" hidden>` con `colspan`. El clic en la fila o en el
    chevrón alterna `hidden` y `aria-expanded`. Los clics en enlaces y botones de dentro no la
    pliegan (`stopPropagation`). La primera se abre al pintar.
  - **Barra:** sustituye `<progress>` por `<div class="barra-compat" role="meter" aria-valuenow …>`
    con un relleno de ancho proporcional. El ancho se pone con `el.style.width` desde JS, que la
    CSP permite porque no es un atributo `style=` en el HTML.
  - **«Por qué»:** la explicación, las citas, los avisos y la corrección pasan del `<details>` de la
    celda al detalle de la fila, tras «Por qué te la recomendamos». El botón «Modificar» pasa a
    llamarse «Corregir explicación» y abre el mismo formulario (`/correccion`).
    `celdaCandidatura` pasa a `accionesCandidatura`, con la misma lógica de 409.
  - **Ayuda «?»:** botón con `aria-expanded` y `aria-describedby` que muestra un `.ayuda-globo`. Se
    cierra con Esc, con un clic fuera o al perder el foco.
- **Móvil:** el mismo DOM. Con CSS, cada `tr` pasa a bloque y la tabla a `<article>` visual (ya se
  hace hoy con `td::before{content: attr(data-etiqueta)}`). No se duplica el marcado. Las celdas se
  reordenan con `order` en flex/grid. El `<details>` de filtros de grupos y `#mas-filtros` pliegan
  los filtros, salvo el primero.

## Resto de pantallas (RF-6.6)
- **Patrón por pantalla:**
  1. HTML: sin `.pp`, con la cabecera común, h1 `.titulo-pantalla` y secciones en `.panel` o `.lista-editorial`.
  2. JS: solo cambian `className` y el orden de nodos.
- **Se conservan** los ids y los textos que fijan los tests:
  - `perfil.html`: `id="visor"`, `estilo`, `escrito-por-ella` y `value="carta"`, y las frases de RF-5.1d.
  - `anadir-oferta.html`: `id="url"`, `formulario` y «Apify».
  - `candidatura.js`: «Revisa esto», `function detalles`, `function cabecera` y `// --- botones`.
  - `candidaturas.js`: «Cerradas» y `"details"`.
  - `costes.html`: 3 `div.tabla-costes` y su regla `overflow-x: auto; max-width: 100%`.

## PWA (RF-6.10)
- **Manifiesto:** `theme_color` y `background_color` pasan a `#f6f6f2`.
- **`<meta name="theme-color">`:** dos, una con `media="(prefers-color-scheme: light)"` (`#f6f6f2`) y otra con `dark` (`#0a0a0a`).
- **`sw.js`:** sube la versión de la caché y precarga `tokens.css`, `estilo.css`, `tema.js` y las 3 fuentes.
- **Iconos:** se mantienen; el cambio de logotipo queda fuera de alcance.

## Tests (TDD: primero fallan)
- **Cambian** (marcados en la spec como «cambio declarado»):
  - `test_f2_t20_t21_pantallas.py` y `test_f3_t18_t20_pantallas.py`: `class="pp"` pasa a
    `/static/tokens.css`.
  - En Recomendadas, `"Modificar"` pasa a `"Corregir explicación"`.
  - El corte `@media (max-width: Npx)` con `.tabla-ofertas` sigue; acepta 900.
  - `test_t12_t15_web.py`: `index.html` admite también `/static/tema.js`.
  - `test_f4_t15_t16_pwa_cabeceras.py`: el `theme-color` nuevo y la precarga de `tokens.css`.
- **Nuevos** (`tests/test_f6_rediseno.py`):
  - Ningún `#hex`, `rgb(` ni `font-family` con nombre fuera de `tokens.css`. Solo valen `var(--…)`.
  - Ningún `border-radius` distinto de 0 o `var(--radius)`.
  - Toda página `*.html`, salvo `offline`, enlaza `tokens.css` antes que `estilo.css` y carga `tema.js`.
  - Ningún HTML ni JS contiene «match», «ATS» o «trazabilidad» en un texto visible (cadenas de
    `nodo(…)` y nodos de texto del HTML).
  - Las fuentes existen en `/static/fuentes/` y `tokens.css` las declara con `@font-face`.
  - En `recomendadas.js`: `role` `meter`, `aria-expanded`, `aria-controls`, «Por qué te la
    recomendamos», «Corregir explicación» y la ausencia de «Condiciones» (se mantiene).
  - En `comun.js`: `aria-label` «Principal», `aria-current` y la ausencia de foto (`<img` y
    `"img"` en la cabecera).

## Requisito → componente
| Requisito | Dónde |
|---|---|
| RF-6.1, 6.2 | `tokens.css`, `fuentes/` |
| RF-6.1d | `tema.js`, botón en `comun.js` / cabeceras mínimas |
| RF-6.3 | `comun.js` (`arrancar`), HTML de cada pantalla, `estilo.css` (barra inferior) |
| RF-6.4 | `estilo.css` |
| RF-6.5 | `recomendadas.html` / `recomendadas.js` |
| RF-6.6 | resto de `*.html` / `*.js` |
| RF-6.7, 6.8 | `estilo.css`, `tests/test_f6_rediseno.py`, auditoría axe |
| RF-6.9 | `AGENTS.md` |
| RF-6.10 | `manifest.webmanifest`, `sw.js`, `offline.html` |

## Decisiones del plan (revisables)
- **Un solo DOM para escritorio y móvil:** la tabla pasa a tarjetas solo con CSS. Se evita duplicar
  el marcado y la lógica.
- **Nombres de tokens en inglés, como el diseño;** las clases siguen en español, como en el resto
  del proyecto.
- **Sin paso de compilación:** el tema oscuro se escribe dos veces en `tokens.css`, como ya se hace.

## Riesgos
- **Reescribir `estilo.css` entero** rompe a la vez todas las pantallas que aún no se han
  repasado. Por eso los bloques B a E van en la misma rama, y el PR se abre cuando todas están
  repasadas.
- **`oklch`** no existe en navegadores antiguos: hay un respaldo en tinta.
