---
type: spec
title: matcher-puestos — Spec funcional
description: Requisitos en notación EARS de la spec 012 (paso 2 del PRD) — puestos sugeridos por niveles de evidencia, medidos antes de construir; nota del matcher fiable y estable; veredicto en palabras con citas comprobadas; condiciones fuera de la nota y correcciones que mandan en la lista de quien corrige.
tags: [spec, matcher, puestos, recomendacion, evals]
status: active
sources: [./clarifications.md, ../prd.md, ../system.md, ../002-perfil-recomendacion/spec.md, ../009-cv-maestro-entrevista/spec.md, ../010-simplificacion/spec.md]
generated: { at: 2026-11-25 }
verified: { by: human, at: 2026-11-25 }
stale_after: null
---

# matcher-puestos — Especificación

**PRD:** US-002 · RF-006, RF-007 · NFR-02, NFR-03, NFR-04, NFR-09 · R-03, R-08.

## Contexto
Dos problemas distintos (informe F4; [PRD](../prd.md), paso 2):
- **Qué puestos sugerir desde el CV.** Nunca se ha medido. Hoy basta una habilidad suelta para justificar un
  puesto («Controller financiero» citando «Excel»), y todos llegan marcados.
- **Qué nota darle a cada oferta.** El eval `recomendacion` da 0,67-0,71 dentro de ±10 (21 casos), frente a 0,90.

Todo lo de después (redactar, avisar y enviar) se apoya en los dos. Se mide antes de construir (F4-D5). Las
decisiones y los supuestos están en [clarifications.md](./clarifications.md); las decisiones D-NNN, en la
pauta de Mar.

## Requisitos (EARS)

### A · Medir antes de construir (F4-D5, F4-D9)
- **RF-12.1** El sistema DEBERÁ tener un set de evals `puestos` con 30 CV inventados: los 18 del eval `perfil`
  y 12 difíciles (cambio de sector, junior sin experiencia, bilingüe, título genérico, nivel alto y dos oficios).
  Cada puesto sugerido DEBERÁ llevar la etiqueta «lo ha sido», «afín» o «ajeno», y cada CV, de 3 a 5 puestos
  imprescindibles. Etiqueta la mayoría de tres etiquetadores ciegos; Mar repasa lo que no tenga unanimidad.
- **RF-12.2** El set DEBERÁ medirse con el `clasificador_postulante` actual antes de cambiar la puerta. Las
  variantes de la puerta se comparan en código sobre esas mismas respuestas, sin volver a llamar al modelo.
- **RF-12.3** Umbrales del set `puestos`: 0 puestos «ajenos» entre los marcados; precisión de los marcados
  ≥ 0,95; precisión de los no marcados («afín» o mejor) ≥ 0,85; cobertura de los imprescindibles ≥ 0,80; equidad
  al 100 % (RF-12.30d). La estabilidad (RF-12.30e) se informa y no suspende el set (D-052). Se informa el acuerdo entre etiquetadores (kappa). En un CV sin ninguna experiencia, un puesto marcado
  «afín» cuenta como acierto en la precisión de los marcados (D-036); un «ajeno» marcado sigue suspendiendo el set.
- **RF-12.3b** (D-064) La CI DEBERÁ correr el set `puestos` con las respuestas reales grabadas, sin llamar al modelo.
- **RF-12.4** El set de títulos de 9a (RF-9.3e) DEBERÁ repasarlo Mar en los pares sin unanimidad y en los que
  difieren del código, y ampliarse con unos 50 pares de sinónimos sin palabras en común. Después se vuelve a
  medir RF-9.3e. SI la cobertura baja de 0,90, ENTONCES se para y se propone a Mar la prueba de embeddings, solo
  para proponer candidatos (F4-D6), como cambio de esta spec.
- **RF-12.4b** (D-053) Con la cobertura en 0,58, antes de cambiar la búsqueda se DEBERÁN medir tres vías (embeddings en local,
  tabla de sinónimos en código y sinónimos dados por el modelo) sobre pares que ninguna haya visto. Nada entra en la
  aplicación hasta que Mar elija.
