---
type: tasks
title: aplicacion-autonoma — Desglose de tareas
description: Tareas pequeñas y comprobables de la parte 1 de la spec 011 (paso 1 del PRD) — medición de destinos y mejoras pequeñas. Cada una empieza con un test que falla; las de pantalla se comprueban a 1280 y 390 px, en claro y en oscuro.
tags: [tareas, envio, medicion, frontend]
status: active
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-25 }
verified: { by: human, at: 2026-11-25 }
stale_after: null
---

# aplicacion-autonoma — Tareas (parte 1)

El estado está en [specs/index.md](../index.md); aquí solo van las casillas.

## Forma de trabajo
- **Ramas:** `envio-a` y `mejoras-m`, una por bloque y un PR cada una. Primero A.
- **Gasto:** 0 USD. Ninguna tarea llama al modelo ni envía nada.
- **Tests:** `UV_NO_SYNC=1 uv run pytest`.

### Spec
- [x] T01 — Spec, plan y tareas de la parte 1, firmados por Mar (25-nov).

### A · Medición de destinos (RF-11.1)
- [x] T02 — `portales.json` y `resolver_destino`.
  - **Test:** direcciones de ejemplo de cada portal dan su canal; LinkedIn e Indeed dan «no
    automático»; InfoJobs y WTTJ dan su canal; una redirección se sigue; ninguna petición es distinta de `GET`.
- [x] T03 — Medición en consola y en Admin.
  - **Test:** con un catálogo de fixtures, la tabla cuenta bien portal, ofertas y «exige cuenta»; sin sesión
    de admin, la API responde 403.
  - **Navegador:** Admin a 1280 y 390 px, claro y oscuro.
- [x] T04 — Cierre de A. 🛑 Mar lee la medición del catálogo real y se anota en la hoja de ruta como decisión; PR. D-028; PR #44 fusionado, 25-nov.

### M · Mejoras pequeñas (RF-11.25 a 11.30)
- [x] T05 — El aviso «Hemos quitado un dato personal» se ve.
  - **Test:** un CV con un dato que Horma no guarda devuelve el aviso en la API y la pantalla lo pinta.
- [x] T06 — Calificar una fuente que responde 403 da «no apta» con motivo.
  - **Test:** con un 403 simulado, la calificación termina sin error y guarda el motivo.
- [x] T07 — Botones de archivo con una sola norma, resaltado simétrico en «Añadir oferta» y barras sin borde.
  - **Navegador:** Ofertas, Perfil y la ventana «Añadir oferta» a 1280 y 390 px, claro y oscuro.
- [x] T08 — Barra de rango de compatibilidad, primero en la guía.
  - **Test:** el mínimo no pasa del máximo; el filtro da las mismas ofertas que las dos casillas; se maneja
    con el teclado.
  - **Navegador:** 1280 y 390 px, claro y oscuro.
- [x] T08b — Tras borrar un CV, la barra dice «Actualizando tu perfil con los CV que quedan», no «Estamos leyendo tu CV».
  Rehacer el perfil con los CV que quedan es correcto (RF-10.14); el fallo era solo el texto.
  - **Test:** `tests/test_s11_borrar_cv_texto_barra.py`.
- [x] T08c — La barra no retrocede al cambiar de pestaña y volver (RF-10.8c): se guarda en `sessionStorage` el último
  valor mostrado de cada tarea (Perfil y «Analizando la oferta»).
  - **Test:** `tests/test_s11_barra_avance_persistente.py` (ejecuta `barraAvance` en node).
- [x] T08d — «Añadir oferta» en dos pestañas («Por URL» y «Por texto»), un solo botón «Añadir oferta» a la
  vista; desaparece «Leer oferta» (prueba de Mar: confundía con el verde de abajo).
  - **Test:** `tests/test_s11_anadir_oferta_dos_pestanas.py`. **Navegador:** 1280 px comprobado; 390 px y oscuro, pendientes.
- [x] T08e — Si la URL no se puede leer, el aviso sale en «Por texto» («Estamos teniendo problemas para leer esa dirección…»);
  al volver a Ofertas se retoma la oferta ya analizada que aún no está en la lista (la barra y la oferta no desaparecen).
  - **Test:** `tests/test_s11_anadir_oferta_retomar_y_url.py`.
- [x] T08f — La lectura de una oferta por URL se retoma al volver a Ofertas: el id se guarda en `sessionStorage` y, al recargar, vuelve la barra «Analizando la oferta»
  (con su valor guardado) y se sigue hasta que la oferta aparece o avisa si falla (antes no había barra y la oferta salía mucho después, sin seguimiento).
  - **Test:** `tests/test_s11_retomar_lectura_url.py`.
