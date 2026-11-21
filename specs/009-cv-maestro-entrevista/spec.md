---
type: spec
title: cv-maestro-entrevista — Spec funcional
description: Requisitos de la fase 9 en notación EARS, en dos partes que se construyen y firman por separado — 9a (huecos y avisos del CV, puestos recomendados en «Qué buscas» y CV maestro visible) y 9b (entrevista con catálogo de preguntas de recruiter, texto o audio, valoración para entrenar y respuestas como fuente de CV, carta y estilo).
tags: [spec, perfil, entrevista, estilo, preferencias, agentes]
status: active
sources: [./clarifications.md, ../system.md, ../constitution.md, ../002-perfil-recomendacion/spec.md, ../003-candidatura/spec.md, ../005-correcciones-profesor/spec.md, ../007-ajustes-pantalla/spec.md, ../008-portada-ofertas/spec.md]
generated: { by: claude-code, at: 2026-11-21 }
verified: { by: human, at: 2026-11-21 }
stale_after: null
---

# cv-maestro-entrevista — Especificación

## Contexto
Tras subir su CV, la usuaria ve qué le falta (huecos y avisos), busca ofertas por títulos de puesto
(castellano, inglés y sinónimos) y ve su CV maestro (9a). Después hace una entrevista de recruiter que la
conoce mejor y la entrena, y Horma usa lo que cuenta para escribir CV y cartas más suyos (9b).

La fase se divide en dos partes (P17). Cada una tiene su plan, sus tareas, su rama, su prueba manual y su PR:
- **9a — CV y puestos.** No hay agentes nuevos; cambian `extractor_perfil` (otras actividades, RF-9.1d) y
  `clasificador_postulante` (puestos, RF-9.3), así que se rehacen las evals de `perfil`.
- **9b — Entrevista.** Hay dos agentes nuevos (`entrevistador` y `valorador_entrevista`), cada uno con su set
  de evals y su umbral. Cambian `analizador_estilo`, `redactor_cv` y `redactor_carta`, así que se rehacen sus
  evals.

Todo lo nuevo sigue la guía de la fase 6 (RF-6.9). Las respuestas del Clarify están en
[clarifications.md](./clarifications.md) y se citan como P1…P18.

Esta spec modifica:
- 9a: RF-2.8 y RF-2.11 (puestos), RF-7.5 (bloques de Perfil) y RF-8.4 (campos de «Qué buscas»).
- 9b: RF-2.3 (dónde se ven las preguntas pendientes), RF-3.6 y la redacción del CV (nueva fuente), y RF-9.5
  (bloques de Perfil).

---

# Parte 9a — CV y puestos

## Requisitos (EARS)

### Huecos (RF-9.1)
- **RF-9.1** CUANDO se componga el CV maestro, Horma DEBERÁ detectar con código cada periodo de **6 meses o
  más** sin experiencia, formación ni otra actividad que conste en el CV (P3), desde la primera fecha del perfil
  hasta hoy. Los periodos que se solapan cuentan juntos.
- **RF-9.1d** Un periodo con otra actividad que conste en el CV (voluntariado, cuidados, viajes, baja u
  hospitalización…) NO DEBERÁ contar como hueco (P18). SI la actividad es un dato del art. 9 (salud), Horma
  DEBERÁ guardar solo sus fechas como «periodo cubierto», sin el motivo.
- **RF-9.1b** Una fecha con solo el año DEBERÁ leerse a favor de la usuaria (inicio en enero, fin en
  diciembre), para no inventar huecos. Una entrada sin fechas no cuenta: ya es una pregunta pendiente (RF-2.3).
- **RF-9.1c** En 9a, cada hueco DEBERÁ mostrarse como aviso neutro, sin pedir el motivo: «Entre marzo de 2019
  y enero de 2020 no consta trabajo ni formación.», con «Añadir en Mi perfil» y «Dar por visto». En 9b pasa a
  ser una pregunta de la entrevista (RF-9.7c).

### Avisos de calidad por reglas (RF-9.2)
- **RF-9.2** CUANDO se componga el CV maestro, Horma DEBERÁ dar estos avisos por reglas, sin modelo (P2):
  - CV de más de 1.000 palabras (unas 2 páginas);
  - experiencia sin descripción;
  - experiencia sin ninguna cifra ni resultado («quizá falten logros»);
  - perfil sin resumen;
  - CV sin correo ni teléfono (se mira en el texto subido; Horma no los guarda).
