---
type: clarifications
title: correcciones-profesor — Aclaraciones
description: Preguntas abiertas de la fase 5 (correcciones del profesor del 17-nov) resueltas con la persona antes de escribir la spec.
tags: [clarify, perfil, cv-maestro, ofertas, ingesta, condiciones, validacion-cv]
status: active
sources: [../system.md, ../constitution.md, ../002-perfil-recomendacion/spec.md, ../004-langgraph-salida/spec.md]
generated: { by: claude-code, at: 2026-11-17 }
verified: { by: human, at: 2026-11-17 }
stale_after: null
---

# correcciones-profesor — Aclaraciones

## Punto de partida
Seis áreas, en este orden: (4) Perfil como fuente de verdad, (5) «Condiciones» en Recomendadas,
(6 + 3) ofertas privadas e ingesta por URL, (2) validar los CV generados, (1) nuevas fuentes.

Comprobado en el código (17-nov):
- Editar el perfil crea una versión nueva, pero copia `cv_maestro` sin tocarlo
  (`horma/web/services/perfil.py`). Los CV base leen el perfil editado; el redactor del CV, el de la
  carta y el juez solo leen `cv_maestro` y el CV base (`horma/flows/candidatura.py`), y la trazabilidad
  se comprueba contra esas dos fuentes. Lo editado no llega al CV adaptado.
- Una oferta pegada entra en el catálogo común, sin dueña (todas la ven en Ofertas). Solo sale en
  Recomendadas si pasa el filtro de Preferencias, y no tiene nota hasta que se pulsa «Recomendar».
  Hipótesis del «limbo»; se confirma reproduciéndolo.

## Preguntas y respuestas

### Perfil
- P1: ¿Cómo manda lo editado en la web? → R: **se regenera el `cv_maestro` con código a partir del
  perfil** en cada edición. Una sola fuente de verdad: lo borrado desaparece y la trazabilidad sigue
  funcionando.
- P2: ¿Qué pasa con lo que el maestro tiene fuera del perfil (proyectos, certificaciones…)? → R: **se
  amplía el perfil** con secciones editables (proyectos, certificaciones, otros) que rellena el
  extractor. Implica tocar el esquema, la pantalla y los evals del extractor.
- P3: ¿Qué CV se modifica al editar? → R: los CV subidos nunca (son el original); el maestro se
  regenera; **los CV base quedan desfasados con aviso de qué cambió y un botón «regenerar» por CV**
  (la versión anterior va al historial). Nada se regenera ni se gasta solo.
- P4: ¿Y las candidaturas en borrador preparadas con la versión anterior? → R: **aviso «preparada con
  una versión anterior de tu perfil» y botón para rehacerla**; se puede aprobar igualmente.

- P14: (pregunta de Mar al leer la spec) ¿Cuántos CV maestros hay? ¿Uno por sector? → R: **uno por
  usuaria** (el almacén con todo) y **un CV base por sector**; uno por sector obligaría a corregir
  cada dato en varios sitios. Al editar un dato, solo quedan desfasados los CV base cuya traza lo usa.
  Experiencia de otro sector en un CV base: **decide la usuaria** (completa, condensada en una línea u
  oculta); por defecto, condensada, para no dejar huecos en las fechas.

### Estilo de redacción de la usuaria
- P12: (petición de Mar tras leer la spec, 17-nov) → R: **un agente nuevo, `analizador_estilo`, se
  fija en cómo escribe la usuaria**, sobre todo en los CV y las cartas que escribió ella misma, y los
  CV y cartas que redacta Horma siguen ese estilo. Complementa a P1: el maestro regenerado con código
  pierde el estilo; este agente lo recupera al redactar.
  **Supuestos que Mar revisa al leer** (no preguntados uno a uno):
  - «Hecha a mano» = **escrita por ella** (no plantilla ni generada por otra herramienta), no un papel
    escaneado. Al subir un documento marca «Lo escribí yo»; esos pesan más.
  - Se pueden **subir cartas de presentación** suyas (hoy solo CV), solo como muestra de estilo: no
    alimentan el perfil.
  - Sale una **guía de estilo** breve y editable en el perfil: registro (formal o cercano), persona
    (primera o impersonal), longitud de frase, forma de las viñetas, verbos y expresiones que usa y
    lo que evita. Cada rasgo con su cita literal de origen (RT-08). Nunca rasgos personales,
    edad ni nada del art. 9 (RT-09).
  - La usan el `redactor_cv` y el `redactor_carta`; el estilo nunca puede añadir hechos. El juez no
    cambia por esto.
  - ~~Una llamada al modelo cada vez que cambian sus documentos subidos.~~ Corregido por Mar
    (17-nov): **se analiza una sola vez**; después, solo si ella lo pide en su configuración
    («Volver a analizar mi estilo»), para no gastar sin necesidad.

- P13: (petición de Mar, 17-nov) Que los CV y las cartas no «suenen a IA» ante quien selecciona. → R:
  **lo hace el mismo `juez_candidatura`**, sin agente nuevo (no suma llamadas). Matiz acordado: los
  detectores de IA no son fiables (falsos positivos frecuentes), así que no se promete «pasar un
  detector» ni se envían los documentos a uno comercial (tercero + RGPD). Se mide lo que sí delata
  un texto de IA: muletillas y frases genéricas (lista con código) y frases que no siguen la guía de
  estilo (juez). Se corrige en la vuelta única.

