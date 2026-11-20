---
type: spec
title: correcciones-profesor — Spec funcional
description: Requisitos funcionales de la fase 5 (correcciones del profesor del 17-nov-2026): el perfil editado como fuente de verdad, fuera la columna «Condiciones», ofertas propias privadas por texto o URL, validación de longitud y coherencia de los CV generados, fuentes de ofertas nuevas y un agente que capta el estilo de redacción de la usuaria, en notación EARS.
tags: [spec, perfil, cv-maestro, ofertas, ingesta, scrapeo, validacion-cv, fuentes, estilo]
status: active
sources: [./clarifications.md, ../system.md, ../constitution.md, ../002-perfil-recomendacion/spec.md, ../003-candidatura/spec.md, ../004-langgraph-salida/spec.md]
generated: { by: claude-code, at: 2026-11-17 }
verified: { by: human, at: 2026-11-17 }
stale_after: null
---

# correcciones-profesor — Especificación

## Contexto
El profesor revisó Horma el 17-nov-2026. Esta fase corrige lo que señaló, más dos peticiones de Mar
(bloques 6 y 7), en siete bloques:

1. **Perfil:** lo que la usuaria edita en la web manda sobre los CV que subió y llega a todo lo que
   se redacta.
2. **Recomendadas:** sale la columna «Condiciones», que no se entendía.
3. **Ofertas propias:** la usuaria añade una oferta pegando el texto o la URL; es privada, se analiza
   y se puntúa al momento y aparece en Recomendadas. Se acaba el «limbo» de las ofertas pegadas.
4. **Validar los CV generados:** longitud y coherencia, además de la fidelidad que ya se comprueba.
5. **Fuentes nuevas** de ofertas para el catálogo común.

6. **Estilo de redacción:** Horma escribe los CV y las cartas como escribe la usuaria.
7. **Que no suene a IA:** el juez señala muletillas y frases genéricas para corregirlas.

**Entra un agente nuevo, `analizador_estilo`** (P12). Cambian el `extractor_perfil` (secciones
nuevas), el `juez_candidatura` (tipos de problema nuevos) y los dos redactores (reciben la guía de
estilo); el resto reutiliza lo que hay.

Los requisitos transversales (RT-xx) están en [system.md](../system.md) y las respuestas del Clarify
en [clarifications.md](./clarifications.md) (se citan como P1…P11).

## Requisitos (EARS)

### Perfil como fuente de verdad (RF-5.1)
- **RF-5.1** CUANDO la usuaria cambie, añada o quite un dato del perfil (o responda una pregunta
  pendiente), el sistema DEBERÁ regenerar el CV maestro de esa versión con código, a partir del perfil
  editado, sin llamar al modelo (P1). Lo que ella quite NO DEBERÁ seguir en el CV maestro.
- **RF-5.1b** Los redactores del CV y de la carta, el juez y la comprobación de trazabilidad DEBERÁN
  seguir usando el CV maestro, que ya refleja lo editado. Un dato que la usuaria escribió DEBERÁ
  contar como dato con origen («usuaria»), nunca como frase sin origen (RT-08).
- **RF-5.1c** El perfil DEBERÁ tener, además de lo actual, las secciones **proyectos**,
  **certificaciones** y **otros** (cada elemento con su origen), que el extractor rellena desde los
  CV y la usuaria puede editar en la web (P2). El CV maestro regenerado DEBERÁ incluirlas. Cada
  sección DEBERÁ mostrar una descripción breve con ejemplos de lo que cabe en ella, p. ej.:
  **Proyectos** «Web de reservas para el restaurante familiar (2024)», «TFG: app de turnos»;
  **Certificaciones** «Manipulador de alimentos», «Carné de carretillero», «Cambridge B2 First»;
  **Otros** «Voluntariado en el banco de alimentos», «Carné de conducir B», «Disponibilidad para
  viajar».
- **RF-5.1d** Los CV subidos NUNCA DEBERÁN modificarse: son el original. La pantalla del perfil
  DEBERÁ decir en llano qué cambia al editar: «Lo que edites aquí manda sobre tus CV subidos y se usa
  para redactar todos tus CV y cartas».
