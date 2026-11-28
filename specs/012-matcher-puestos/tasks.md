---
type: tasks
title: matcher-puestos — Desglose de tareas
description: Tareas pequeñas y comprobables de la spec 012 (paso 2 del PRD), en tres bloques — puestos, nota y explicación, y lo que ve la usuaria. Cada una empieza con un test que falla; cada gasto real, con estimación y OK de Mar.
tags: [tareas, matcher, puestos, recomendacion]
status: active
sources: [./plan.md]
generated: { at: 2026-11-25 }
verified: { by: human, at: 2026-11-25 }
stale_after: null
---

# matcher-puestos — Tareas

El estado está en [specs/index.md](../index.md); aquí solo van las casillas.

## Forma de trabajo
- **Ramas:** `matcher-p`, `matcher-n` y `matcher-v`, un PR cada una y en ese orden.
- **Gasto:** solo en las tareas con 🛑 de gasto. Estimación antes y OK de Mar ([plan](./plan.md), Costes).
- **Tests:** `$env:UV_NO_SYNC=1; $env:PRESUPUESTO_DIARIO_USD='1.0'; uv run pytest`.

### Spec
- [x] T01 — Aclaraciones, spec, plan y tareas, firmados por Mar (25-nov).

### P · Puestos (RF-12.1 a 12.10)
- [x] T02 — Set `puestos`: 12 CV difíciles nuevos y el harness con sus métricas, en simulado.
  - **Test:** con respuestas simuladas, cada métrica da lo esperado; un puesto «ajeno» marcado hace fallar el set.
- [x] T03 — 🛑 OK al gasto (~0,1 USD). Pasada real del `clasificador_postulante` actual; respuestas guardadas (26-nov: 40 llamadas, 0,05 USD).
- [x] T04 — Etiquetado ciego (tres etiquetadores) e imprescindibles. 🛑 Mar repasa lo que no tiene unanimidad
  (26-nov: 296 puestos, kappa 0,77, 53 repasados; D-037).
- [x] T05 — Puerta por niveles, tope de nivel y genéricos con familia, medidos sobre las respuestas de T03 (0 USD)
  (26-nov: ajenos marcados 0, no marcados 0,98, marcados 0,79, cobertura 0,795, equidad 0; D-038).
  - **Test:** «Controller financiero» citando «Excel» queda fuera; el puesto entero de una experiencia da nivel 1;
    una titulación da nivel 2; «Senior …» no sale para un perfil junior; «Manager» no casa con una oferta de
    otra familia y sí con una sin familia.
- [x] T06 — `relacion` en el clasificador. 🛑 OK al gasto (~0,4-0,7 USD): segunda pasada del set y eval `perfil`
  (26-nov: 0,44 USD; `perfil` aprobado al 100 %; ajenos 0, marcados 0,98, no marcados 0,99, cobertura 0,94,
  equidad 0; 126 puestos nuevos por etiquetar).
- [x] T22 — Léxico y `en_genero` (`tools/lexico_genero.py`). 🛑 Mar repasa el léxico (0 USD; aprobado el 26-nov, D-050).
  - **Test:** la tabla de ejemplos de D-043, incluida «Costurera» sin cambio; ida y vuelta
    `en_genero(a_copia(x), género de x) == x`; sin género, «Camarero/a».
- [x] T23 — `PerfilCiego` y `copia_ciega()` (RF-12.30a y b).
  - **Test:** el esquema tiene exactamente los campos de la lista; al menos 10 gemelas escritas a mano (las del
    set y 5 con secretaria, asistenta, gobernanta y modista) dan el mismo `model_dump_json`; el nombre en una
    descripción, el correo, la URL y el teléfono desaparecen; las fechas y el perfil original no cambian.
- [x] T24 — El clasificador con la copia, puerta y huella de clasificación (RF-12.30f a h). Ejemplos del prompt en «/a».
  - **Test:** el proveedor simulado no recibe el nombre ni «Camarera»; un `dato` «Camarero/a» da nivel 1 y se
    guarda «Camarera»; con género femenino se ve «Camarera» y sin género «Camarero/a»; cambiar el nombre o
    `genero_puestos` no cambia `huella_clasificacion` y añadir una certificación sí; cambiar `genero_puestos`
    reescribe los títulos sin llamar al modelo.