- [x] T08g — La barra de avance nunca parece parada (RF-10.8c; prueba de Mar del 25-nov: en Perfil, tras subir un CV y volver de otra pestaña, se quedaba quieta). Causa: entre pasos avanzaba un 2 % del hueco que le quedaba hasta 20 puntos por delante del paso real; si el paso tardaba (la tarea 512 estuvo 71 s en 0 %) se pegaba al tope sin llegar y el % dejaba de cambiar, y al volver se retomaba ya junto al tope (igual en la lectura por URL retomada de T08f). Ahora avanza un punto cada 3 s y, en el tope, el relleno late hasta el siguiente paso (ritmo revisado en T08s).
  - **Test:** `tests/test_s11_barra_nunca_parada.py` (ejecuta `barraAvance` en node).
- [x] T08h — El aviso «Hemos quitado un dato personal» sale al subir un CV con fecha de nacimiento, nacionalidad o estado civil (M12b). Causa: solo salía si el modelo devolvía el dato y el código lo quitaba; el modelo ya no lo extrae (su prompt se lo prohíbe), así que no salía nunca. Ahora también se mira el texto de los CV.
  - **Test:** `tests/test_f2_t08_t10_flujos.py`.
- [x] T08i — Los cuadros de texto crecen solo en alto y nunca pasan del ancho de su columna (M15: descripción de experiencia, «Por texto» de «Añadir oferta» y corregir oferta). Causa: `field-sizing: content` ensanchaba el cuadro con una palabra larga sin espacios. Regla común en `estilo.css` y en la guía (spec 006, «Cuadro de texto»).
  - **Test:** `tests/test_p1_t07_t08_mejoras_pantalla.py`. **Navegador:** 1280 px comprobado (claro y oscuro); 390 px, comprobado por Mar (25-nov).
- [x] T08j — Al cerrar «Añadir oferta» con una lectura por URL en marcha, la barra «Analizando la oferta» pasa a la página, bajo los filtros (M16: se quedaba dentro de la ventana cerrada y no se veía ninguna). La ventana es modal: para ir a otra pantalla hay que cerrarla antes.
  - **Test:** `tests/test_s11_retomar_lectura_url.py`.
- [x] T08k — Una URL ya añadida no se vuelve a leer ni analizar: «Ya añadiste esta oferta el …» con «Ver oferta» y «Leer de nuevo», que relee y actualiza la misma oferta (RF-11.29, D-030; antes la misma URL de lifeworq creó las ofertas 200, 203 y 205, cada una pagada).
  - **Test:** `tests/test_s11_url_repetida.py` (URL canónica, API y worker con BD), `tests/test_s11_url_repetida_cliente.py` (pantalla, en node). **Navegador:** 1280 px comprobado (claro y oscuro); 390 px, comprobado por Mar (25-nov).
- [x] T08l — Una sola barra «Analizando la oferta» de la lectura de la página al análisis, sin cambiar de frase ni bajar (RF-11.30, D-031; antes pasaba a «Analizando la oferta añadida» y bajaba, p. ej. de 15 % a 4 %).
  - **Test:** `tests/test_s11_una_sola_barra.py` (en node); `tests/test_s11_retomar_lectura_url.py` ajustado. **Navegador:** 1280 px comprobado; 390 px, comprobado por Mar (25-nov).
- [x] T08m — Al rehacer el perfil, lo que escribió la usuaria pasa el filtro de datos personales y, si se quita algo, sale el aviso (RF-11.25c, D-032; un «casada con hijos» escrito antes de T05 pasaba de versión en versión).
  - **Test:** `tests/test_f2_t08_t10_flujos.py`. Las versiones antiguas del perfil de prueba (Irene, 38 a 55) y su `origen` se limpiaron a mano el 25-nov, tras la prueba M12c.
- [x] T08n — Borrar las ofertas caducadas del catálogo ya no falla si tienen notas de compatibilidad (RF-5.5d, spec 005; el cierre de la ingesta se deshacía por `matches_oferta_id_fkey`). Causa: un DELETE exige también ver las filas y el sistema no veía `matches` ni `candidaturas`. Migración 0030: política SELECT solo para las notas de caducadas del catálogo y función `oferta_con_candidatura` (la candidatura sigue frenando el borrado).
  - **Test:** `tests/test_f5_t30_fuentes_nuevas.py` (con BD: borra oferta y nota, vigente intacta; el sistema solo ve las notas de caducadas; con candidatura no se borra).
