---
type: spec
title: rediseno-2c — Spec funcional
description: Requisitos del rediseño visual «Editorial» (dirección 2c) de todas las pantallas de Horma, en notación EARS. Incluye la guía de tokens y componentes que deben seguir las pantallas nuevas, y las reglas de accesibilidad.
tags: [spec, frontend, diseno, accesibilidad, tokens, componentes]
status: active
sources: [./clarifications.md, ../system.md, ../constitution.md, ../002-perfil-recomendacion/spec.md, ../003-candidatura/spec.md, ../005-correcciones-profesor/spec.md]
generated: { by: claude-code, at: 2026-11-19 }
verified: { by: human, at: 2026-11-19 }
stale_after: null
---

# rediseno-2c — Especificación

## Contexto
Horma cambia de aspecto. Sale el marco Passe-Partout, provisional, y entra la dirección 2c
«Editorial» en todas las pantallas:
- fondo hueso y tinta negra;
- lima como único color de marca;
- todo recto, sin radios ni sombras;
- titulares grandes en Familjen Grotesk y etiquetas en DM Mono, en mayúsculas.

**No cambia lo que hace cada pantalla:** mismos datos, mismas acciones, mismas reglas (RF-5.2 sigue
vigente: sin «Condiciones»). Esta spec es además la **guía de diseño** que deben seguir las pantallas
que se creen después (RF-6.9).

Los requisitos transversales (RT-xx) están en [system.md](../system.md) y las respuestas del Clarify,
en [clarifications.md](./clarifications.md); aquí se citan como P1…P3.

## Requisitos (EARS)

### Tokens y temas (RF-6.1)
- **RF-6.1** Todos los valores de diseño (colores, fuentes, tamaños, grosores, espaciados) DEBERÁN
  vivir en **un único archivo de tokens**. Fuera de él NO DEBERÁ haber colores escritos a mano, ni
  radios distintos de 0, ni familias tipográficas (P3).
- **RF-6.1b** Paleta clara (por defecto):

  | Token | Valor | Uso |
  |---|---|---|
  | fondo | `#f6f6f2` | página |
  | superficie | `#ffffff` | campos, paneles desplegados |
  | superficie-2 | `#ecece6` | hover de secundarios, avatar |
  | tinta | `#0a0a0a` | texto, bordes fuertes, relleno de barra |
  | apagado | `#55554f` | texto secundario, etiquetas |
  | línea | `#cfcfc8` | separadores de filas |
  | acento | `#c8f031` | fondo de primarios y pestaña activa, marca |
  | sobre-acento | `#0a0a0a` | texto sobre lima |
  | texto-acento | `#0a0a0a` | enlaces-botón, foco (el lima no sirve como texto en claro) |
  | pista de barra | `#d9d9d2` | fondo de la barra de compatibilidad |
  | error | a fijar en el plan, ≥ 4,5:1 sobre el fondo | avisos de error |

- **RF-6.1c** Paleta oscura: fondo `#0a0a0a`, superficie `#161616`, superficie-2 `#1d1d1d`, tinta
  `#f6f6f2`, apagado `#a9a9a2`, línea `#2c2c2a`. En oscuro, el lima `#c8f031` SÍ DEBERÁ usarse
  como texto-acento, borde de primarios y relleno de barra.
- **RF-6.1d** El tema oscuro DEBERÁ aplicarse cuando el sistema lo prefiera. CUANDO la usuaria
  elija un tema con el botón de la cabecera, su elección DEBERÁ mandar sobre la del sistema y
  recordarse en ese navegador. SI el navegador no permite guardarla, la página DEBERÁ funcionar igual
  con el tema del sistema.

### Tipografía (RF-6.2)
- **RF-6.2** Titulares y texto en **Familjen Grotesk** (400-700). Etiquetas de campo, cabeceras de
  tabla y notas de compatibilidad en **DM Mono** (400-500).