- [x] T25 — Pares irregulares en `variantes_genero` y `canonico` (RF-12.30i).
  - **Test:** «Gobernanta» casa con «Gobernante/a de pisos»; «Actor» con «Actriz»;
    `canonico("Asistenta") != canonico("Asistente")`.
- T26 — Retirada (D-048): los modelos de Horma no admiten `temperature`.
- [x] T27 — Métricas de equidad (sobre las copias) y estabilidad (`--veces 3`).
  - **Test:** una gemela con una palabra fuera del léxico hace fallar la equidad; tres pasadas simuladas
    distintas bajan la estabilidad.
  - 🛑 OK al gasto (~0,5-0,8 USD): 3 pasadas reales del set `puestos` y eval `perfil`.
  - 🛑 Mar fija el umbral de estabilidad (26-nov: 0,50 USD, estabilidad 0,52, `perfil` aprobado; D-052: sin
    umbral y sus puestos, por código). Etiquetados los puestos nuevos (26-nov: 261, kappa 0,75, 53 repasados)
    y el set aprueba: ajenos 0, marcados 0,99, no marcados 1,0, cobertura 0,93, equidad 1,0.
- [x] T07 — Set de títulos de 9a: ~50 pares de sinónimos. 🛑 Mar firma los pares dudosos. Se vuelve a medir
  RF-9.3e; SI la cobertura baja de 0,90, 🛑 se para y se propone la prueba de embeddings (F4-D6). Hecho (26-nov):
  0,58 con texto; se midieron tres vías y entran tabla y modelo (D-053, D-061).
  Set de 202 pares: cumple RF-9.3e; en 80 pares nuevos, cobertura 0,68 y precisión 1,0.
- [x] T07b — Las otras formas que da el modelo (RF-12.4c): agente pequeño, guardadas con las preferencias y pedidas
  en el worker al clasificar y al guardar un puesto escrito a mano. Con T08: «También busco: …» bajo cada puesto
  marcado, sin editar.
  - **Test:** guardar «Peluquera» pide sus formas una vez y la búsqueda las usa; la API las enseña.
- [x] T08 — «Qué buscas»: nivel 1 marcado, nivel 2 sin marcar con su porqué y junior sin experiencia (RF-12.7).
  - **Test:** la API devuelve nivel y porqué; un CV sin experiencia trae marcados los de titulación.
  - **Navegador:** 1280 y 390 px, claro y oscuro (`tests/capturas.js`, 27-nov). El porqué de cada puesto, D-063.
- [x] T09 — Cierre de P: set `puestos` en umbral, suite verde, `specs/index.md` al día y PR. Hecho (27-nov): set en
  umbral y en la CI con las respuestas grabadas (D-064), suite verde; PR #46 fusionado.

### N · Nota y explicación (RF-12.11 a 12.24, 12.31 y 12.32; y RF-12.4e)
- [x] T10 — Eval `recomendacion` a ~60 casos, con orden y pares de equidad (0 USD). 🛑 Mar repasa los casos con más
  de 10 puntos entre etiquetadores y cualquier cambio de una nota esperada existente (RF-12.14).
  Hecho (27-nov): 60 casos (6 de orden y 6 pares de equidad); 6 ofertas repasadas (D-069); ninguna nota anterior cambia.
- [x] T11 — Harness: `--veces 3`, variación por caso, `orden`, `equidad`, `citas` y el revisor, en simulado.
  - **Test:** un par invertido hace fallar `orden`; dos notas de un par a más de 3 puntos hacen fallar `equidad`;
    el revisor simulado detecta una explicación sembrada que no se apoya en su cita.
  Hecho (27-nov, 0 USD): `verificar_citas`, agente `revisor-explicacion` solo del eval, control sembrado en
  `evals/recomendacion/revisor.json`; los casos de orden miden solo el orden (D-070).
- [x] T12 — Prompt del `matcher` (franjas, sin nombrar instrucciones, citas literales) y `verificar_citas` con un
  reintento.
  - **Test:** una cita inventada se pide una vez más; si vuelve a fallar, la explicación se retira y la nota se
    conserva; una tanda con una oferta sin resultado la deja «sin puntuar».
- [x] T13 — `convertir_cv` ignora el texto invisible.
  - **Test:** un PDF y un DOCX con una instrucción en blanco o de tamaño 0 no la devuelven en el texto.
  Hecho (27-nov): en PDF se dibuja cada página con `pypdfium2` (ya instalado), en vez de leer colores con `pypdf`.