- **RF-12.4c** (D-061) La búsqueda por título DEBERÁ casar también con las otras formas de anunciar cada puesto: las que
  da el modelo pequeño una vez por puesto (también para los que ella escribe, al guardar) y las de una tabla en código.
  RF-9.3e se mide con las dos (≥ 0,90 en el set); en puestos nuevos la cobertura medida es 0,68, con precisión 1,0.
- **RF-12.4d** (D-062) «Qué buscas» DEBERÁ enseñar bajo cada puesto marcado «También busco: …» con sus otras formas, sin
  editarlas. Los términos excluidos no se amplían.
- **RF-12.4e** (D-068) El agente `sinonimos-puestos` DEBERÁ tener su set de evals con umbral (RT-11), en el bloque N. El
  umbral lo fija Mar antes de medir con el modelo real.
  (D-076) Como máximo 0,05 de las formas pueden ser otro puesto y, solo con las formas del modelo, DEBERÁ
  encontrarse al menos 0,60 de los anuncios firmados que el texto solo no encuentra. La CI DEBERÁ correr el set con
  las respuestas reales grabadas, sin llamar al modelo.
  Al etiquetar una forma: en dirección y ventas, otro escalón de la misma área es el mismo puesto; en los oficios, no
  (D-072). Una palabra suelta que arrastra otro oficio («Developer», «Server») es otro puesto (D-073). Los parecidos
  dudosos los decide Mar (D-074).
  (D-075) El prompt del agente DEBERÁ pedir esas mismas reglas: ni otro escalón en los oficios, ni palabras sueltas que
  sirvan para otro oficio, ni puestos parecidos.

### B · Puestos por niveles de evidencia (PRD RF-006)
- **RF-12.5** La puerta de puestos DEBERÁ dar a cada puesto sugerido un nivel, decidido por código (S1):
  - **Nivel 1 · «Lo has sido»:** el `dato` es el puesto entero de una experiencia y el título es ese mismo puesto,
    también traducido, en otro género o con un sinónimo.
  - **Nivel 2 · «Afín»:** el `dato` es una titulación o una certificación entera, o un puesto entero con un
    título distinto.
  - Una especialidad del mismo puesto («Camarero de barra» para una camarera) cuenta como el mismo puesto;
    un puesto de otro escalón («Jefa de RRHH» para una directora), no: es nivel 2 (D-037).
  - **Fuera:** el `dato` es solo una habilidad, el titular, el resumen o un trozo de un campo.
- **RF-12.6** En «Qué buscas», solo el nivel 1 DEBERÁ llegar marcado. El nivel 2 DEBERÁ llegar sin marcar y con
  su porqué a la vista («Por tu grado en Estadística»). Lo de fuera NO DEBERÁ enseñarse. *(Cambia RF-9.3b.)*
- **RF-12.6c** (D-063) El porqué de cada puesto sugerido DEBERÁ decir de dónde sale: «Lo has sido: <puesto>» (nivel
  1), «Parecido a tu puesto: <puesto>», «Por tu certificación: <nombre>» o, si es una titulación, «Por tu <titulación>»
  cuando empieza por grado, máster, licenciatura, ingeniería, diplomatura, doctorado, ciclo o bachillerato, y «Por tu
  titulación: <titulación>» en los demás casos. El de RF-12.7 lleva delante «Para empezar, ».
- **RF-12.6b** Los puestos de las experiencias del perfil DEBERÁN sugerirse siempre, de nivel 1 y marcados,
  puestos por código aunque el modelo no los devuelva (D-052).
- **RF-12.7** SI el CV no tiene ninguna experiencia, ENTONCES los puestos por titulación DEBERÁN llegar marcados,
  con el porqué «Para empezar, por tu grado en…» (F4-D7, S4).