- **RF-5.1e** CUANDO el perfil cambie de versión, solo los CV base cuya traza use un dato que cambió
  DEBERÁN mostrarse como desfasados (p. ej. editar una experiencia de hostelería no toca el CV base de
  construcción que no la usa), con qué cambió y un botón «Regenerar» por CV. NO DEBERÁN regenerarse
  solos. Al regenerar, la versión anterior DEBERÁ quedar en su historial (P3, P14).
- **RF-5.1g** Hay **un solo CV maestro por usuaria** (todo lo suyo) y **un CV base por sector** que
  elige qué destacar (P14). En un CV base, la experiencia de otro sector DEBERÁ ir **condensada en una
  línea** (puesto · empresa · fechas) por defecto, para no dejar huecos en las fechas. En cada CV base,
  la usuaria DEBERÁ poder marcar cada experiencia como «completa», «condensada» u «oculta»; al
  regenerar, se respeta lo que marcó.
- **RF-5.1f** MIENTRAS una candidatura en borrador esté preparada con una versión anterior del perfil,
  DEBERÁ mostrar el aviso «Preparada con una versión anterior de tu perfil» y un botón para volver a
  prepararla. La usuaria DEBERÁ poder aprobarla igualmente (P4).

### Recomendadas: fuera «Condiciones» (RF-5.2)
- **RF-5.2** La lista de Recomendadas NO DEBERÁ mostrar la columna «Condiciones» (P5). El cálculo puede
  seguir existiendo; integrarlo en la nota queda como mejora futura.

### Ofertas propias: texto o URL (RF-5.3)
- **RF-5.3** Antes de cambiar nada, DEBERÁ reproducirse el «limbo» de las ofertas pegadas con una
  prueba que hoy falle: una oferta pegada por la usuaria no llega a Recomendadas ni permite preparar
  una candidatura.
- **RF-5.3b** La web DEBERÁ tener una pestaña propia, «Añadir oferta», donde la usuaria pega el texto
  de una oferta o su URL. El formulario sale de la página del catálogo.
- **RF-5.3c** Una oferta añadida por una usuaria DEBERÁ ser privada: solo su dueña la DEBERÁ ver (en
  Ofertas, en Recomendadas y en cualquier API). Lo DEBERÁ garantizar la base de datos (RLS), no solo
  la consulta. Las ofertas que llegan de las fuentes siguen en el catálogo común. Si dos usuarias
  añaden la misma oferta, cada una DEBERÁ tener la suya (P6).
- **RF-5.3d** CUANDO la usuaria añada una oferta, el sistema DEBERÁ procesarla como cualquier otra
  (extracción y auditoría) y, después, puntuarla con el `matcher` para la versión vigente de su perfil,
  sin esperar a «Recomendar». Cada paso DEBERÁ tener su tope de coste (RT-14). SI la usuaria aún no
  tiene perfil, ENTONCES DEBERÁ puntuarse en cuanto lo tenga, sin que ella haga nada.
- **RF-5.3e** **TODAS** las ofertas que la usuaria añade, por texto o por URL, DEBERÁN aparecer en
  Recomendadas con su evaluación hecha y la marca «Añadida por ti · analizada el <fecha>», sin
  excepción (P17): aunque no pasen los filtros de Preferencias ni el rango de nota y aunque el auditor
  las marque como fantasma o con señales de fraude. Con señales de fraude, DEBERÁ verse el aviso del
  auditor; con «fantasma», NO DEBERÁ avisarse, porque la ha pegado ella (P19).
  SI la usuaria pega otra vez un texto igual (misma huella) a una oferta suya que no falló, ENTONCES
  el sistema NO DEBERÁ crear otra ni volver a procesarla ni puntuarla: devuelve la que ya tiene (P18). Desde ahí DEBERÁ poder prepararse la candidatura como con cualquier otra.
  Solo queda fuera una URL que no se pudo leer, porque no hay oferta: se pide pegar el texto.
- **RF-5.3f** CUANDO la usuaria dé una URL, el sistema DEBERÁ leer la página con el proveedor elegido
  (Apify, actor *RAG Web Browser*, P7) y procesar el texto obtenido. La URL DEBERÁ guardarse con la
  oferta.