- [x] T14 — 🛑 OK al gasto (~2,4-3 USD, D-077). Una ejecución real entera, con las 3 pasadas de RF-12.12; después, solo los casos que fallan
  (🛑 OK a cada tanda, ~0,1-0,3 USD), hasta que el `matcher` llegue. (D-113) Ya no hay tandas parciales: se cierra con
  tres pasadas nuevas o como «medida» (T14t y T14u).
  **Cerrada como «medida» (28-nov, D-113 y D-115).** Las tres pasadas nuevas llegan a los umbrales (nota 0,907 ·
  0,926 · 0,926; orden 6 de 6; revisor 0,988 · 0,988 · 1,0), pero Mar ve un grave entre los rechazos confirmados
  (47): la puerta no pasa. Gasto total de T14: 8,32 USD (el cierre, con T14m, 3,04 de 3,1).
  Primera ejecución (27-nov, 1,87 USD): **no llega**. Nota 0,63 (pide 0,90), orden 0,50 (100 %), citas 0,88 y
  revisor 0,10 (100 %; su control, 1,0); condiciones, rasgos, segunda persona y equidad, en 1,0. Decidido
  cómo corregir tras investigarlo (D-080 a D-086; T14a a T14h).
  Revisor repetido con D-078 sobre las mismas respuestas (27-nov, 0,11 USD): 11 de 234 sin apoyo; peor pasada,
  0,90 (pide 100 %); control, 1,0.
  D-079 (27-nov, 0,21 USD): el `matcher` no cuenta un título como experiencia y el revisor no exige lo
  discriminatorio ni confunde el nivel. Revisor sobre las mismas respuestas: 12 de 234 sin apoyo (06, 14 y 48 ya
  no fallan); control, 1,0. `matcher` repetido en 07 y 47: ya no cuenta el título, pero 07 baja a 55-58 (espera
  93) y 47 afirma cosas que no constan. **Sigue sin llegar.**
  **Corrección (D-080 a D-086; F4, apartado 11).** En este orden. Tope de gasto: 3,9 USD; cada gasto, con OK de Mar.
- [x] T14a — Etiquetas: notas de D-082 a D-084 con su D-NNN en el `motivo`; motivos de 01, 03, 05, 08, 12, 16 y 20
  sin condiciones, con la misma nota (RF-12.14, 0 USD).
  - **Test:** ningún `motivo` nombra sueldo, contrato, remoto ni ciudad; los ocho esperados nuevos.
  - Volver a puntuar las salidas grabadas de T14: nota ~0,76-0,80 y orden 0,50. SI da otra cosa, se para.
- [x] Corrección (27-nov, 0 USD): las habilidades y las certificaciones no se podían citar (el verificador excluía
  toda clave `nombre`, no solo la de la persona; RF-12.19). Test: `tests/test_s12_t12_matcher_citas.py`.
- [x] T14b — Guardar en la traza del eval las citas que fallan; nada en la base (RF-12.19, 0 USD).
  - **Test:** una explicación retirada por sus citas deja las dos citas de cada intento.
- [x] T14c — Marcas y relación en la salida y el prompt del `matcher`; la frase de franja, en código (RF-12.34,
  12.18 y 12.21; D-080; 0 USD, simulado).
  - **Test:** una salida sin la marca de un requisito se rechaza; un rasgo personal o una condición sale «no aplica».
- [x] T14d — `acotar_nota`, función pura (RF-12.35; D-080, D-081 y D-085; 0 USD).
  - **Test:** uno por regla; «no aplica» no cambia la nota; dos gemelas dan la misma.
- [x] T14e — Aviso «Pide menos de lo que tienes», primero en la guía; revisar la landing (RF-12.36, 12.28 y 12.29;
  D-081; 0 USD).
  - **Test:** oferta de nivel inferior y mismo puesto o afín enseña el aviso; la nota no cambia.
  - **Navegador:** 1280 y 390 px, claro y oscuro.
  Hecho (0 USD): la migración 0033 de `matches` se adelanta desde T14h (D-090). Sin veredicto todavía (T18), la
  línea va bajo la barra de compatibilidad. Comprobado en las capturas `ofertas-aviso`; la landing no cambia.