- **RF-12.8** La puerta NO DEBERÁ sugerir un puesto cuyo título indique un nivel superior al del perfil
  («Senior», «Lead», «Head», «Jefe/a», «Director/a»…, frente a `taxonomia.nivel`). «Senior», «Lead» y «Jefe/a» piden
  nivel «senior»; «Head» y «Director/a», «direccion»; un puesto que ya ha tenido nunca se bloquea (D-038).
  El filtro de ofertas por nivel no cambia (F4-D4).
- **RF-12.9** Un puesto genérico (lista corta en código: «Manager», «Técnico», «Responsable», «Especialista»,
  «Consultor»…) DEBERÁ casar solo con ofertas de la familia del perfil (F4-D3, S2). Una oferta sin familia pasa,
  como cualquier oferta a la que le falta un dato del filtro (P2 de la spec 002). Vale para los puestos sugeridos y
  para los que escribe ella.
- **RF-12.10** Cada puesto sugerido DEBERÁ guardar su nivel y el tipo de dato del que sale, para que el envío
  (spec 011, parte 2) use solo el nivel 1 o los marcados por ella (F4-D8).

### C · Nota fiable y estable (PRD NFR-02)
- **RF-12.11** El eval `recomendacion` DEBERÁ pasar de 21 a unos 60 casos: más sectores, notas intermedias
  (40-70), perfiles casi vacíos, ofertas incompletas, correcciones importadas, casos de orden y pares de equidad.
- **RF-12.12** Cada medición con el modelo real DEBERÁ correr el set 3 veces seguidas y dar al menos 0,90 de
  casos dentro de ±10 en cada una. DEBERÁ informar, por caso, cuánto varía la nota entre las tres.
  (D-100) Las tres pueden correr por etapas: la pasada 1 y, solo si pasa, la 2 y la 3, sin tocar nada entre medias.
  `horma eval repuntuar` junta lo grabado de varias ejecuciones como pasadas seguidas y vuelve a puntuarlo en
  código, sin llamar al modelo; así se ajustan también los valores de RF-12.35.
  (D-112, D-113) Para cerrar T14 cuentan tres pasadas nuevas, por etapas; la pasada 1 de T14m no vale. SI una no
  llega, ENTONCES se para y T14 se cierra como «medida», sin más cambios de reglas, prompt ni etiquetas sobre
  estos casos; el examen pasa a ser la revisión de Mar de 20 recomendaciones reales, a ciegas (apunta la franja
  antes de ver la nota).
- **RF-12.13** El eval DEBERÁ medir el orden (S7): en cada caso de orden, la mejor oferta esperada sale primera
  frente a las que esperan más de 10 puntos menos (D-109), y ningún par con 20 o más puntos de diferencia
  esperada sale al revés.
  (D-070) Un caso de orden mide solo el orden: sus notas no cuentan en el ±10 de RF-12.12, que se calcula sobre
  los casos de una oferta.
- **RF-12.14** La nota esperada de un caso existente solo DEBERÁ cambiarse con el OK de Mar y con el motivo
  escrito en su `esperado.json` (S8). Cambios aprobados: D-082 a D-084, D-099 y D-110.
- **RF-12.15** CUANDO pase la puerta, `recomendacion` DEBERÁ volver a correr con el modelo real en `evals-reales`
  de la CI.
- **RF-12.16** El `matcher` DEBERÁ medirse también con el modelo pequeño, con el mismo eval. SI pasa la puerta,
  ENTONCES Mar decide si se cambia (F1-E6) y la decisión se anota como D-NNN.
  (D-117) Medido el 28-nov: no pasa (nota 0,72-0,78). Sigue el modelo mayor y F1-E6 queda abierta para volver a
  probarlo más adelante.

### D · Explicación fiable (PRD RF-007)
- **RF-12.17** Junto a la nota, Horma DEBERÁ enseñar un veredicto en palabras, puesto por código (F7-D5, S5):
  70-100 «Muy compatible», 50-69 «Compatible», 30-49 «Poco compatible» y 0-29 «No te la recomendamos».