- **RF-5.3g** El sistema NO DEBERÁ leer URL de portales cuyas condiciones prohíben el scrapeo
  (LinkedIn, Indeed, Glassdoor, InfoJobs), según una lista configurable, y NO DEBERÁ activar proxies
  residenciales ni servicios para saltar bloqueos. En ese caso, o SI la página no se puede leer,
  ENTONCES DEBERÁ decir el motivo en llano y pedir que pegue el texto.
- **RF-5.3h** El sistema DEBERÁ aceptar solo URL `https` con un dominio público: NO DEBERÁ aceptar IP
  literales, direcciones privadas o locales ni credenciales en la URL. El texto leído DEBERÁ tener un
  tamaño máximo y tratarse como no fiable (RT-07).
- **RF-5.3i** Antes de construir RF-5.3f DEBERÁ confirmarse por escrito, con fuente oficial, dónde
  guarda Apify los datos, durante cuánto tiempo, sus subencargados y que su DPA cubre este uso. SI no
  se confirma, ENTONCES DEBERÁ usarse ScrapingBee, sin cambiar nada más que el cliente. El proveedor
  DEBERÁ figurar como encargado del tratamiento en `docs/revision-lineas-rojas.md` (sección «Encargados del tratamiento»).
- **RF-5.3j** Leer una URL DEBERÁ tener un límite de ritmo por usuaria y responder 429 al pasarse,
  como el resto de entradas (RF-4.6d).

### Validar los CV generados (RF-5.4)
- **RF-5.4** El sistema DEBERÁ comprobar con código, en cada CV adaptado y en cada CV base, que: la
  longitud está entre unas 250 y 1.000 palabras (1-2 páginas, P10; con un perfil corto, el mínimo baja al 60 % de las palabras del maestro); tiene las secciones obligatorias
  (al menos Experiencia o Formación); y sus fechas son válidas y en orden (el fin no es anterior al
  inicio).
- **RF-5.4b** El `juez_candidatura` DEBERÁ señalar, además de lo actual, problemas de **coherencia**:
  fechas que se solapan o contradicen sin explicación, un resumen o titular que no casa con la
  experiencia, y secciones repetidas o desordenadas. Igual que ahora, señala y no reescribe.
- **RF-5.4c** Los errores de RF-5.4 y RF-5.4b DEBERÁN entrar en la vuelta única que ya existe: el
  redactor recorta o corrige lo que se le señala. Lo que siga mal tras la vuelta DEBERÁ mostrarse como
  aviso en llano.
- **RF-5.4d** Los CV base DEBERÁN pasar también por el juez y por la comprobación de RF-5.4 antes de
  guardarse (P8). Esto suma una llamada al modelo por CV base.
- **RF-5.4e** Los evals del juez (`evals/cv/`) y del CV base (`evals/cv-base/`) DEBERÁN tener casos de
  CV demasiado largos, demasiado cortos, con fechas incoherentes y con un resumen que no casa, con su
  umbral en `evals/umbrales.json`.

### Fuentes de ofertas nuevas (RF-5.5)
- **RF-5.5** DEBERÁN entrar en el catálogo común, por configuración y pasando la calificación de
  fuentes: Adzuna (activar), Himalayas, Jobicy y Remotive (P11).
- **RF-5.5b** InfoJobs (API oficial) DEBERÁ configurarse, pero NO DEBERÁ activarse hasta tener sus
  condiciones de uso por escrito. Necesita una segunda llamada por oferta para traer la descripción.
- **RF-5.5c** Greenhouse y Lever DEBERÁN poder añadirse empresa a empresa (una fuente por empresa).
  Mar quiere **todas las empresas de Greenhouse** (metabuscador): Claude investiga cómo descubrirlas
  y qué permiten sus condiciones antes de ingerir (18-nov).
- **RF-5.5d** Cada oferta de una fuente DEBERÁ enlazar al original y citar la fuente. El catálogo NO
  DEBERÁ exponerse hacia fuera ni publicarse como `JobPosting`. Las ofertas caducadas DEBERÁN
  borrarse cuando la fuente lo exija (Himalayas), y DEBERÁN respetarse los límites de peticiones de
  cada fuente (Remotive: unas 4 al día).