- [x] T14f — 🛑 OK al gasto (~0,35, tope 0,45 USD). Los 21 casos que fallan y los 6 de orden, una pasada; se graban
  nota del modelo, marcas y citas fallidas.
  - **Seguir** con ≥ 17 de 21 dentro de ±10 y 6 de 6 en orden. SI falla el código, se ajustan suelos y topes sobre
    lo grabado (0 USD); SI el marcado falla en más de 4 casos, se corrigen las definiciones del prompt y **una**
    tanda más; las citas, según lo que muestren.
  Primera tanda (27-nov, 0,36 USD): 16 de 21 y 3 de 6 en orden; citas, sin fallos. Corregidas cuatro reglas y las
  definiciones del prompt (D-091; sobre lo grabado, 19 y 4).
  Segunda tanda (27-nov, 0,37 USD): 18 de 21 y 5 de 6; con D-092 sobre lo grabado, 18 y 6. Se sigue.
  Antes de T14g, las ofertas sin requisitos solo suben a 80 con el mismo puesto (D-093, 0 USD).
- [ ] T14g — 🛑 OK al gasto (~2,3-2,8, tope 3,0 USD). 60 casos, 3 pasadas y revisor, con las respuestas grabadas
  (RF-12.12, 12.13, 12.19, 12.21 y 12.22). SI pasa todo, T14 y T15 hechas (D-086). SI no, no se toca más el prompt:
  se simula a 0 USD la nota entera por código y se traen a Mar los casos que queden.
  Medida el 27-nov (2,36 USD): **no llega**. Nota 0,85-0,87 (pide 0,90), orden 0,67-1,0 (100 %), citas 0,97 y
  revisor 0,92-0,97 (100 %); equidad, rasgos, condiciones y segunda persona, 1,0. Las citas que fallaban eran un
  fallo del verificador (corregido). Simulado: la nota entera por código queda peor (44-45 de 54; orden 5 de 6) y
  ajustando solo valores el techo es 48 de 54. **Decidido cómo cerrar (D-098 a D-100; F4, apartado 12):** T14i a T14n,
  en este orden. Tope de gasto: 2,6 USD. No se repite una tanda solo con los casos que fallan.
- [x] T14i — Revisor (D-098; RF-12.21; 0 USD): el eval guarda el `motivo` de cada juicio; cada rechazo se juzga dos
  veces más y cuenta si lo confirman 2 de 3; la métrica `revisor` es, por pasada, la parte de explicaciones sin
  rechazo confirmado (umbral 0,95) y el resultado lista los confirmados para Mar.
  - **Test:** un rechazo que confirma uno de los dos juicios nuevos suspende; uno que no confirma ninguno, no; los
    tres motivos quedan en la salida.
- [x] T14j — Etiquetas (D-099; RF-12.14; 0 USD): 10, 25 → 15 y 03, 35 → 20, con D-099 en el `motivo`.
  - **Test:** las dos notas nuevas y su D-099.
- [x] T14k — `acotar_nota`: tope 10 → 15 y fuera el 95 de D-092 (D-100; RF-12.35; 0 USD). `horma eval repuntuar`
  vuelve a puntuar lo grabado (RF-12.12) y se vuelve a puntuar T14g.
  - **Test:** las reglas con los valores nuevos; volver a puntuar lo grabado con el código de hoy da las mismas notas
    y junta dos ejecuciones como tres pasadas.
  - SI T14g no da nota 0,907 · 0,926 · 0,926 y orden 4 · 4 · 4 (de 6), se para.
  Hecho (28-nov, 0 USD): T14g vuelto a puntuar da justo eso; su revisor, con un solo juicio, 0,939.
- T14l — Prompt del `matcher`, un solo cambio (D-100; RF-12.34; 0 USD, simulado): las marcas no siguen la regla
  de «no consta»; «N años» con las fechas; «desde 2019» solo si el puesto sigue, si no «de 2015 a 2025»; no contar
  los requisitos.
  - **Test:** el prompt pide las cuatro cosas y ya no pide «desde 2019» sin más.
  Retirada tras T14m (D-100): el prompt vuelve al de T14g, y su test con él. Vuelve en T14s (D-113).