- **RF-9.2b** Un aviso DEBERÁ decir qué pasa y cómo arreglarlo en una frase, con «Corregir», que lleva a la
  sección de Mi perfil, y «Dar por visto».
- **RF-9.2c** Un hueco o aviso dado por visto NO DEBERÁ volver a salir mientras no cambie lo que lo causa,
  aunque la usuaria suba otro CV. Lo visto se guarda por usuaria (RLS).
- **RF-9.2d** El aviso de CV largo DEBERÁ ofrecer dos opciones (P18): «Mantener la longitud» (un perfil sénior
  puede tenerlo todo relevante) y «Que Horma lo sintetice». La elección se guarda por usuaria y se puede cambiar;
  la aplica `redactor_cv` en 9b (RF-9.10f). Hasta elegir, Horma sintetiza como hoy.

### Puestos recomendados (RF-9.3)
- **RF-9.3** `clasificador_postulante` DEBERÁ sugerir, en la misma llamada, **8-15 títulos de puesto** ajustados
  a la experiencia de la usuaria: en castellano, en inglés y sinónimos (P11). Cada uno cita el dato del perfil
  que lo justifica (RT-08).
- **RF-9.3b** «Qué buscas» DEBERÁ separar **Área** (las 19 familias de hoy) y **Puestos** (títulos). Los
  sugeridos llegan como casillas marcadas, con «Seleccionar todo» y «Quitar selección»; la usuaria puede
  desmarcar, añadir los suyos y escribir **términos excluidos** («prácticas», «comercial»). Lo que ella marcó o
  escribió no lo pisa una subida nueva.
- **RF-9.3c** Una oferta DEBERÁ entrar a puntuar SI su familia está entre las marcadas **o** su título contiene
  un puesto marcado (P9), y NO DEBERÁ entrar SI su título contiene un término excluido.
- **RF-9.3d** La coincidencia del título DEBERÁ ser por **frase completa normalizada** (sin tildes, sin
  mayúsculas, singular y plural, guiones como espacios), nunca por una palabra suelta del puesto: «Data
  Analyst» casa con «Senior Data Analyst (m/f)» y no con «Data Entry» (P10).
- **RF-9.3e** La coincidencia DEBERÁ medirse con un set de **títulos reales del catálogo** (aciertos y falsos
  positivos etiquetados por Mar): precisión ≥ 0,95 y cobertura ≥ 0,90 para cerrar la parte (P10). Sin coste de
  modelo.
- **RF-9.3f** El tope diario de puntuación (RF-8.5b) no cambia: ampliar la búsqueda no amplía el gasto.

### CV maestro visible (RF-9.4)
- **RF-9.4** «Tu CV maestro» DEBERÁ enseñar el CV maestro de la última versión del perfil con formato
  (títulos, listas, párrafos), su fecha y su número de versión (P12), y la frase «Es el texto del que Horma saca
  tus CV y cartas. Se cambia desde Mi perfil.»
- **RF-9.4b** Cada sección DEBERÁ tener «Editar», que lleva a esa sección de Mi perfil. El texto NO DEBERÁ
  poder editarse aquí (RF-5.1b).
- **RF-9.4c** Lo que se ve DEBERÁ ser exactamente lo que usan los redactores, y solo lo ve su dueña (RLS).
  Se muestra sin interpretar HTML (RF-8.3b).

### Perfil en 9a (RF-9.5)
- **RF-9.5** Perfil DEBERÁ mostrar sus bloques en este orden (sustituye a RF-7.5):
  1. Tus CV, abierto;
  2. Mi perfil, abierto;
  3. Preguntas pendientes y avisos, desplegable, con el número en el título; abierto CUANDO haya alguno.
     Primero las preguntas (RF-2.3), luego huecos y avisos (RF-9.1c, RF-9.2);
  4. Tu CV maestro, desplegable, cerrado (RF-9.4);
  5. Tu estilo de redacción, desplegable, cerrado.

## Criterios de aceptación (9a)
- Un CV inventado con 8 meses sin trabajo ni estudios da un hueco; uno con 4 meses, no; un año suelto no crea
  huecos falsos. Un periodo de voluntariado o de cuidados que conste en el CV no da hueco.
- Un CV de más de 1.000 palabras ofrece «Mantener la longitud» y «Que Horma lo sintetice», y la elección queda
  guardada.