- **RF-12.18** (D-080, D-087) La explicación DEBERÁ empezar por la frase de su franja, puesta por código con la nota ya
  acotada (RF-12.35): 70-100, por qué te la recomendamos; 50-69, por qué tienes opciones; 30-49, por qué no te la
  recomendamos, aunque puedes intentarlo; 0-29, por qué no te la recomendamos. El `matcher` DEBERÁ escribir solo
  2 o 3 frases de hechos, sin la frase de franja.
  Frases: «Te la recomendamos por esto.», «Tienes opciones por esto.», «No te la recomendamos, aunque puedes
  intentarlo.» y «No te la recomendamos.». Una explicación retirada queda sin frase delante.
- **RF-12.19** `cita_perfil` y `cita_oferta` DEBERÁN ser fragmentos literales, y un verificador en código DEBERÁ
  comprobar que existen en la copia del perfil (RF-12.30) y en la oferta; lo que vaya en «/a» se enseña con
  `en_genero`. SI alguna no existe, ENTONCES se piden otra vez, una sola vez, solo esas ofertas. SI vuelve a
  fallar, ENTONCES la explicación se retira y la nota se conserva con el aviso «Sin explicación comprobada» (S6).
- **RF-12.20** La explicación NO DEBERÁ nombrar las instrucciones embebidas de una oferta, ni siquiera para
  decir que las ignora (NFR-03).
- **RF-12.21** (D-078) Un revisor con el modelo pequeño, solo dentro del eval, DEBERÁ ver la copia del perfil y la
  oferta enteras y juzgar que cada explicación no afirma nada que no esté en ellas y que sus citas tienen que ver
  con lo que dice.
  (D-079) Callar un requisito discriminatorio NO es un fallo, y el «nivel» de la oferta y del perfil es el del
  puesto, no el de un idioma.
  (D-098) Cada rechazo DEBERÁ juzgarse dos veces más y contar solo si lo confirman 2 de 3. El eval DEBERÁ guardar
  el `motivo` de cada juicio y listar los rechazos confirmados para que Mar los revise. Umbral: en cada pasada, al
  menos el 95 % de las explicaciones revisadas sin rechazo confirmado; y, en la revisión de Mar, 0 graves (un
  puesto, un título, un idioma o unos años inventados).
  (D-112) También es dato inventado, y grave, atribuir a un puesto tareas que su descripción no recoge; el revisor
  DEBERÁ rechazarlo. (D-115) Y dar por pedido lo que la oferta no pide, aunque esté en su título. No es grave
  nombrar lo que el trabajo diario de un puesto incluye y RF-12.34 da por cubierto («trato con clientes» de una
  camarera).
- **RF-12.22** El `matcher` DEBERÁ recibir solo la copia de RF-12.30; la equidad de nombre y género la cubre
  RF-12.30d. En los pares que cambian la edad, la nacionalidad o un hueco laboral, la mediana de 3 ejecuciones
  DEBERÁ coincidir ±3, y ninguna explicación DEBERÁ citar el rasgo. Umbral: 100 % (NFR-04, RT-09).
- **RF-12.23** Con ofertas en otro idioma, muy largas, con instrucciones embebidas o sin datos, y con tandas que
  fallan en parte, el `matcher` DEBERÁ fallar con un aviso y NUNCA dar una nota inventada. Una oferta sin
  resultado queda «sin puntuar».
- **RF-12.24** `convertir_cv` DEBERÁ ignorar el texto invisible de un CV: blanco sobre blanco, de tamaño 0 u
  oculto.

### E · Condiciones y correcciones (D-026, D-027)
- **RF-12.25** Las condiciones NO DEBERÁN cambiar la nota. Junto al veredicto, Horma DEBERÁ enseñar una línea
  corta con cada condición marcada por la usuaria que la oferta no dice o no cumple («No dice el sueldo»,
  «Contrato temporal»). Con la misma nota, DEBERÁ ir antes la oferta que cumple todo. Se calcula al pedir la
  lista, sin llamar al modelo. *(Amplía RF-5.2 y RF-6.5.)*