- **RF-6.2b** Las fuentes DEBERÁN servirse desde la propia Horma, sin pedir nada a terceros (la CSP no
  se relaja). SI no cargan, DEBERÁ verse la fuente del sistema.
- **RF-6.2c** Escala tipográfica:

  | Elemento | Tamaño | Otros |
  |---|---|---|
  | texto base | 16 px | interlineado 1,4-1,5 |
  | h1 de pantalla | 76 px (móvil 56 px) | peso 600, tracking −0,035 em, interlineado 1,05 |
  | título de elemento de lista | 21 px | peso 600, tracking −0,035 em |
  | nota de compatibilidad | 28 px | DM Mono, peso 500 |
  | etiqueta (mono) | 11,5 px | DM Mono, mayúsculas, tracking 0,08 em, peso 600, apagado |
  | entradilla bajo el h1 | 17 px | apagado, máx. 62 caracteres de ancho |

### Cabecera y navegación (RF-6.3)
- **RF-6.3** Todas las pantallas con sesión DEBERÁN llevar la misma cabecera, generada en un solo
  sitio:
  - **Marca:** cuadrado lima de 22 px y «Horma» en 26 px, que enlaza a la portada.
  - **Navegación:** «Principal».
  - **A la derecha:** el nombre del perfil con su inicial en un círculo de 32 px, el botón de tema
    y «Salir».
  - SI el perfil no tiene nombre, no se muestran ni el nombre ni la inicial.
  - NUNCA DEBERÁ mostrarse una foto.
- **RF-6.3b** *(sustituido por la spec 008)* Las pestañas DEBERÁN ser las seis actuales (P2): Perfil · Preferencias · CV base ·
  Añadir oferta · Recomendadas · Candidaturas.
  - Cada una mide al menos 44 px de alto.
  - La activa lleva `aria-current="page"`, fondo lima, texto tinta y peso 700.
  - El resto va en apagado y pasa a tinta al pasar el ratón.
- **RF-6.3c** En móvil (< 900 px), la navegación DEBERÁ pasar a una **barra superior**, bajo la marca y fija al desplazarse (cambio pedido por Mar el 20-nov; antes era inferior):
  - una rejilla de 6 columnas sobre la superficie, con línea superior;
  - pestañas de al menos 48 px de alto y texto de 12 px, sin cortar palabras;
  - la activa, en lima.
- **RF-6.3d** *(sustituido por la spec 008)* Las pantallas de admin (`/ingesta`, `/costes`) DEBERÁN llevar la misma marca, tema y
  «Salir», sin las pestañas de usuaria. Mantienen sus enlaces entre ellas y a «Ofertas».
- **RF-6.3e** *(sustituido por la spec 008)* La portada sin sesión DEBERÁ mostrar la marca, un h1 editorial y el botón primario
  «Entrar con Google».

### Componentes (RF-6.4) — guía para cualquier pantalla
Cada pantalla DEBERÁ construirse con estos componentes. Una pantalla nueva NO DEBERÁ inventar otros
mientras uno de estos sirva (RF-6.9).

