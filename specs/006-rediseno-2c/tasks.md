---
type: tasks
title: rediseno-2c — Desglose de tareas
description: Tareas pequeñas y comprobables del rediseño 2c. Cada una empieza con un test que falla y se comprueba en el navegador a 1280 y 390 px, en claro y en oscuro.
tags: [tareas, frontend, diseno, tokens, accesibilidad]
status: active
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-19 }
verified: { by: human, at: 2026-11-19 }
stale_after: null
---

# rediseno-2c — Tareas

## Orden y forma de trabajo
1. spec (A, T01), con Opus y el OK de Mar;
2. base común (B, T02-T06);
3. Recomendadas (C, T07-T10);
4. resto de pantallas de usuaria (D, T11-T15);
5. admin (E, T16);
6. cierre (F, T17, T17b, T18 y T19).

- **Modelo:** la construcción (B-F) se hace con Sonnet; Mar cambia de modelo antes de empezar B.
- **Rama:** B a E van en una sola, porque `estilo.css` nuevo afecta a todas las pantallas a la vez.
  El PR se abre al terminar E.
- **Sin gasto:** nada llama al modelo ni a servicios de pago.
- **Prueba de cada tarea:** su test y un vistazo en Chrome a 1280 y 390 px, en claro y en oscuro.

### Bloque A · Spec
- [x] T01 — Spec 006 escrita y aprobada. *(firmada por Mar el 19-nov)*
  - **Qué se hace:** `clarifications.md`, `spec.md`, `plan.md` y `tasks.md`; entrada en `specs/index.md`.
  - **Test:** Mar lee la spec y la firma (`verified`).
  - **Cubre:** todo.

### Bloque B · Base común (RF-6.1-6.4, RF-6.10)
- [x] T02 — Tokens y fuentes.
  - **Qué se hace:**
    - `tokens.css` con la paleta clara y la oscura (por `@media` y por `[data-theme]`);
    - la escala tipográfica y `@font-face`;
    - las fuentes woff2 con `OFL.txt` en `static/fuentes/`.
  - **Test:** `tokens.css` declara las dos familias, y los archivos existen y se sirven. El
    oscuro define los mismos tokens que el claro.
  - **Cubre:** RF-6.1-6.1c, RF-6.2-6.2c.
- [x] T03 — `estilo.css` reescrito con los componentes.
  - **Qué se hace:**
    - los componentes de RF-6.4 con las clases del plan;
    - foco visible, cortes a 900 px y `prefers-reduced-motion`;
    - fuera `.pp`, los radios y las sombras.
  - **Test:** sin hex, `rgb(` ni familias fuera de `tokens.css`; sin `border-radius` distinto de 0;
    `:focus-visible` con `var(--focus)`.
  - **Cubre:** RF-6.4, RF-6.7c, RF-6.7f.
- [x] T04 — Cabecera común y tema.
  - **Qué se hace:**
    - `arrancar()` pinta la marca, las 6 pestañas (`aria-label="Principal"`), el nombre con su
      inicial (de `/api/perfil`), el botón de tema y «Salir»;
    - `tema.js` en `<head>`;
    - cabecera mínima en la portada, Ingesta y Costes;
    - en todos los HTML: sin `.pp`, con `tokens.css` antes de `estilo.css` y `tema.js`.
  - **Test:**
    - toda página, salvo offline, enlaza `tokens.css` y `tema.js`;
    - ninguna lleva `class="pp"`;
    - en `comun.js`, «Principal», `aria-current` y nada de `img`;
    - `index.html` admite `tema.js`.
    Se actualizan los tests de las fases 2 y 3 que pedían `pp`.
  - **Cubre:** RF-6.1d, RF-6.3-6.3d.
- [x] T05 — PWA.
  - **Qué se hace:**
    - en el manifiesto, `theme_color` y `background_color` 2c;
    - dos `<meta theme-color>` en cada HTML;
    - `sw.js` con la caché nueva, que precarga los tokens, `tema.js` y las fuentes;
    - `offline.html` con el estilo 2c.
  - **Test:** el test de la PWA, con los valores nuevos; «Sin conexión» se mantiene.
  - **Cubre:** RF-6.10.