### Estilo de redacción de la usuaria (RF-5.6)
- **RF-5.6** Al subir un documento, la usuaria DEBERÁ poder marcar «Lo escribí yo» y DEBERÁ poder subir,
  además de CV, **cartas de presentación** suyas. Las cartas solo DEBERÁN usarse como muestra de
  estilo: NO DEBERÁN alimentar el perfil (P12).
- **RF-5.6b** El agente `analizador_estilo` DEBERÁ leer los documentos de la usuaria (CV de clase
  «fuente» y cartas), dando prioridad a los marcados «Lo escribí yo», y devolver una **guía de estilo**:
  registro, persona gramatical, longitud de frase, forma de las viñetas, verbos y expresiones que
  usa y lo que evita. Cada rasgo DEBERÁ llevar su cita literal de origen (RT-08). Como todo agente, sin
  acceso a base de datos ni a disco (RT-01).
- **RF-5.6c** La guía NO DEBERÁ describir a la persona ni inferir edad, nacionalidad ni nada del
  art. 9 del RGPD (RT-09): describe cómo escribe, no cómo es. Las instrucciones que encuentre en los
  documentos DEBERÁN ir a `instrucciones_embebidas` (RT-07).
- **RF-5.6d** El sistema DEBERÁ calcular la guía **una sola vez**, la primera vez que haya documentos
  de la usuaria (una llamada al modelo, con tope de coste). Después NO DEBERÁ recalcularla sola, ni al
  subir documentos ni al editar el perfil: solo CUANDO la usuaria pulse «Volver a analizar mi estilo»
  en su configuración. La guía DEBERÁ verse en el perfil y la usuaria DEBERÁ poder editarla; lo que
  ella edite manda.
- **RF-5.6e** El `redactor_cv` y el `redactor_carta` DEBERÁN recibir la guía y seguirla. El estilo
  NUNCA DEBERÁ añadir hechos: la trazabilidad, los rasgos personales y el juez se comprueban igual que
  ahora. Sin guía (no hay documentos escritos por ella), DEBERÁN redactar como hasta ahora.
- **RF-5.6f** `analizador_estilo` DEBERÁ tener su set de evals (`evals/estilo/`) con umbral: guías con
  cita de origen, ningún rasgo personal (100 %) y documentos con instrucciones embebidas sin efecto
  (100 %). Los sets `cv` (CV y carta) DEBERÁN incluir casos con guía de estilo.

### Que no suene a IA (RF-5.7)
- **RF-5.7** El sistema DEBERÁ buscar con código, en cada CV y carta generados o editados por la usuaria, una lista versionada
  de muletillas y frases genéricas típicas de texto de IA (p. ej. «en el dinámico mundo de»,
  «apasionada por», «sinergias», «no solo… sino también») y señalarlas como error (P13). Al editar un borrador, la misma comprobación y la de RF-5.4 se repiten con código y salen como avisos en llano (los avisos no bloquean Aprobar).
- **RF-5.7b** El `juez_candidatura` DEBERÁ señalar con un tipo nuevo, `suena_a_ia`, las frases
  genéricas o artificiales que la lista no recoja y, si hay guía de estilo (RF-5.6), las que no la
  siguen. Igual que ahora, señala y no reescribe; no añade llamadas al modelo.
- **RF-5.7c** Lo señalado DEBERÁ entrar en la vuelta única. Lo que siga tras la vuelta DEBERÁ
  mostrarse como aviso en llano.
- **RF-5.7d** El sistema NO DEBERÁ enviar los documentos a detectores de IA externos ni prometer que
  «pasan» un detector: estos no son fiables.
- **RF-5.7e** Los evals del juez (`evals/cv/`) DEBERÁN incluir casos con muletillas de IA y con frases
  fuera de estilo, con su umbral.