| Componente | Cómo es |
|---|---|
| **Título de pantalla** | h1 editorial (RF-6.2c) y entradilla en apagado |
| **Botón primario** | 44 px de alto mínimo, fondo lima, texto sobre-acento, borde de 1 px (tinta en claro, lima en oscuro), peso 700, sin radio; hover `brightness(1.05)`. Uno por bloque como mucho |
| **Botón secundario** | transparente, borde de 1 px en tinta, texto tinta; hover en superficie-2 |
| **Botón de texto** | subrayado con desplazamiento de 4 px, peso 600, 44 px de alto |
| **Campo** | 44 px de alto, superficie, borde de 1 px en tinta, sin radio; en móvil, texto de 16 px (para que iOS no haga zoom). La etiqueta va encima, en estilo mono |
| **Cuadro de texto** (añadido por la spec 011) | campo de varias líneas con el ancho de su columna: crece en alto con lo que se escribe (hasta el 70 % de la pantalla; después se desplaza por dentro), nunca en ancho, y solo se estira en vertical (`resize: vertical`, `contain: inline-size`). Mismo borde y fondo que el campo |
| **Casilla** | 22 px, con la fila entera clicable de 44 px; color de marca: tinta en claro y lima en oscuro |
| **Panel** | transparente, borde de 1 px en tinta, 20 px de relleno (16 px en móvil). Agrupa formularios y filtros |
| **Panel desplegado** | superficie y borde de 1 px en línea. Para guías y detalles |
| **Lista editorial** | filas sin caja, separadas por una línea inferior de 1 px y 26 px de relleno vertical. Sustituye a las tarjetas con sombra |
| **Fila desplegable** | toda la fila es clicable, con un chevrón de 44 px dibujado con bordes que lleva `aria-expanded` y `aria-controls`; el contenido desplegado va tras una línea superior |
| **Plegable** | `<details>`/`<summary>` o botón con `aria-expanded`, con el mismo chevrón |
| **Etiqueta de puesto** | 28 px de alto, borde de 1 px, fondo transparente, texto de 13 px y peso 600. El color sale del tono de la familia, con suficiente contraste. El texto siempre visible |
| **Barra de compatibilidad** | 6 px de alto, sin radio y sin línea de borde (la pista ya contrasta 3:1), pista y relleno según el tema; `role="meter"` con valor, mínimo y máximo. A su lado, la nota en DM Mono |
| **Ayuda «?»** | botón de 44 × 44 px con un círculo de 20 px; abre una ayuda propia con foco o clic (no basta con `title`) y lleva `aria-label` «Qué significa …» |
| **Explicación plegable** | la ayuda «?» junto al título de un bloque, con la explicación del bloque dentro (`montarExplicaciones()` en `comun.js`, sobre un párrafo marcado con `data-explicacion`). Sustituye a los párrafos explicativos sueltos (RF-10.14m) |
| **Aviso** | texto con `role="status"` (o `alert` si es un error), con el color de error y nunca solo con color: el texto dice qué pasó |
| **Tabla de datos** (admin) | cabeceras mono, filas con línea inferior, desplazamiento horizontal dentro de su caja en móvil |
| **Documento** (CV y carta) | hoja de superficie con borde de 1 px en línea, tipografía del cuerpo y anchura de lectura |
| **Ventana** (añadida por la spec 008) | `<dialog class="ventana">` modal de ancho de lectura (60 rem como máximo), borde de 1 px en tinta, cabecera con el título y «Cerrar» (secundario de 44 px), cuerpo con desplazamiento propio; con un documento (CV o carta), el documento ocupa todo el cuerpo (spec 011, T08o). Esc la cierra y el foco vuelve al botón que la abrió. Generaliza el visor de CV de Perfil |
| **Barra de avance** (añadida por la spec 008) | pista de 6 px sin radio ni borde con relleno según el tema, `role="progressbar"` con `aria-valuenow`, mínimo y máximo, y encima una frase en mono con el porcentaje («Puntuando ofertas · 40 %»). Entre pasos avanza sola según lo que suele tardar la tarea, rápida al principio y cada vez más despacio, hacia el 95 %; si el % no cambia en 3 s, el relleno late; al volver de otra pestaña cuenta el tiempo fuera (RF-10.8c, D-035). El color nunca es la única señal. Sin animación si se pide reducir el movimiento |
| **Aviso con dos acciones** (añadido por la spec 009) | fila con el texto a la izquierda y dos botones a la derecha, ambos de 44 px de alto (la acción que arregla y «Dar por visto»), separada por una línea inferior de 1 px. En móvil, el texto arriba y los botones debajo. Lleva el texto del aviso, nunca solo un color |
| **Aviso con elección de longitud** (añadido por la spec 009) | el aviso con dos acciones con el texto arriba y las dos opciones debajo, de igual ancho («Mantener la longitud» y «Que Horma lo sintetice») |
| **Indicador de avance** (añadido por la spec 010) | enlace en la cabecera, a la izquierda de «Tema» y «Salir», con la frase y el porcentaje en mono mayúsculas («Puntuando 40 %»), borde de 1 px, alto `--tap` y `role="status"`. Lleva a la pantalla de la tarea y desaparece al terminar. A 390 px cabe junto a la marca sin desplazar el menú. El texto es la señal: no depende del color |
| **Barra de rango** (añadida por la spec 011) | un solo control para un mínimo y un máximo: pista de 6 px sin borde, tramo elegido en el color de relleno, dos tiradores con zona táctil de 44 px y sus dos números en mono a los lados. El mínimo no pasa del máximo. Se maneja con el teclado (flechas) y cada tirador lleva su `aria-label`. Etiqueta encima, como un campo |
| **Botón de archivo** (añadido por la spec 011) | sigue la norma de los botones: primario si subir el archivo es la acción principal de la pantalla («Subir mi CV» en Ofertas, «Elegir archivos» en Perfil sin CV) y secundario si no («Subir archivos» en Perfil con CV) |