- [x] T06 — Guardas de textos.
  - **Qué se hace:** un test que busca «match», «ATS» y «trazabilidad» en los textos visibles de los
    HTML y JS, y corrige lo que encuentre.
  - **Test:** el propio test, que tiene que pasar en verde.
  - **Cubre:** RF-6.8.

### Bloque C · Recomendadas (RF-6.5)
- [x] T07 — Estructura y filtros.
  - **Qué se hace:**
    - h1 y entradilla;
    - panel `role="search"` con los mismos ids, en una rejilla de 4 columnas, y «Buscar» como primario;
    - contador con `aria-live` y «Recomendar»;
    - «Cómo leer…» como plegable `<details>`.
  - **Test:** los asserts actuales (`contador`, `filtros`, `details` y valores de `orden`), además
    de `role="search"` y `aria-live`.
  - **Cubre:** RF-6.5, RF-6.5f.
- [x] T08 — Tabla de escritorio.
  - **Qué se hace:**
    - las columnas Oferta · Puesto · Compatibilidad · Salario · Lugar · Publicado, más el chevrón;
    - las celdas de RF-6.5c, con la barra `role="meter"`;
    - «Sin puntuar» y «No publicado».
  - **Test:** las columnas y su `AYUDA`; `meter`, `aria-valuenow`; no aparece «Condiciones» ni
    `cond-`; no queda `<progress>`.
  - **Cubre:** RF-6.5b, RF-6.5c.
- [x] T09 — Fila desplegable con acciones.
  - **Qué se hace:**
    - la fila de detalle con «Por qué te la recomendamos», la explicación, las citas y los avisos;
    - «Corregir explicación» (el formulario actual) y «Preparar candidatura» (con los casos 409);
    - la primera fila, abierta;
    - los clics internos no pliegan la fila.
  - **Test:** `aria-expanded`, `aria-controls`, «Corregir explicación», `/correccion`, «Preparar
    candidatura» y «Preparar otra igualmente». Se actualiza el assert de «Modificar».
  - **Cubre:** RF-6.5d.
- [x] T10 — Móvil y ayudas «?».
  - **Qué se hace:**
    - de 900 px para abajo, las tarjetas `<article>` visuales con el orden de RF-6.5e;
    - «Más filtros» / «Menos filtros»;
    - la ayuda «?» como globo propio (foco, clic, Esc).
  - **Test:**
    - `@media (max-width: 900px)` con `.tabla-ofertas` y `attr(data-`;
    - `#mas-filtros` con `aria-expanded`;
    - el botón «?» con `aria-label` «Qué significa …» y sin depender de `title`.
  - **Cubre:** RF-6.5e, RF-6.7b.

### Bloque D · Resto de pantallas (RF-6.6)
- [x] T11 — Portada.
  - **Qué se hace:**
    - sin sesión: marca, h1 y «Entrar con Google» como primario;
    - con sesión: h1 «Ofertas», el catálogo como lista editorial y las etiquetas de auditoría con texto.
  - **Test:** los asserts actuales de la portada (sin `textarea`, solo scripts externos y «Añadida por ti»).
  - **Cubre:** RF-6.3e, RF-6.6.
- [x] T12 — Perfil.
  - **Qué se hace:** CV subidos como lista editorial, la subida en un panel, guía y preguntas
    plegables, secciones con etiquetas mono y visor en un diálogo con borde.
  - **Test:** los asserts actuales de perfil (`visor`, `estilo`, `escrito-por-ella`, las frases de RF-5.1d).
  - **Cubre:** RF-6.6.
- [x] T13 — Preferencias y Añadir oferta.
  - **Qué se hace:**
    - en Preferencias, los grupos en paneles y «Guardar» como primario;
    - en Añadir oferta, URL o texto en un panel y la lista de las últimas añadidas.
  - **Test:** los asserts actuales (`sueldo-minimo`, `type="number"`, `url`, `formulario`, `textarea` y «Apify»).
  - **Cubre:** RF-6.6.