- **RF-12.26** CUANDO la usuaria corrija la nota de una oferta, su lista DEBERÁ usar su nota para ordenar, para
  el rango y para el veredicto, y enseñar «Tu nota: 40 · Horma: 75» con el motivo que escribió, legible sin abrir
  nada más. La corrección vale para esa oferta aunque cambie su perfil, hasta que pulse «Quitar mi nota» (S9).
  No llama al modelo. *(Cambia RF-10.15e.)*
- **RF-12.36** (D-081) SI el nivel de la oferta es inferior al del perfil (taxonomía) y la relación es mismo puesto
  o afín, ENTONCES Horma DEBERÁ enseñar junto al veredicto «Pide menos de lo que tienes», puesto por código. La
  nota NO DEBERÁ cambiar.
- **RF-12.27** Mar DEBERÁ revisar las correcciones antes de cada medición del eval, con
  `horma eval importar-correccion`. Ninguna entra en `evals/` sin su revisión (RF-2.13).

### G · Copia ciega: el género no influye (D-043 a D-048)
- **RF-12.30** ANTES DE llamar a `clasificador_postulante` o al `matcher`, el sistema DEBERÁ construir en código,
  sin modelo, una copia del perfil (`PerfilCiego`) y enviar solo esa copia. El perfil y el CV NO DEBERÁN cambiar
  (D-047).
  - **RF-12.30a** La copia DEBERÁ llevar solo los campos de su esquema (S12): de cada experiencia, puesto,
    empresa, inicio, fin y descripción; de cada formación, título, inicio y fin; idiomas y su nivel,
    habilidades, proyectos, certificaciones (nombre, entidad y fecha) y `otros`; la taxonomía, solo para el
    `matcher`. NO DEBERÁN entrar el nombre, `genero_puestos`, los titulares, los resúmenes, los orígenes, el
    centro de estudios, las actividades, los periodos cubiertos, las preguntas pendientes ni las instrucciones
    embebidas.
  - **RF-12.30b** En todo texto de la copia, el sistema DEBERÁ borrar el nombre de la usuaria (cada palabra de 3
    o más letras, entera; nunca «del», «las», «los», «van», «von» ni «san», y no dentro del puesto, la
    titulación o la certificación, D-051), los correos, las URL y los teléfonos, y cambiar cada palabra del léxico por su forma
    de la copia (D-043). Las fechas NO DEBERÁN cambiar (D-044). Las descripciones DEBERÁN entrar, pasadas por el
    léxico (D-045).
  - **RF-12.30c** Léxico: cerrado, en código y sin reglas de sufijos. Cada entrada DEBERÁ dar la forma de la
    copia («Camarero/a», «Actor/actriz», «Modista») y las formas femenina y masculina; reconoce con y sin tilde,
    en plural y sin distinguir mayúsculas. Una palabra marcada como ambigua («técnica», «química»…) solo DEBERÁ
    cambiar si es la primera de un puesto, una titulación o una certificación. Un adjetivo («administrativa»,
    «jurídico», «titulada») DEBERÁ cambiar solo si va justo detrás de una palabra de persona (D-049). Una palabra que también es inglesa («director», «editor»,
    «supervisor»…) y el plural «dependientes» DEBERÁN cambiar solo si son la primera o van tras un artículo
    (D-050). SI delante de una palabra del
    léxico o de un epiceno listado («responsable», «gerente», «asistente») va un artículo, ENTONCES el artículo
    DEBERÁ pasar a su doble forma. Una palabra que no esté en el léxico NO DEBERÁ cambiar.
  - **RF-12.30d** Equidad: dos perfiles gemelos que solo cambian el nombre y el género gramatical DEBERÁN dar
    copias idénticas, carácter a carácter. Las gemelas se escriben a mano, no con el léxico. Umbral: 100 %, en la
    suite de tests (D-046).
  - **RF-12.30e** Estabilidad: cada CV del set `puestos` DEBERÁ pasarse 3 veces con el modelo real. Por CV,
    «puestos marcados en las tres pasadas / puestos marcados en alguna». Se informa la media; no hay umbral (D-052;
    primera medida, 26-nov: 0,52).
  - **RF-12.30f** Los títulos que devuelva el clasificador DEBERÁN pasar a la forma de la copia y enseñarse con
    `en_genero` según `genero_puestos`; sin él, en «/a». El género NUNCA DEBERÁ deducirse del nombre. El `dato`
    que se guarda y se enseña DEBERÁ ser el texto original del perfil. CUANDO cambie `genero_puestos`, los
    títulos sugeridos DEBERÁN reescribirse en código, sin llamar al modelo.
  - **RF-12.30g** La puerta (RF-12.5) DEBERÁ comparar el `dato` con los campos de la copia.
  - **RF-12.30h** Las huellas (RF-10.10c y 10.10d) DEBERÁN calcularse sobre la copia, así que ya no incluyen el
    titular: la de compatibilidad, experiencia, formación, habilidades e idiomas; la de clasificación,
    experiencia, formación y certificaciones. Cambiar el nombre o `genero_puestos` NO DEBERÁ volver a clasificar
    ni a puntuar.
  - **RF-12.30i** La búsqueda por puesto DEBERÁ casar también con las formas irregulares del léxico («Gobernanta»
    con «Gobernante/a»). «Asistenta» y «Asistente» NO DEBERÁN dar la misma clave.