- **RF-6.4b** Simetría (prioridad alta de Mar): los elementos de una misma fila o rejilla DEBERÁN
  tener la misma altura, la misma separación y estar alineados por abajo. Una etiqueta o un contador
  NO DEBERÁN descolocar a sus vecinos. Los contadores y las marcas dentro de un control ocupan un
  tamaño fijo y se colocan siempre en el mismo sitio. Se comprueba a 1280 y 390 px antes de dar una
  pantalla por buena.

### Recomendadas (RF-6.5) — la pantalla con diseño cerrado
- **RF-6.5** Orden de la pantalla:
  1. h1 «Recomendadas» y entradilla: «Ofertas ya revisadas, sin fraudes ni ofertas fantasma, para
     tu perfil». Si hay titular, va detrás de dos puntos.
  2. Panel de filtros con los campos actuales (clarificaciones, «Supuestos»), en una rejilla de 4
     columnas, y «Buscar» como primario a la derecha.
  3. Contador «N ofertas» (con «· M sin puntuar» si las hay) con `aria-live`, el botón
     «Recomendar» y, a la derecha, el plegable «Cómo leer las recomendaciones».
  4. La lista.
- **RF-6.5b** En escritorio (≥ 900 px), la lista DEBERÁ ser una tabla con estas columnas:
  - Oferta · Puesto · Compatibilidad · Salario · Lugar · Publicado, más el chevrón.
  - Cada cabecera lleva su ayuda «?» con los textos actuales.
  - NO DEBERÁ aparecer «Condiciones» (RF-5.2). *(Ampliado por la spec 012, RF-12.25: una línea junto a la nota.)*
- **RF-6.5c** Celdas:
  - **Oferta:** título de 21 px, que enlaza a la oferta, y la empresa en apagado. Debajo, la
    atribución de la fuente, o «Añadida por ti» y el aviso del auditor si los hay. Sin logotipo.
  - **Puesto:** la etiqueta de la familia y el nivel.
  - **Compatibilidad:** la barra y la nota. Sin nota, «Sin puntuar» en cursiva y apagado.
  - **Salario:** el literal de la oferta, o «No publicado» en apagado (P17 de la fase 2).
  - **Lugar** y **Publicado:** este último, en apagado.
- **RF-6.5d** Al desplegar una fila DEBERÁ verse:
  - **A la izquierda**, en un máximo de 64 caracteres de ancho:
    - la etiqueta «Por qué te la recomendamos»;
    - la explicación en 17 px;
    - las citas del perfil y de la oferta;
    - los avisos de nota desfasada o de explicación retirada;
    - la corrección enviada, si la hay.
  - **A la derecha:**
    - «Corregir explicación» (secundario), que abre el formulario de corrección actual;
    - «Preparar candidatura» (primario), con sus casos actuales: «Preparar otra igualmente» y el
      enlace a «Generar CV base».
  - SI la oferta no tiene nota, solo DEBERÁ verse el texto que invita a pulsar «Recomendar».
  - Pueden quedar varias filas abiertas. La primera sale desplegada.