- [x] T14m — 🛑 Pasada 1 (~0,79-0,81 USD; tope de la ejecución 0,90, para que los juicios extra no la corten; el
  total sigue en 2,6): 60 casos, una vez, con revisor. SI pasa todo, T14n sin parar; SI no,
  se para, se vuelve al prompt de T14g y se trae el resultado a Mar.
  Medida el 28-nov (0,76 USD): **no llega**. Nota 0,889 (48 de 54; pide 0,90) y orden 4 de 6 (100 %); citas 1,0;
  revisor 0,988 (1 confirmado, sin dato inventado); equidad, rasgos, condiciones y segunda persona, 1,0. Fallan
  14, 15, 20, 32, 37 y 41 en la nota y 45 y 46 en el orden. El prompt arregla las marcas literales («3 años», SQL)
  pero 41 sube a 50 (espera 30) y 37 sale «afín» sin requisitos (60; espera 85). Sobre lo grabado, ninguna
  variante de reglas pasa de 0,889 (0 USD). Prompt de T14g repuesto. Investigado y decidido (D-108 a D-113; F4,
  13.7): el rechazo del 58 es grave (D-112) y esta pasada no vale para la puerta. **Cierre (D-109 a D-113):** T14o a
  T14u, en este orden y en una sola ronda. Tope de gasto: 3,1 USD (quedan 2,34).
- T14n — Retirada (D-112, D-113): la pasada 1 de T14m no vale; van tres pasadas nuevas (T14t y T14u).
- [x] T14o — Orden con margen de 10 (D-109; RF-12.13; 0 USD): «la mejor, primera» solo frente a las que esperan más
  de 10 puntos menos; los pares con 20 o más de diferencia, igual.
  - **Test:** 95 frente a 92 puede salir al revés; 95 frente a 84, no; un par a 20 puntos invertido sigue fallando.
  Hecho (28-nov, 0 USD): `tests/test_s12_t14o_orden.py`.
- [x] T14p — Etiqueta (D-110; RF-12.14; 0 USD): 45-recepcionista, 35 → 15, con D-110 en el `motivo`.
  - **Test:** la nota nueva y su D-110.
  Hecho (28-nov, 0 USD).
- [x] T14q — `acotar_nota` (D-111; RF-12.35; 0 USD): los topes 15 y 20 solo si ningún exigido sale «sí»; con alguno,
  30. Volver a puntuar T14g y la pasada 1 de T14m con `horma eval repuntuar`.
  - **Test:** con mayoría de «no» y algún «sí», tope 30; sin ningún «sí», 15 y 20 como antes.
  - SI no da nota 0,926 · 0,944 · 0,944 · 0,907 y orden 6 de 6 en las cuatro pasadas, se para.
  Hecho (28-nov, 0 USD): da justo eso (indicio, no prueba: medido sobre los mismos casos).
- [x] T14r — Revisor (D-112; RF-12.21; 0 USD): rechaza atribuir a un puesto tareas que su descripción no recoge.
  - **Test:** el prompt lo pide; el 58 de la pasada 1 queda como ejemplo en el control (`revisor.json`), no apoyado.
  Hecho (28-nov, 0 USD): el control pasa de 9 a 10 explicaciones.
- [x] T14s — Prompt del `matcher` (D-100 y D-113; RF-12.34; 0 USD, simulado): el cambio de D-100 tal como está en
  `encargos.md` (T14m) y, en la explicación, «Las tareas de un puesto se citan solo con ese puesto: no las juntes con
  otro». Recupera T14l.
  - **Test:** el prompt pide las cinco cosas y ya no pide «desde 2019» sin más.
  Hecho (28-nov, 0 USD; sin medir: lo mide T14t). Suite verde: 1.975 tests y 2 saltados.
- [x] T14t — 🛑 Pasada 1 nueva (~0,76 USD; tope de la ejecución 0,90): 60 casos, una vez, con revisor. SI pasa todo,
  se traen a Mar los rechazos confirmados y, si no ve graves, T14u. SI no pasa, regla de parada.
  Medida el 28-nov (0,755 USD): **pasa**. Nota 0,907 (49 de 54; fallan 14, 15, 20, 29 y 37), orden 6 de 6, citas
  1,0, revisor 0,988 (1 confirmado de 84) y control del revisor 1,0; equidad, rasgos, condiciones y segunda
  persona, 1,0. El confirmado (04: «un puesto que incluye trato diario con clientes», sin descripción) no es grave
  para Mar: es lo que RF-12.34 da por cubierto, no un dato inventado. El tope diario del `.env` no limita el eval
  (solo la web): se deja en 1.0, con el OK de Mar.