- **RF-12.31** El `matcher` NO DEBERÁ recibir las condiciones de la usuaria (D-026).
- **RF-12.32** La explicación DEBERÁ hablar de la experiencia y de la oferta, no de la persona: sin adjetivos ni
  sustantivos que concuerden con ella («tu experiencia en sala encaja», no «eres una candidata ideal»).
- **RF-12.33** (D-079) Un título, un máster o un certificado NO DEBERÁ contar como experiencia, ni en la nota ni en
  la explicación.
- **RF-12.34** (D-080) Por cada oferta, el `matcher` DEBERÁ devolver, además de la nota:
  - una marca por cada requisito de la oferta, identificado por su posición: `tipo` (exigido, valorable o no
    aplica) y `cubierto` (sí, a medias o no). Un requisito sobre un rasgo personal o una condición es «no aplica»:
    los rasgos personales los fuerza además el código; las condiciones, solo el prompt (D-088).
    «Sí» incluye lo que forma parte del trabajo diario de un puesto del perfil. «A medias» es el mismo puesto sin
    la especialidad (nunca «no»), la formación sin la experiencia pedida (RF-12.33), la experiencia sin los años
    o la duración que se piden, o algo muy cercano. «No» es que nada lo cubre; un título o puesto superior del
    mismo ámbito nunca es «no» (D-091);
  - la `relacion` con el puesto: mismo puesto, afín u otro oficio.

  SI falta la marca de algún requisito, ENTONCES esa salida DEBERÁ rechazarse. Las marcas se deciden con todo el
  perfil: «no consta» es una regla de la explicación, no de las marcas; «N años» se cubre con las fechas de los
  puestos (D-100, D-113). La explicación NO DEBERÁ nombrar como carencia algo que la oferta no pide, opinar del
  nivel, deducir lo que no consta (se dice «no consta»), calcular años de experiencia (copia las fechas: «desde
  2019» solo si el puesto sigue; si acabó, «de 2015 a 2025»), contar los requisitos («los dos requisitos»), decir
  que algo «se acerca», «se relaciona» o «cubre en parte» un requisito (D-094), ni juntar las tareas de un puesto
  con otro: se citan solo con su puesto (D-113).