- **RF-6.5e** En móvil (< 900 px), cada oferta DEBERÁ verse como una tarjeta (`<article>`) sin caja,
  con una línea inferior. Contenido, en este orden:
  1. Título y empresa, con el chevrón a la derecha.
  2. La etiqueta de puesto y «Publicado …».
  3. La fila «Compatibilidad», con la barra y la nota.
  4. Salario.
  5. Lugar.
  6. Al desplegar: la explicación y, a todo el ancho, «Preparar candidatura» y luego «Corregir
     explicación», ambos de 48 px.

  Los filtros, salvo el primero, DEBERÁN plegarse bajo «Más filtros» / «Menos filtros» (con
  `aria-expanded`), en la misma fila que «Buscar».
- **RF-6.5f** *(sustituido por la spec 008)* Filtrar y ordenar NO DEBERÁN llamar al modelo (RF-2.15c). «Recomendar» sigue siendo un
  solo botón que puntúa lo pendiente (clarificaciones, «Supuestos»).

### Resto de pantallas (RF-6.6)
Mismo contenido y mismas acciones que hoy, con los componentes de RF-6.4:

| Pantalla | Cómo queda |
|---|---|
| Portada (`/`) | Sin sesión: RF-6.3e. Con sesión: h1 «Ofertas», catálogo como lista editorial con las etiquetas de auditoría como etiquetas con texto, y accesos como botones |
| Perfil | h1 «Perfil». CV subidos como lista editorial con sus acciones. Subir CV en un panel. Guía de estilo y preguntas pendientes como plegables. Secciones del perfil con etiquetas mono y la descripción con ejemplos (RF-5.1c). El visor de CV, en un diálogo con borde de 1 px |
| Preferencias | h1 «Preferencias». Grupos de casillas en paneles, con su contador; sueldo y orden como campos; «Guardar» como primario |
| CV base | h1 «CV base». Cada CV base como bloque con el documento (RF-6.4), el historial y las diferencias (añadido en tinta, quitado tachado y en apagado; nunca solo con color), la visibilidad de experiencias y «Regenerar» y «Copiar texto» como secundarios |
| Añadir oferta | h1 «Añadir oferta». Un panel con URL o texto y «Procesar» como primario. Las últimas añadidas como lista editorial |
| Candidaturas | h1 «Candidaturas». Tablero de 4 columnas con cabeceras mono y su contador, las candidaturas como filas con línea y «Cerradas» plegada; en móvil, las columnas se apilan |
| Candidatura | h1 con el puesto y la empresa debajo en apagado. «Revisa esto» en un panel. Documentos CV y carta (RF-6.4). «Detalles» plegado. «Aprobar y descargar» como único primario. Cambios de estado como secundarios. Historial como lista |
| Ingesta y Costes (admin) | RF-6.3d. Tablas de datos (RF-6.4), editor JSON como campo de texto mono, y estados con texto |
| Sin conexión | Marca, h1 «Sin conexión» y texto en apagado, solo con estilos precargados |

### Accesibilidad (RF-6.7)
- **RF-6.7** Todo texto DEBERÁ tener un contraste de al menos 4,5:1 (3:1 para el texto grande y los
  bordes de los controles), en claro y en oscuro.
- **RF-6.7b** Todo objetivo táctil DEBERÁ medir al menos 44 × 44 px, incluidas las ayudas «?» y los
  chevrones.
- **RF-6.7c** El foco DEBERÁ verse siempre: contorno de 3 px en texto-acento, separado 2 px.
- **RF-6.7d** El lima NUNCA DEBERÁ usarse como color de texto sobre un fondo claro.
- **RF-6.7e** El color NUNCA DEBERÁ ser la única señal: los puestos, las notas, los estados, las
  diferencias y los avisos siempre llevan texto.
- **RF-6.7f** CUANDO el sistema pida reducir el movimiento, los giros de chevrón y los despliegues
  NO DEBERÁN animarse.