- [x] T14u — Pasadas 2 y 3 sin tocar nada (~1,52 USD) y unión de las tres con `horma eval repuntuar`. SI las tres
  pasan, T14 y T15 hechas (D-086). SI no, regla de parada.
  Medida el 28-nov (1,522 USD; tope de la ejecución 1,58): las dos pasan. Nota 0,926 y 0,926 (fallan 14, 20, 29, 37
  y 40; el 29 varía 30 puntos), orden 6 de 6, citas 1,0 y revisor 0,988 y 1,0; equidad, rasgos, condiciones y
  segunda persona, 1,0. La unión de las tres con `repuntuar` aprueba. Un confirmado nuevo (47, oferta 2: «la oferta
  pide experiencia … de cuidado de personas mayores», que solo está en su título) **es grave para Mar (D-115)**:
  se aplica la regla de parada.
  - **Regla de parada (D-113):** si una pasada no llega, no se gasta más. T14 se cierra como «medida», con las cifras
    de cada pasada aquí, y T15 no se da por hecha. Se quedan T14o a T14s; no hay más cambios de reglas, prompt ni
    etiquetas sobre estos 60 casos, ni tandas parciales, ni otro encargo. El examen pasa a ser la revisión de Mar
    de 20 recomendaciones reales, a ciegas (T21), y se sigue con T16 y el bloque V.
- [x] T14h — «Qué buscas» quita la franja de otro oficio, recalculando desde lo guardado en T14e; pruebas de Mar en
  el plan de pruebas (RF-12.37; D-085; 0 USD). Va tras T14g.
  - **Test:** marcar «Teleoperador/a» quita la franja a las ofertas que casan y desmarcarlo la devuelve; sin llamar
    al modelo y con la misma huella.
  Probado por Mar (lote 1, 28-nov): B9 y B10 pasan.
  Hecho (27-nov, 0 USD): `relacion_que_cuenta` y `recalcular_notas`; se recalcula al guardar «Qué buscas», al llegar
  los sinónimos y al cambiar los puestos desde el CV o una oferta añadida. Pruebas de Mar, B9 y B10 del plan.
- [ ] T15 — 🛑 OK al gasto (~2,4-3 USD). Puerta: 3 ejecuciones seguidas con el modelo mayor. Valen las tres pasadas
  de T14t y T14u si pasan todos los umbrales (D-086, D-113); si T14 se cierra como «medida», T15 no se da por hecha.
  No se da por hecha (28-nov, D-115): T14 se cerró como «medida». El examen pasa a ser la revisión a ciegas (T21).
- [x] T16 — 🛑 OK al gasto (~0,15-0,3 USD). 3 ejecuciones con el modelo pequeño. 🛑 Mar decide F1-E6 (D-NNN).
  Medida el 28-nov (0,305 USD; el tope de 0,30 la cortó en 56 de 60 casos, sin los pares 57 a 60): **no pasa**.
  Nota 0,72 · 0,78 · 0,76, orden 1,0 · 0,83 · 0,83, adversarias 0,50, condiciones 0,95, rasgos, segunda persona y
  citas 0,96, revisor 0,987 · 1,0 · 1,0 y equidad 1,0; variación máxima, 65 puntos (43). En 06 y 25 devuelve
  `matches` como texto y la salida se rechaza. **D-117:** el `matcher` sigue con el modelo mayor y F1-E6 queda abierta
  para volver a probarlo más adelante.
- [x] T28 — Con T12 y antes de T14: el `matcher` con la copia y sin condiciones (RF-12.31), RF-12.32 en el prompt y
  `huella_compatibilidad` sobre la copia, con una migración que reescriba las huellas guardadas (sin ella se
  vuelve a puntuar todo).
  - **Test:** el proveedor simulado no recibe el nombre, «Camarera» ni las condiciones; cambiar el nombre no
    cambia la huella; la migración conserva las notas.
  Hecho (27-nov, 0 USD) junto con T12 y T29: migración 0032.
- [x] T29 — Con T12: citas contra la copia.
  - **Test:** «encargado/a de turno» existe en la copia y se enseña «encargada de turno»; una cita con el nombre
    de la usuaria no existe y se pide otra vez.
- [x] T30 — Con T11: pares de RF-12.22 solo para edad, hueco y nacionalidad.
  - **Test:** dos medianas a más de 3 puntos hacen fallar la equidad.
  Hecho (27-nov, 0 USD): seis parejas (T10), métrica `equidad` al 100 % en `umbrales.json`.