### Recomendadas: «Condiciones»
- P5: ¿Cómo se explica la columna «Condiciones» (bajo/medio/alto de `evaluar_condiciones`)? → R: **se
  quita de la pantalla por ahora**. Integrar las condiciones en la nota de compatibilidad queda
  anotado como mejora futura (`docs/mejoras-futuras.md`); no entra en esta fase.

### Ofertas propias (pegadas o por URL)
- P6: ¿Dónde se ve una oferta que añade la usuaria? → R: **es privada** (solo la ve quien la añade) y
  se **analiza y puntúa al momento** (una llamada al `matcher`). Sale en **Recomendadas con la marca
  «Añadida por ti · analizada el <fecha>»**, aunque no pase los filtros de Preferencias, y también en
  Ofertas. El catálogo que llega de las fuentes sigue siendo común. Si dos usuarias añaden la misma
  oferta, cada una tiene su copia. Supuesto: el formulario pasa a una pestaña propia, «Añadir
  oferta», con texto o URL.
- P17: (aclaración de Mar, 17-nov) → **TODAS** las ofertas pegadas o por URL pasan a Recomendadas con
  la evaluación hecha, sin excepción: también las repetidas y las que el auditor marque como fantasma
  o fraude (con su aviso). Sin perfil, se puntúan en cuanto lo haya.
- P18: (prueba manual 3.4, 19-nov) Pegar la misma oferta otra vez la duplicaba y la puntuaba distinto
  → R: **no se duplica**: misma usuaria + misma huella de texto (y la previa no falló) devuelve la
  existente, sin reprocesar ni repuntuar. Matiza P17: «también las repetidas» deja de aplicar.

- P19: (revisión de usabilidad de la fase 6, 20-nov) El aviso «Podría ser una oferta fantasma» en una
  oferta que la usuaria pegó ella misma es ruido → R: **no se avisa de «fantasma» en las propias; el aviso de
  fraude se mantiene**. Matiza P17 y RF-5.3e.

### CI
- P16: (petición de Mar, 17-nov) ¿Aparcar `evals-reales`? → R: **sí, hasta lanzar al público**. Solo
  se lanzan a mano y con su OK; los evals en simulado siguen en cada push y siguen bloqueando. Deja en
  pausa parte de RF-4.4c (fase 4).
- P7: ¿Con qué se lee la URL? → R: **Apify, actor *RAG Web Browser*** (Playwright en su nube; Apify
  Technologies s.r.o., Praga). Elegido frente a ScrapingBee (~228 $/año, el más sólido en RGPD) y al
  lector propio con Playwright, porque a nuestro volumen sale a 0 $ (dentro de los 5 $/mes gratis;
  margen prudente de 1.000-1.500 páginas/mes) y es compatible con un despliegue en Vercel. Los
  portales cuyas condiciones prohíben el scrapeo (LinkedIn, Indeed, Glassdoor, InfoJobs) quedan
  vetados; no se usan proxies residenciales ni el «Unblocker»; si la página no se puede leer, se pide
  pegar el texto.
  **Por confirmar antes de construir** (17-nov sin fuente oficial): dónde guarda los datos, cuánto
  tiempo, lista de subencargados (solo con NDA) y que su DPA (art. 28 en sus condiciones) cubre el
  uso. Si no se confirma, se cambia a ScrapingBee (el cliente es intercambiable). Va a
  `docs/revision-lineas-rojas.md` (sección «Encargados del tratamiento») como encargado del tratamiento. El lector propio queda como mejora futura
  prioritaria.

- P15: (pregunta de Mar al leer la spec) ¿Y un agente con Playwright por usuaria, para uso personal,
  para no quedarnos sin ofertas? → R: **no**: lo ejecutaría el servidor de Horma, que sería quien
  rastrea esos portales contra sus condiciones (riesgo de bloqueo y reclamación; la constitución
  prohíbe LinkedIn e Indeed como fuentes). Para los vetados, **pegar el texto**. El botón del
  navegador «Enviar a Horma» queda en mejoras futuras.

### Validar los CV generados
- P8: ¿Cómo se validan longitud y coherencia? → R: **longitud, secciones y fechas con código;
  coherencia ampliando `juez_candidatura`** con tipos nuevos. Se aplica al CV adaptado y al CV base.
  Sin agente nuevo; se amplían los evals del juez.
- P10: ¿Qué longitud es válida? → R: **1-2 páginas**, medidas por código en palabras (unas 250-1.000).
  Si se pasa, el redactor recorta en la vuelta única.

### Nuevas fuentes
- P9: ¿Qué fuentes se añaden? → R: **Claude propone una lista** (cobertura en España, condiciones de
  uso, coste, esfuerzo) y Mar elige.
- P11: ¿Cuáles entran? → R: **todas las propuestas**: activar Adzuna (ya configurada); añadir
  Himalayas, Jobicy y Remotive (condiciones claras, solo configuración); **InfoJobs API** (activación
  bloqueada hasta tener sus condiciones por escrito: el enlace de su portal está roto); y
  **Greenhouse/Lever** para una lista corta de empresas que dará Mar. Fuera por ahora: Jooble,
  Careerjet (solo extracto, sin permiso claro para guardar), EURES, SEPE, Tecnoempleo, Manfred y
  Welcome to the Jungle (sin API abierta).
  Condiciones que la spec debe recoger: enlazar siempre a la oferta original y citar la fuente; no
  exponer el catálogo hacia fuera ni como `JobPosting` (Remotive y Himalayas lo prohíben); borrar las
  caducadas (Himalayas); respetar los límites de peticiones (Remotive: ~4 al día).