- **RF-6.7g** Sin desplazamiento horizontal de la página a 390 px; solo dentro de las tablas de admin.

### Textos (RF-6.8)
- **RF-6.8** Ningún texto visible DEBERÁ decir «match», «ATS» ni «trazabilidad». En su lugar:
  «compatibilidad», «formato legible por los filtros de las empresas» y «de dónde sale».
- **RF-6.8b** Nunca se muestran la edad, una foto, la nacionalidad ni datos de salud (constitución).

### Pantallas nuevas (RF-6.9)
- **RF-6.9** Toda pantalla que se cree después DEBERÁ:
  - enlazar los tokens y la hoja común;
  - usar la cabecera común (RF-6.3);
  - construirse con los componentes de RF-6.4;
  - cumplir RF-6.7 y RF-6.8.

  SI necesita un componente nuevo, DEBERÁ añadirse primero a esta guía. `AGENTS.md` DEBERÁ recoger
  esta regla.

### PWA (RF-6.10)
- **RF-6.10** El color de tema y el fondo de la PWA (manifiesto y `theme-color`) DEBERÁN ser los de
  2c. Además, la página «Sin conexión» DEBERÁ verse con la paleta 2c sin red.

## Criterios de aceptación (puerta de salida)
- [x] Ninguna página lleva el marco Passe-Partout, y todas enlazan los tokens.
- [x] Un test comprueba que no hay colores hex fuera del archivo de tokens.
- [x] Ningún HTML lleva estilos ni scripts en línea, y la CSP no cambia.
- [x] Las 11 pantallas, vistas a 1280 px y 390 px, en claro y en oscuro:
  - [x] sin desplazamiento horizontal;
  - [x] cabecera común;
  - [x] menú superior en móvil.
- [x] Recomendadas:
  - [x] cumple RF-6.5 a RF-6.5f frente al diseño 2c;
  - [x] sin «Condiciones»;
  - [x] la primera fila sale desplegada;
  - [x] «Corregir explicación» y «Preparar candidatura» funcionan como antes.
- [x] Auditoría sin fallos (axe no pudo cargarse; se hizo con una auditoría propia en JS: contraste, 44 px, nombres y desborde) de contraste, nombre accesible ni tamaño de objetivo, en
      Recomendadas, Perfil y Candidatura, con los dos temas.
- [x] Revisión de usabilidad de las 11 pantallas hecha (T17b). Cada hallazgo está corregido o
      tiene la decisión de Mar.
- [x] El botón de tema cambia y recuerda el tema; sin almacenamiento, sigue al sistema.
- [x] Ningún texto visible con «match», «ATS» o «trazabilidad» (test).
- [x] Toda la batería de tests en verde. Los textos y los ids que fijaban los tests se conservan,
      salvo los cambios declarados aquí.
- [x] `AGENTS.md` recoge RF-6.9.

## Riesgos
- **Volumen:** son 11 pantallas y unas 2.800 líneas de HTML y JS. Cambiar el marcado puede romper
  comportamientos que los tests no cubren. Se mitiga trabajando por bloques y con una prueba en el
  navegador por pantalla.
- **Pantallas sin diseño cerrado:** salvo Recomendadas, el aspecto lo deduce Claude de la guía.
  Puede no coincidir con lo que Mar imagina. Mar revisa cada bloque en local antes del PR.
- **Contraste de las etiquetas de puesto:** los tonos de color deben dar 4,5:1 en los dos temas.
  Se comprueba con axe.
- **Barra superior de 6 pestañas a 390 px:** «Recomendadas» y «Candidaturas» casi no caben con
  12 px. Si no caben, se acortan las etiquetas solo en móvil y se pregunta antes a Mar.

## Fuera de alcance
- Cambiar funciones, datos o flujos de cualquier pantalla.
- Logotipo nuevo y aspecto de los PDF generados.
- Un framework de frontend o un paso de compilación del CSS.