- [x] T08o — «Ver» un CV o una carta en Perfil → Documentos subidos enseña el documento a toda la ventana (tercera prueba de Mar, 25-nov: solo se veía una franja y había que desplazarse dentro). Causa comprobada en Chrome: `.ventana-cuerpo` es una rejilla con `align-content: start` y el iframe `.visor-marco` (`height: 100%`) se queda en 150 px. Ahora, con un documento, su fila ocupa todo el cuerpo (guía, spec 006, «Ventana»).
  - **Test:** `tests/test_s11_visor_documento.py`. **Navegador:** comprobado en claro y oscuro (marco de 150 a 510 px de alto); la ventana de Chrome no baja de 1536 px, pero a 1280 el visor mide lo mismo (60 rem). Mar: 1280 y 390 px, claro y oscuro (25-nov).
- [x] T08p — «Mostrar» en Ofertas tiene la opción «Añadidas por mí (N)»: las que la usuaria añadió por URL o por texto, con candidatura o sin ella, menos las descartadas (mejora pedida por Mar; RF-11.31, D-033).
  - **Test:** `tests/test_s11_mostrar_anadidas_por_mi.py` (en node). **Navegador:** comprobado en claro y oscuro con las ofertas de Irene («Añadidas por mí (18)», con las 5 de candidatura). Mar: 1280 y 390 px, claro y oscuro (25-nov).
- [x] T08q — «Ordenar por: Más recientes» ordena por la llegada a Horma y pone arriba la última oferta añadida (prueba de Mar: la añadida por URL quedaba abajo; RF-11.32, D-034). Causa: ordenaba por `fecha_publicacion`, que en las añadidas es texto de la web («25/11/2026», «hace 23 horas»); `new Date` no lo entendía, valía 0 y la oferta caía al final.
  - **Test:** `tests/test_s11_orden_mas_recientes.py` (en node). **Navegador:** comprobado con las ofertas de Irene: las añadidas el 25-nov salen primero (207, 206, 205…) y las del catálogo detrás, por lote. Mar: 1280 y 390 px, claro y oscuro (25-nov).
- [x] T08r — Tras «Ya añadiste esta oferta…», al volver a abrir «Añadir oferta» → «Por URL» el campo está vacío y sin el aviso (RF-11.29). Causa: al abrir solo se quitaba «Ya añadiste…»; la dirección se quedaba y, al pulsar otra vez «Añadir oferta», el aviso volvía. Con una lectura en marcha se queda la dirección que se lee.
  - **Test:** `tests/test_s11_anadir_url_vacia_al_reabrir.py` (en node). **Navegador:** comprobado en claro y oscuro con la URL de lifeworq ya añadida (sin lectura ni gasto). Mar: 1280 y 390 px, claro y oscuro (25-nov).
- [x] T08s — La barra de avance avanza según lo que suele tardar cada tarea y cuenta el tiempo que la usuaria pasó en otra pestaña (M17, tercera prueba de Mar: «subida muy lenta» y, al volver de otra pestaña, parecía congelada; RF-10.8c revisado, D-035). Causa comprobada en node: un punto cada 3 s dejaba un CV (37 s de mediana, con el servidor en 0 % casi todo el rato) en ~14 % antes de saltar a 100 %; y al volver se retomaba el valor con el que se fue (10 s dentro y 20 fuera: 5 % al irse y 5 % al volver, frente a 12 % sin irse). Ahora se acerca al 95 % con la duración típica de cada tarea (`DURACION_TIPICA_S` en `comun.js`; a esa duración va por el 60 %) y guarda la hora con el valor.
  - **Test:** `tests/test_s11_barra_ritmo_tiempo_fuera.py` (en node, con reloj de mentira); `tests/test_s11_barra_nunca_parada.py` adaptado a la regla nueva. **Navegador:** simulada en Perfil, sin gasto, en claro y oscuro: 24 % a los 10 s; al irse a Candidaturas con 35 % y volver 22 s después, 62 % (antes, 35 %). Mar: M17 con un CV real, 1280 y 390 px, claro y oscuro (25-nov).
- [x] T09 — Cierre de M. 🛑 Prueba manual de Mar; `specs/index.md` al día; PR. Tercera prueba (25-nov): M12a a M18 funcionan; «a trompicones» era solo M17 (la barra parecía congelada al volver de otra pestaña: T08s) y salen T08o a T08s. Cuarta prueba (25-nov): M17 y M19 a M22 bien, a 1280 y 390 px, en claro y oscuro. PR #44 fusionado, 25-nov.