- Un CV con una experiencia sin cifras da el aviso de logros. Un aviso dado por visto no vuelve al subir el mismo
  CV otra vez.
- «Qué buscas» enseña Área y Puestos, con los sugeridos marcados; la búsqueda trae una oferta con título en
  inglés de otra familia y no trae una con un término excluido. El set de títulos pasa los umbrales de RF-9.3e.
- «Tu CV maestro» coincide con `perfiles.cv_maestro`; otra usuaria recibe 404.
- Evals de `perfil` en umbral.
- Todo comprobado a 1280 y 390 px, en claro y en oscuro (RF-6.4b).

---

# Parte 9b — Entrevista

## Requisitos (EARS)

### Catálogo de preguntas (RF-9.6)
- **RF-9.6** Horma DEBERÁ tener un catálogo de **100-150 preguntas de recruiter** en castellano, cada una con
  su número y sus etiquetas de situación (huecos según motivo, cambio de sector, primer empleo,
  reincorporación, perfil sénior, logros, soft skills, forma de trabajar, motivación…) (P14).
- **RF-9.6b** El catálogo NO DEBERÁ tener preguntas sobre edad, nacionalidad, salud, embarazo o planes de
  familia, estado civil, religión, ideología, afiliación sindical ni otras categorías del art. 9 del RGPD.
- **RF-9.6c** Claude prepara el borrador a partir de fuentes de recruiters; **Mar lo revisa y lo firma antes de
  construir el agente**. Cambiarlo después exige su firma.
- **RF-9.6d** El borrador se prepara con una **skill temporal de asesoría de recruiter** (`asesor-recruiter`,
  solo de desarrollo, no del producto) (P18). Su criterio: preguntas indirectas, de comportamiento y
  situacionales, con base en psicología y selección de personal, que saquen la máxima información sobre
  capacidades, valores y forma de trabajar sin preguntarlo de frente. Cumple RF-9.6b. Se borra al firmar el
  catálogo.

### Entrevista (RF-9.7)
- **RF-9.7** CUANDO termine el primer CV maestro, el `entrevistador` DEBERÁ preparar la **entrevista inicial**:
  **10-12 preguntas** elegidas del catálogo según el CV maestro, los huecos y los avisos, en tres partes:
  trayectoria y huecos · logros y cómo trabajas · qué buscas y por qué (P14). Es una llamada. SI no hay huecos
  ni avisos, la entrevista se hace igual, con las preguntas que haría un recruiter a ese perfil (P18).
- **RF-9.7i** La entrevista inicial DEBERÁ estar pensada para **20-30 minutos** y decirlo al empezar («Unos
  25 minutos. Puedes dejarla a medias y seguir luego.») (P18).
- **RF-9.7b** El agente DEBERÁ elegir preguntas **solo del catálogo** (por su número) y PODRÁ adaptar la
  redacción a los datos de la usuaria (fechas, empresas, puestos), sin cambiar lo que se pregunta.
- **RF-9.7c** Cada hueco (RF-9.1) DEBERÁ preguntarse de forma neutra, sin pedir el motivo, y con la opción
  «Prefiero no contarlo» (P14).
- **RF-9.7d** En la misma llamada, el `entrevistador` DEBERÁ añadir avisos con criterio de recruiter (logros
  flojos, incoherencias, lo que un recruiter preguntaría) (P2, P13). Cada aviso DEBERÁ citar el fragmento del CV
  maestro del que sale (RT-08) y no repetir uno de reglas.
- **RF-9.7e** CUANDO la usuaria suba otro CV fuente, el `entrevistador` DEBERÁ preparar un **seguimiento** de
  3 a 5 preguntas solo sobre lo nuevo (huecos, experiencias o avisos que no había). SI no hay nada nuevo, no
  hay seguimiento ni llamada.
- **RF-9.7f** Horma NUNCA DEBERÁ volver a hacer una pregunta del catálogo que la usuaria ya respondió o a la que
  dijo «Prefiero no contarlo».
- **RF-9.7g** No hay más tandas a petición: la entrevista inicial es una vez (P14). «Contar algo más» (RF-9.8d)
  cubre lo que quiera añadir.