### Evals con el modelo real, aparcados (RF-5.8)
- **RF-5.8** Hasta el lanzamiento al público, el job `evals-reales` NO DEBERÁ correr solo en los PR:
  solo DEBERÁ lanzarse a mano (`workflow_dispatch`) y con el OK de Mar (P16). Los evals en simulado
  DEBERÁN seguir corriendo en cada push y bloqueando el merge. Esto deja en pausa la parte de RF-4.4c
  que corre el modelo real en cada PR. Antes del lanzamiento DEBERÁ reactivarse.

## Criterios de aceptación (puerta de salida)
- [ ] Editar o borrar una experiencia cambia el CV maestro, y un CV adaptado nuevo usa el dato
      editado sin errores de trazabilidad; lo borrado no aparece (test).
- [ ] El extractor rellena proyectos, certificaciones y otros, y su set de evals (`evals/perfil/`)
      sigue en umbral.
- [ ] Tras editar el perfil, los CV base y los borradores de candidatura muestran su aviso y su botón,
      y nada se regenera solo (test).
- [ ] Recomendadas ya no muestra «Condiciones».
- [ ] La prueba del «limbo» (RF-5.3) falla antes y pasa después.
- [ ] Una oferta añadida por Ana no la ve Berta ni por la web ni por la API (test de RLS).
- [ ] Una oferta pegada o por URL sale puntuada en Recomendadas con su marca, aunque no pase los
      filtros, y permite preparar la candidatura.
- [ ] Una URL de LinkedIn, una IP privada o una URL `http` se rechazan con un mensaje en llano (test).
- [ ] RGPD de Apify confirmado y anotado en `docs/revision-lineas-rojas.md` (sección «Encargados del tratamiento») (o cambiado a ScrapingBee).
- [ ] Un CV de más de 1.000 palabras o con fechas incoherentes se señala y se corrige en la vuelta
      única; los sets `cv` y `cv-base` siguen en umbral con el modelo real.
- [ ] Adzuna, Himalayas, Jobicy y Remotive calificadas y activas; InfoJobs configurada e inactiva.
- [ ] Con una carta escrita por ella subida, la guía de estilo aparece en el perfil con citas, y un CV
      y una carta nuevos la siguen sin añadir hechos; `horma eval correr estilo` en umbral.
- [ ] Un CV con «apasionada por» o una frase genérica se señala y se corrige en la vuelta única
      (test y eval `cv`).

## Riesgos
- **Regenerar el CV maestro con código:** pierde el estilo del texto extraído por el modelo. Lo
  compensa la guía de estilo al redactar (RF-5.6e).
- **Agente nuevo:** más coste (una llamada al empezar y otra cada vez que ella pida reanalizar) y otro
  set de evals que mantener; el estilo podría empujar al redactor a inventar, por eso la trazabilidad no cambia.
- **Coste:** un juez más por CV base y una llamada al `matcher` por oferta añadida (unos 0,003 USD).
  Apify sale a 0 $ dentro de los 5 $ al mes gratis (unas 1.000-1.500 páginas al mes, con margen
  prudente).
- **RGPD:** Apify es un encargado del tratamiento nuevo, con puntos sin confirmar (RF-5.3i).
- **Seguridad:** el servidor pide páginas a URL que da la usuaria (RF-5.3h, RF-5.3j).
- **Fuentes:** sus condiciones cambian; InfoJobs no tiene condiciones legibles.
- **Evals con el modelo real aparcados (RF-5.8):** sin ellos en cada PR, un cambio en un prompt puede
  empeorar la calidad sin que CI lo note. Se mitiga lanzándolos a mano al cerrar la fase (con OK de
  Mar) y reactivándolos antes del lanzamiento.

## Fuera de alcance
- Integrar las condiciones en la nota de compatibilidad (`docs/mejoras-futuras.md`, punto 3).
- Lector de URL propio en capas o con Playwright (`docs/mejoras-futuras.md`, punto 4).
- Leer los portales vetados desde el servidor, también «por usuaria» (P15). Botón del navegador
  «Enviar a Horma» (`docs/mejoras-futuras.md`, punto 5).
- Jooble, Careerjet, EURES, SEPE, Tecnoempleo, Manfred y Welcome to the Jungle.
- Puntuar automáticamente el catálogo común: «Recomendar» sigue siendo manual (RF-2.15c).