- [x] T14 — CV base.
  - **Qué se hace:**
    - el documento con la hoja 2c;
    - historial y diferencias, con lo añadido en tinta y lo quitado tachado;
    - la visibilidad por experiencia;
    - las acciones como secundarios.
  - **Test:** los asserts actuales de `cv-base.js` y `.linea-anadida`, `.linea-quitada` y `line-through`.
  - **Cubre:** RF-6.6, RF-6.7e.
- [x] T15 — Candidaturas y Candidatura.
  - **Qué se hace:**
    - el tablero con cabeceras mono, que se apila en móvil, y «Cerradas» plegada;
    - en el detalle, «Revisa esto» en un panel, los documentos, «Detalles» plegado y «Aprobar y
      descargar» como único primario.
  - **Test:** los asserts actuales de la fase 3 (`.tablero` dentro de `@media (max-width: 760px)` y
    los textos literales).
  - **Cubre:** RF-6.6.

### Bloque E · Admin (RF-6.3d, RF-6.6)
- [x] T16 — Ingesta y Costes.
  - **Qué se hace:** la cabecera mínima, tablas de datos, el editor JSON en mono y estados con texto.
  - **Test:** los asserts actuales (`ingesta.js`, 3 `tabla-costes` con `overflow-x: auto` y `viewport`).
  - **Cubre:** RF-6.3d, RF-6.6.

### Bloque F · Cierre
- [x] T17 — Accesibilidad. *(20-nov: 11 pantallas en claro y oscuro con auditoría propia en JS, porque axe no pudo cargarse; corregidos «Cerradas» y «Verla en Recomendadas»; 390 px pendiente de la vista de Mar en F12)*
  - **Qué se hace:** axe o Lighthouse en Recomendadas, Perfil y Candidatura, con los dos temas, a 390
    y 1280 px; se corrige lo que salga, como el contraste de los tonos de puesto o los 44 px. También
    se recorren las 11 pantallas sin desplazamiento horizontal.
  - **Test:** el informe, sin fallos de contraste, nombre ni tamaño de objetivo.
  - **Cubre:** RF-6.7-6.7g.
- [x] T17b — Revisión de usabilidad (añadida a petición de Mar el 19-nov). *(20-nov: todos los hallazgos corregidos o decididos por Mar; 3 con enmienda de RF-5.3e (P19), 5 se queda)*
  - **Qué se hace:** Claude recorre las 11 pantallas ya rediseñadas, en móvil y en escritorio, con
    los criterios estándar de usabilidad:
    - claridad de lo que se puede hacer;
    - carga de trabajo y pasos de más;
    - mensajes de error y de estado;
    - coherencia entre pantallas;
    - recorrido completo de una candidatura en móvil.

    Los hallazgos van a un informe gitignorado, `docs/revision-ux-006.md`, con su gravedad y su
    arreglo. Lo que encaje en esta spec (aspecto, textos de ayuda, orden) se corrige. Lo que cambie
    funciones o flujos se propone a Mar y, con su OK, va a una spec nueva.
  - **Test:** el informe existe, cada hallazgo está corregido o tiene la decisión de Mar, y los tests
    siguen en verde.
  - **Cubre:** criterios de aceptación (apoyo a T19).
- [x] T18 — Documentación. *(20-nov; falta solo la bitácora del Workbook, fuera del repo)*
  - **Qué se hace:**
    - la regla RF-6.9 en `AGENTS.md`;
    - en las specs 002 (RF-2.15, RF-2.15b) y 003 (P5), la nota «aspecto sustituido por 006»;
    - `README` e `index.md` al día;
    - la bitácora del Workbook, fuera del repo.
  - **Test:** `AGENTS.md` cita `tokens.css` y la spec 006; el índice lista la 006 con su estado real.
  - **Cubre:** RF-6.9.
- [x] T19 — Prueba manual de Mar. *(firmada por Mar el 20-nov)*
  - **Qué se hace:** un plan corto, gitignorado, en `docs/plan-pruebas-006.md`. Mar recorre las
    pantallas en local y firma.
  - **Test:** la firma de Mar.
  - **Cubre:** criterios de aceptación.