- **RF-9.7h** Para cada experiencia sin logros (aviso de RF-9.2), el `entrevistador` PODRÁ usar una pregunta de
  logros del catálogo y añadirle **tareas y logros habituales de ese puesto** como ejemplos («En puestos de
  administración suele haber cierres mensuales o ahorro en proveedores. ¿Hiciste algo así? ¿Con qué
  resultado?») (P18). Los ejemplos son solo ayuda para recordar: NO DEBERÁN pasar al CV ni a la carta si la
  usuaria no los cuenta en su respuesta (RT-08).

### Respuestas (RF-9.8)
- **RF-9.8** Cada pregunta DEBERÁ poder responderse **por escrito** (hasta **5.000 caracteres**, unas 750
  palabras) o **por audio** (hasta **5 minutos**), o saltarse para luego (P4, P18). El texto siempre está
  disponible.
- **RF-9.8h** Junto a cada pregunta DEBERÁ verse la guía «Lo ideal: 1-2 minutos, como en una entrevista real.»
  Al llegar al tope, Horma DEBERÁ parar la grabación o no admitir más texto y decirlo: «Has llegado al máximo.
  En una entrevista real, intenta no pasar de 2 minutos.» (P18).
- **RF-9.8b** El audio DEBERÁ pasarse a texto con Whisper libre en el worker de Horma, sin enviarlo a terceros
  (P5). La usuaria DEBERÁ ver el texto y poder corregirlo antes de guardar. El audio NO DEBERÁ guardarse: se
  borra al transcribirlo, también si falla. Tope de **30 minutos de audio al día** por usuaria.
- **RF-9.8c** Las respuestas DEBERÁN guardarse aparte del perfil, por usuaria (RLS), con origen «entrevista» y
  la pregunta a la que responden (P15). No crean versión del perfil ni cambian el CV maestro. Se pueden editar
  y borrar en cualquier momento.
- **RF-9.8d** «Contar algo más» DEBERÁ estar siempre en «Tu entrevista»: la usuaria escribe o dicta, por su
  cuenta, un logro, un proyecto o algo de su forma de trabajar. Se guarda como una respuesta más. Sin modelo.
- **RF-9.8e** Al guardar una respuesta, Horma DEBERÁ quitar los datos del art. 9, la edad y la nacionalidad
  (como `quitar_sensibles` en el perfil) y avisar: «Hemos quitado un dato personal que Horma no guarda.»
- **RF-9.8f** Las respuestas son texto no fiable: las instrucciones que contengan se registran y no se
  ejecutan (RT-07).
- **RF-9.8g** Las preguntas de datos del perfil (RF-2.3, RF-2.9b, RF-2.9c) siguen como hoy: su respuesta
  actualiza el perfil y crea una versión nueva (RF-2.4).

### Valoración para entrenar (RF-9.9)
- **RF-9.9** CUANDO la usuaria termine la entrevista inicial o un seguimiento, el `valorador_entrevista`
  DEBERÁ dar, en una llamada, una valoración corta de cada respuesta: qué funciona y cómo mejorarla
  (situación, acción, resultado), en segunda persona y en 2-3 frases (P16).
- **RF-9.9d** SI una respuesta pasa de unas **300 palabras** (unos 2 minutos hablando), la valoración
  DEBERÁ recomendar acortarla para una entrevista real y decir qué dejar (P18).
- **RF-9.9b** La valoración NO DEBERÁ juzgar a la persona ni mencionar rasgos personales (RT-09): valora la
  respuesta como respuesta de entrevista.
- **RF-9.9c** La usuaria DEBERÁ poder reescribir la respuesta desde su valoración; la nueva sustituye a la
  anterior. Reescribir no pide otra valoración.

### Las respuestas en CV, carta y estilo (RF-9.10)
- **RF-9.10** `redactor_cv` y `redactor_carta` DEBERÁN recibir las respuestas de la entrevista como fuente y
  elegir, según la oferta, cuáles usar: soft skills, logros, forma de trabajar y motivación (P15).
- **RF-9.10b** Cada frase que salga de una respuesta DEBERÁ citarla como origen «entrevista», y
  `verificar_trazabilidad` y el juez DEBERÁN aceptarla como fuente válida. Lo que no está en el CV maestro ni
  en una respuesta sigue sin poder escribirse.
- **RF-9.10c** Una respuesta «Prefiero no contarlo» o borrada NO DEBERÁ usarse.
- **RF-9.10d** `analizador_estilo` DEBERÁ recibir las respuestas como documentos «entrevista» (P7): de ellas
  salen la personalidad y las expresiones; el registro (formal o cercano) sale de CV y cartas.