- [x] T31 — Set de evals de `sinonimos-puestos` (RF-12.4e, D-068), con su harness en simulado. 🛑 Mar fija el umbral.
  🛑 OK al gasto antes de medir con el modelo real; entra en la CI sin gasto.
  - **Test:** una forma que sea otro puesto hace fallar el set.
  Hecho (27-nov, 0,022 USD): la primera pasada dio 22 formas ajenas; prompt corregido (D-075) y umbral de reserva
  (D-076): 3 de 213 ajenas (0,014) y cobertura 0,60. En la CI con las respuestas grabadas.
- [x] T17 — `recomendacion` de vuelta en `evals-reales`. Cierre de N: suite verde, `specs/index.md` al día y PR.
  Con T14 «medida» la puerta no ha pasado: `recomendacion` no vuelve a `evals-reales` (RF-12.15).
  Hecho (28-nov): suite verde (1.975 tests y 2 saltados), PR #47 abierto y su CI en verde, tras un commit de estilo
  (ruff); a la espera de fusionar.

### V · Lo que ve la usuaria (RF-12.25 a 12.29)
- [x] T18 — Veredicto en palabras y línea de condiciones, con el orden de empate. Primero en la guía.
  - **Test:** 70 da «Muy compatible» y 69 «Compatible»; con sueldo mínimo marcado, una oferta sin sueldo dice «No
    dice el sueldo» y conserva su nota; a igual nota, la que cumple todo va antes.
  - **Navegador:** lista y detalle de Ofertas, 1280 y 390 px, claro y oscuro.
  Hecho (28-nov, 0 USD; D-120 y D-123): `veredicto`, `faltas` y `tests/test_s12_t18_veredicto.py`; capturas miradas.
- [x] T19 — La nota corregida manda en su lista, con su motivo y «Quitar la mía»; texto de ayuda de RF-10.15e.
  - **Test:** corregir de 75 a 40 cambia orden, rango y veredicto; la corrección sigue tras una versión nueva del
    perfil; «Quitar la mía» devuelve el 75. Ninguna llamada al modelo.
  - **Navegador:** 1280 y 390 px, claro y oscuro.
  Hecho (28-nov, 0 USD; D-118, D-119, D-121, D-122 y D-125): `tests/test_s12_t19_nota_usuaria.py`; capturas miradas.
- [x] T20 — Landing revisada: promete solo lo que funciona.
  Revisada (28-nov): lo que dice de la compatibilidad ya funciona; sin cambios.
- [ ] T21 — **No se da por hecha (28-nov, D-127):** B11 sin aprobar (15 de 20 en la misma franja (mínimo 17), 3 a dos franjas o más y 0 datos inventados); quedan sin hacer B4 y V1 a V6,
  y el PR #48 sin fusionar. El paso se cierra como «medido»; se vuelve al `matcher` antes de que entren usuarias reales.
  Cierre del paso. 🛑 Revisión de Mar sobre 20 recomendaciones (a ciegas si T14 se cierra como «medida»:
  apunta la franja antes de ver la nota; D-113; aprueba con 17 de 20 en su franja, ninguna a dos y 0 datos
  inventados, D-116) y prueba manual (lote 2, con B4, D-124; al prepararlo, puntuar 26 ofertas agotó los 60 s de espera del
  modelo: sube a 240 s, D-126; hoja 1 de B11 rellenada y comparada el 28-nov; sección en
  `docs/plan-pruebas-manuales.md`); `specs/index.md`, PRD y pauta al día; PR.

### Cambios pequeños
- [x] 390 px: botones de la portada a todo el ancho, sin «Calificar todas» cuando no hay CV, y `tests/capturas.js` para
  comprobar pantallas. Test: `tests/test_s12_portada_movil_calificar.py`.
- [x] `/favicon.ico` con el cuadrado de la marca. Test: `tests/test_s12_favicon.py`.
- [x] «Ver» un PDF en el móvil: cada página como imagen (`pypdfium2`; prueba M19 de Mar). Test:
  `tests/test_s12_visor_pdf_movil.py`.
- [x] Simetría a 390 px: paneles de Perfil a todo el ancho, ventanas con «Cerrar» junto al título, filas de
  botones en columnas iguales y sin la caja vacía en Candidatura. Test: `tests/test_s12_simetria_movil.py`.
- [x] Iconos de la app instalable (192, 512 y maskable) con el cuadrado de la marca sobre fondo oscuro.