- **RF-12.35** (D-080, D-081, D-085) El código DEBERÁ acotar la nota del `matcher` con las marcas, la relación y
  la taxonomía, sin llamar al modelo. Un requisito «no aplica» NO DEBERÁ cambiar la nota y dos perfiles gemelos
  (RF-12.30d) con las mismas marcas DEBERÁN recibir la misma. El veredicto y la franja usan la nota acotada.
  Reglas de partida, con sus valores en un solo sitio:
  1. Todos los exigidos «sí» y mismo puesto o afín: mínimo 90. (D-100 quita el 95 de D-092.)
  2. Ningún exigido que aplique y mismo puesto o afín: mínimo 80. SI la oferta no trae ningún requisito, solo
     el mismo puesto (D-093).
  3. Todos los exigidos «sí» y algún valorable «no»: mínimo 85. Manda sobre la 1 (D-089).
  4. Mismo puesto, la titulación exigida «sí» y sin mayoría de exigidos «no»: mínimo 70 (D-091). Es titulación el requisito que
     empieza por grado, máster, licenciatura, ingeniería, diplomatura, doctorado, ciclo, bachillerato, FP o
     título (D-089).
  5. La mayoría de los exigidos «no», o la mitad y ninguno «sí»: máximo 30. Si además la oferta es de un nivel
     superior al del perfil o de otro oficio: máximo 20; de nivel superior y sin ser el mismo puesto: 15 (D-091,
     D-100). Los topes 20 y 15 solo se aplican si ningún exigido sale «sí»; si cubre alguno, el tope es 30 (D-111).
  6. Otro oficio con todos los exigidos «sí»: entre 30 y 55, salvo RF-12.37 o un perfil sin ninguna experiencia
     (D-091).
  7. Un nivel de la oferta inferior al del perfil no cambia la nota.

  Los valores solo DEBERÁN ajustarse sobre respuestas grabadas, de 5 en 5 y sin pasar de siete reglas.
- **RF-12.37** (D-085) SI la oferta casa con un puesto marcado en «Qué buscas», ENTONCES NO DEBERÁ contar como
  otro oficio. CUANDO cambie «Qué buscas», la nota DEBERÁ recalcularse en código desde la nota del modelo, las
  marcas y la relación guardadas, sin llamar al modelo ni cambiar la huella (RF-12.30h).

### F · Pantallas
- **RF-12.28** Los cambios de Ofertas y de «Qué buscas» DEBERÁN usar componentes de la guía (uno nuevo se añade
  antes a la guía, RF-6.9), sin las palabras de RF-6.8, y comprobarse a 1280 y 390 px, en claro y en oscuro,
  mirando alineación y simetría (RF-6.4b).
- **RF-12.29** SI la landing habla de la compatibilidad o de los puestos, DEBERÁ prometer solo lo que ya funciona.

## Criterios de aceptación (puerta de salida del paso 2)
- Un CV que solo nombra «Excel» como habilidad no trae «Controller financiero» marcado. Cada puesto marcado cita
  un puesto que la persona ya ha tenido.
- Set `puestos` en sus umbrales (RF-12.3), con copias idénticas entre gemelas (RF-12.30d); set de títulos de 9a con cobertura ≥ 0,90 y precisión ≥ 0,95.
- Eval `recomendacion` ≥ 0,90 dentro de ±10 en 3 ejecuciones seguidas con el modelo real, y de vuelta en
  `evals-reales` (NFR-02).
- 100 %: sin rasgos personales, pares de equidad dentro de ±3 y explicaciones con citas verificadas.
- Revisor según RF-12.21 (D-098, D-112 y D-115): al menos el 95 % sin rechazo confirmado en cada pasada y 0 graves.
- Una oferta que no publica el sueldo, con sueldo mínimo marcado, enseña «No dice el sueldo» y la misma nota.
- Corregir una nota de 75 a 40 reordena la lista y enseña el motivo; «Quitar mi nota» la devuelve a 75.
- Revisión de Mar sobre 20 recomendaciones (a ciegas si T14 se cierra como «medida», D-113): al menos 17 de 20 en
  su misma franja, ninguna a dos franjas y 0 datos inventados (D-116).
- Pantallas comprobadas a 1280 y 390 px, en claro y en oscuro; suite verde.

## Riesgos
- **Los evals reales cuestan más de lo estimado** (el `cv` llegó a 2,7 USD frente a 0,5-1). Estimación y OK de
  Mar antes de cada gasto ([plan](./plan.md), Costes).
- **Familia mal asignada:** RF-12.9 depende de ella. Se mide en el set `puestos`; si falla, F4-D3, segundo paso.
- **Maquillar el eval:** cambiar notas esperadas para aprobar. Lo frena RF-12.14.
