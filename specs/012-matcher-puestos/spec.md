---
type: spec
title: matcher-puestos — Spec funcional
description: Requisitos en notación EARS de la spec 012 (paso 2 del PRD) — puestos sugeridos por niveles de evidencia, medidos antes de construir; nota del matcher fiable y estable; veredicto en palabras con citas comprobadas; condiciones fuera de la nota y correcciones que mandan en la lista de quien corrige.
tags: [spec, matcher, puestos, recomendacion, evals]
status: active
sources: [./clarifications.md, ../prd.md, ../system.md, ../002-perfil-recomendacion/spec.md, ../009-cv-maestro-entrevista/spec.md, ../010-simplificacion/spec.md]
generated: { by: claude-code, at: 2026-11-25 }
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
- **RF-12.4** El set de títulos de 9a (RF-9.3e) DEBERÁ repasarlo Mar en los pares sin unanimidad y en los que
  difieren del código, y ampliarse con unos 50 pares de sinónimos sin palabras en común. Después se vuelve a
  medir RF-9.3e. SI la cobertura baja de 0,90, ENTONCES se para y se propone a Mar la prueba de embeddings, solo
  para proponer candidatos (F4-D6), como cambio de esta spec.

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
- **RF-12.13** El eval DEBERÁ medir el orden (S7): en cada caso de orden, la mejor oferta esperada sale primera y
  ningún par con 20 o más puntos de diferencia esperada sale al revés.
- **RF-12.14** La nota esperada de un caso existente solo DEBERÁ cambiarse con el OK de Mar y con el motivo
  escrito en su `esperado.json` (S8).
- **RF-12.15** CUANDO pase la puerta, `recomendacion` DEBERÁ volver a correr con el modelo real en `evals-reales`
  de la CI.
- **RF-12.16** El `matcher` DEBERÁ medirse también con el modelo pequeño, con el mismo eval. SI pasa la puerta,
  ENTONCES Mar decide si se cambia (F1-E6) y la decisión se anota como D-NNN.

### D · Explicación fiable (PRD RF-007)
- **RF-12.17** Junto a la nota, Horma DEBERÁ enseñar un veredicto en palabras, puesto por código (F7-D5, S5):
  70-100 «Muy compatible», 50-69 «Compatible», 30-49 «Poco compatible» y 0-29 «No te la recomendamos».
- **RF-12.18** La explicación DEBERÁ empezar por lo que toca a su franja: 70-100, por qué te la recomendamos;
  50-69, por qué tienes opciones; 30-49, por qué no te la recomendamos, aunque puedes intentarlo; 0-29, por qué
  no te la recomendamos.
- **RF-12.19** `cita_perfil` y `cita_oferta` DEBERÁN ser fragmentos literales, y un verificador en código DEBERÁ
  comprobar que existen en la copia del perfil (RF-12.30) y en la oferta; lo que vaya en «/a» se enseña con
  `en_genero`. SI alguna no existe, ENTONCES se piden otra vez, una sola vez, solo esas ofertas. SI vuelve a
  fallar, ENTONCES la explicación se retira y la nota se conserva con el aviso «Sin explicación comprobada» (S6).
- **RF-12.20** La explicación NO DEBERÁ nombrar las instrucciones embebidas de una oferta, ni siquiera para
  decir que las ignora (NFR-03).
- **RF-12.21** Un revisor con el modelo pequeño, solo dentro del eval, DEBERÁ juzgar si cada explicación se apoya
  en sus citas. Umbral: 100 %.
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
- Una oferta que no publica el sueldo, con sueldo mínimo marcado, enseña «No dice el sueldo» y la misma nota.
- Corregir una nota de 75 a 40 reordena la lista y enseña el motivo; «Quitar mi nota» la devuelve a 75.
- Revisión de Mar sobre 20 recomendaciones.
- Pantallas comprobadas a 1280 y 390 px, en claro y en oscuro; suite verde.

## Riesgos
- **Los evals reales cuestan más de lo estimado** (el `cv` llegó a 2,7 USD frente a 0,5-1). Estimación y OK de
  Mar antes de cada gasto ([plan](./plan.md), Costes).
- **Familia mal asignada:** RF-12.9 depende de ella. Se mide en el set `puestos`; si falla, F4-D3, segundo paso.
- **Maquillar el eval:** cambiar notas esperadas para aprobar. Lo frena RF-12.14.