- **RF-9.10e** CUANDO termine la entrevista inicial, Horma DEBERÁ reanalizar el estilo SI la usuaria no ha
  editado la guía; SI la editó, «Tu estilo» DEBERÁ ofrecer «Actualizar mi estilo con la entrevista», que avisa
  de que sustituye la guía.
- **RF-9.10f** `redactor_cv` DEBERÁ respetar la elección de longitud de RF-9.2d: con «Mantener la longitud»
  conserva todas las experiencias; con «Que Horma lo sintetice» elige las que encajan con la oferta.

### «Tu entrevista» en Perfil (RF-9.11)
- **RF-9.11** «Tu entrevista» DEBERÁ sustituir al bloque 3 de RF-9.5 (P8), con el número de preguntas sin
  responder en el título; abierto CUANDO haya alguna. Reúne, en este orden: datos que faltan (RF-2.3), avisos
  (RF-9.2, RF-9.7d) y las preguntas de la entrevista por partes, con su avance («4 de 11»). Una a una; se puede
  dejar a medias y seguir luego.
- **RF-9.11b** Mientras Horma prepara la entrevista, transcribe un audio o valora, DEBERÁ verse la barra de
  avance o de espera de la fase 8 (RF-8.7).
- **RF-9.11c** El control de audio («Grabar», «Parar», tiempo grabado y tiempo restante) es un componente nuevo: DEBERÁ añadirse
  antes a la guía (RF-6.9), usarse con teclado y no depender solo del color (RF-6.7e).

## Criterios de aceptación (9b)
- La entrevista inicial tiene 10-12 preguntas, todas con un número del catálogo; ninguna repite una respondida.
  Subir otro CV sin nada nuevo no hace ninguna llamada. Un CV sin huecos ni avisos también recibe entrevista.
- Una experiencia sin logros recibe una pregunta con logros habituales del puesto como ejemplo; si la usuaria
  no los cuenta, no aparecen en el CV ni en la carta.
- Una respuesta de más de 300 palabras recibe en su valoración la recomendación de acortarla.
- Una grabación se para sola a los 5 minutos y un texto no admite más de 5.000 caracteres, con el aviso de
  RF-9.8h.
- El entrevistador añade al menos un aviso propio, citado, a un CV con logros flojos.
- Una respuesta por audio se transcribe, se corrige y se guarda; el audio no queda en ningún sitio. Al minuto
  31 del día, el audio se desactiva con un aviso y el texto sigue disponible.
- Una respuesta que menciona una enfermedad se guarda sin ese dato y con el aviso de RF-9.8e.
- Al terminar, cada respuesta tiene su valoración y se puede reescribir.
- Una carta generada usa una respuesta de la entrevista que encaja con la oferta, y la cita como origen.
- La guía de estilo, sin editar, se reanaliza al terminar; editada, sale el botón.
- Evals de `entrevistador`, `valorador_entrevista`, `estilo` y `cv` en umbral.
- Todo comprobado a 1280 y 390 px, en claro y en oscuro (RF-6.4b).

---

## Fuera de alcance
- Accesibilidad específica para personas sordas o ciegas en la entrevista (P4).
- Entrevista en otros idiomas oficiales de España (P4).
- Simulacro de entrevista para una oferta concreta (P16).
- Entrevista por llamada de voz en vivo (P18): idea futura; costaría varios euros por sesión frente a céntimos.
- Más tandas de preguntas a petición (P14).
- Revisar cómo el extractor asigna la familia a cada oferta (P10).
- Descargar el CV maestro (P12).

## Supuestos
- Whisper libre (`faster-whisper`, modelo pequeño) entiende bien el castellano y cabe en el worker (~0,5 GB);
  tarda unos segundos por respuesta en CPU. Se mide en el plan de 9b.
- Coste por usuaria (9b): entrevista inicial ~0,03 USD, valoración ~0,03 USD y cada seguimiento ~0,02 USD.
  Las respuestas alargan algo las llamadas de los redactores. En el peor caso (12 respuestas al tope de
  RF-9.8, unas 9.000 palabras), la valoración subiría a ~0,10 USD. Es una estimación; se mide con las evals.
- Se habla a unas 130-150 palabras por minuto: 2 minutos son unas 300 palabras y 5 minutos, unas 700.
- La voz es un dato personal, pero aquí no es biométrico (no se usa para identificar) y no se guarda.
