---
type: spec
title: simplificacion — Spec funcional
description: Requisitos de la simplificación de Horma en notación EARS — recorrido de 4 pantallas y 4 clics, ocho conceptos, tres pestañas, candidatura sin CV base, «Tu CV completo» en PDF, bandeja «Por resolver», un agente por oferta, caché de la compatibilidad, presupuesto diario único, orden interno y las correcciones tras la prueba (S7: avance en su pantalla, avisos agrupados, carta, PDF del CV, simetría y el repaso del 22-nov; S8: correcciones de la pasada del 22-nov; S10: subir varios documentos a la vez) — y la lista de requisitos anteriores que sustituye.
tags: [spec, simplificacion, ux, frontend, costes, arquitectura, agentes]
status: active
sources: [./clarifications.md, ../system.md, ../constitution.md, ../002-perfil-recomendacion/spec.md, ../003-candidatura/spec.md, ../005-correcciones-profesor/spec.md, ../006-rediseno-2c/spec.md, ../007-ajustes-pantalla/spec.md, ../008-portada-ofertas/spec.md, ../009-cv-maestro-entrevista/spec.md]
generated: { by: claude-code, at: 2026-11-21 }
verified: { by: human, at: 2026-11-23 }  # S7 firmada el 21-nov; S8 (RF-10.14 a 10.14r) y S9 (RF-10.15 a 10.15e) firmadas el 22-nov; RF-5.3i, 10.4e, 10.6i, 10.8c, 10.16 y 10.17 pedidos por Mar en la prueba del 22-nov; S10 (RF-10.18 a 10.18i) firmada el 23-nov
stale_after: null
---

# simplificacion — Especificación

## Contexto
Horma hace lo mismo con menos: menos pantallas, menos clics, menos palabras y menos llamadas al modelo.
Ninguna línea roja cambia. Las respuestas del Clarify están en [clarifications.md](./clarifications.md) y se
citan como P1…P12.

Esta spec **sustituye** a los requisitos anteriores que se listan en «Requisitos que sustituye». Las specs
002-009 no se reescriben: cada requisito sustituido lleva una línea que apunta aquí.

## Recorrido (una página)

| # | Pantalla | Qué hace la usuaria | Clics | Espera |
|---|---|---|---|---|
| 1 | Landing | «Continuar con Google» | 1 | Google |
| 2 | Perfil (vacío: solo «Sube tu CV») | Elige el archivo; se sube solo | 1 | **1.ª** «Estamos leyendo tu CV…» |
| 3 | Ofertas | Al abrirla, Horma puntúa sola (RF-8.5). «Preparar candidatura» | 1 | **2.ª** puntuar · **3.ª** preparar CV y carta |
| 4 | Candidatura | «Aprobar y descargar» | 1 | 2 PDF |

**4 pantallas · 4 clics · 3 esperas.** La puntuación no se lanza al acabar el CV (P5): empieza al abrir
Ofertas, que es adonde lleva Horma cuando el perfil está listo.

```
Landing ──Google──> Ofertas ◄──► Candidaturas ◄──► Perfil
                      │               │               ├─ Tu perfil (por secciones)
                      │               │               ├─ Subir archivo
                      │               │               ├─ Tu CV completo (ver · PDF)
                      │               │               ├─ Por resolver (con «Avisos»)
                      │               │               ├─ Documentos subidos
                      │               │               └─ Cómo escribes
                      ├─ Qué buscas (plegable)
                      ├─ + Añadir oferta (ventana)
                      └─ Preparar ──> Candidatura (detalle)
Admin (solo administradoras): Ingesta · Catálogo · Costes
```

## Requisitos (EARS)

### Entrada y menú (RF-10.1)
- **RF-10.1** CUANDO alguien sin sesión abra `/`, la landing DEBERÁ tener «Continuar con Google» como botón
  primario, arriba a la derecha y al final de la página, y llevar directamente a Google. `/entrar` NO DEBERÁ
  existir como pantalla: redirige a `/`.
- **RF-10.1b** «Cómo empezar» DEBERÁ tener tres pasos: «Entra con Google» · «Sube tu CV» · «Mira tus ofertas
  y prepara tu candidatura». No DEBERÁ mencionar el CV base.
- **RF-10.1c** Las pestañas de la usuaria DEBERÁN ser tres: **Ofertas · Candidaturas · Perfil**, más «Admin»
  para las administradoras (P3). En móvil, la rejilla se ajusta a tres (RF-6.3c).
- **RF-10.1d** CUANDO alguien con sesión abra `/` o vuelva de Google, Horma DEBERÁ llevarla a Ofertas; SI aún
  no tiene perfil, a Perfil. La marca «Horma» lleva a Ofertas.
- **RF-10.1e** Las direcciones antiguas DEBERÁN redirigir: `/recomendadas` → `/ofertas`; `/anadir-oferta` →
  `/ofertas` con la ventana «Añadir oferta» abierta; `/cv-base` → `/perfil`.

### Palabras (RF-10.2)
- **RF-10.2** La usuaria DEBERÁ ver solo estos ocho conceptos (P4):

  | Nombre | Qué es, en una línea | Sustituye a |
  |---|---|---|
  | **Tu perfil** | Lo que Horma sabe de ti. Lo que corrijas aquí manda. | Perfil, Mi perfil, Tus CV, versiones |
  | **Por resolver** | Lo que Horma te pide mirar: responder, corregir o «Dar por visto». | Preguntas pendientes, huecos, avisos |
  | **Tu CV completo** | Tu perfil escrito como CV. Se ve y se descarga; no se edita. | CV maestro, CV base |
  | **Qué buscas** | Los puestos y condiciones que quieres. | Preferencias, área, puestos, excluidos |
  | **Ofertas** | Las que encajan, con su compatibilidad (0-100) y su porqué. | Recomendadas, Añadir oferta, nota, puntuación |
  | **Candidatura** | Tu CV y tu carta para una oferta. Nada sale sin tu aprobación. | CV adaptado, carta, preparación |
  | **Cómo escribes** | Tu forma de redactar, que Horma imita. | Guía de estilo |
  | **Tu entrevista** | Preguntas de recruiter para conocerte mejor (fase 9b). | — |

- **RF-10.2b** «Compatibilidad» DEBERÁ ser la única palabra para el número 0-100; ningún texto de la usuaria
  DEBERÁ decir «nota», «puntuación» ni «match».
- **RF-10.2c** «Hueco» DEBERÁ nombrar solo un periodo sin actividad (RF-9.1). Lo que la oferta pide y el perfil
  no tiene DEBERÁ decirse: «La oferta pide X y no consta en tu perfil».
- **RF-10.2d** Ningún texto de la usuaria DEBERÁ mencionar el CV base, el CV maestro, proveedores (Apify),
  piezas internas («el auditor», «tope de coste») ni a personas del equipo («Mar la revisará»).
- **RF-10.2e** Todos los textos y etiquetas de la usuaria (estados, motivos, ayudas, avisos) DEBERÁN estar en
  un solo archivo de textos que usen todas las pantallas, también las de Admin.

### Candidatura sin CV base (RF-10.3)
- **RF-10.3** CUANDO la usuaria pulse «Preparar candidatura», el flujo `candidatura` DEBERÁ partir del CV
  maestro de la versión vigente del perfil, sin CV base (P1). Ya no hay que generar nada antes. Sustituye a
  RF-3.1b y RF-3.7b en lo del CV base.
- **RF-10.3b** `redactor-cv` DEBERÁ elegir qué destacar según la oferta: la experiencia que no encaje DEBERÁ ir
  condensada en una línea (puesto · empresa · fechas), sin dejar huecos en las fechas (lo que hacía el CV base,
  RF-5.1g), y respetar la elección de longitud (RF-9.2d, RF-9.10f).
- **RF-10.3c** Las fuentes de `verificar_trazabilidad` y del juez DEBERÁN ser el CV maestro (y, para la carta,
  la oferta). La regla de origen no cambia (RT-08).
- **RF-10.3d** El eval real `cv` DEBERÁ pasar su umbral sin CV base antes de quitar el CV base del recorrido.
  SI no lo pasa, el CV base DEBERÁ volver como respaldo: se usa si existe y, si no, el CV maestro.
- **RF-10.3e** La pantalla y la pestaña del CV base DEBERÁN desaparecer. Las tablas `cv_base` y
  `cv_base_versiones` dejan de escribirse; NO DEBERÁ borrarse ningún dato.
- **RF-10.3f** Las candidaturas ya preparadas con un CV base DEBERÁN seguir viéndose, editándose y
  aprobándose como hoy.
- **RF-10.3g** *(S7)* La carta DEBERÁ sonar escrita por una persona: abrir con lo que interesa del puesto ligado a
  un hecho de la usuaria; frases cortas, una idea por frase; 3-4 párrafos y menos de una página; decir en llano
  lo que la oferta pide y no consta, sin disculparse; cerrar con lo que quiere aprender allí; sin clichés de
  autoalabanza ni halagos a la empresa. La regla de origen (RT-08) no cambia: las frases de motivación toman
  su origen de la oferta.

### Tu CV completo (RF-10.4)
- **RF-10.4** Perfil DEBERÁ tener «Tu CV completo» con «Ver» (el CV maestro con formato, RF-9.4) y «Descargar
  PDF» (P2). Lo compone el código a partir del perfil, sin modelo. Sustituye a «Tu CV maestro» (RF-9.4) en el
  nombre.
- **RF-10.4b** El PDF DEBERÁ ser legible por un ATS (sin tablas ni imágenes) y llevar solo datos del perfil.
  Solo lo descarga su dueña (RLS).
- **RF-10.4c** «Tu CV completo» NO DEBERÁ poder editarse: cada sección lleva «Editar», que lleva a esa sección
  de Tu perfil.
- **RF-10.4d** *(S7; cambiado por la spec 013, RF-13.26: tres diseños elegibles)* El PDF del CV (Tu CV completo y el de cada candidatura) DEBERÁ tener un diseño sobrio: el
  nombre grande y el titular debajo, en gris; las secciones en mayúsculas con una línea fina; «puesto ·
  empresa» en negrita y las fechas a la derecha; las habilidades en una línea; la tipografía de la marca, en
  tinta y gris. Todo es texto real, en el orden de lectura, sin tablas ni imágenes (RF-10.4b). La carta en
  PDF y en «Ver» DEBERÁ verse como carta: párrafos, sin negritas ni secciones. Las plantillas para elegir
  siguen en la spec 013 (calidad de CV y carta).
- **RF-10.4e** *(22-nov, cambiado tras la prueba: I8)* Los PDF de una candidatura aprobada DEBERÁN descargarse
  como `cv_nombre-apellidos_puesto_empresa.pdf` y `carta_nombre-apellidos_puesto_empresa.pdf`: la persona que
  selecciona la encuentra por su nombre y ella ve al final para qué puesto y empresa es. Lo que no conste (p. ej.
  el nombre) no sale; si ella quiere otro nombre, lo cambia a mano.

### Perfil en una pantalla (RF-10.5)
- **RF-10.5** CUANDO la usuaria no tenga perfil, Perfil DEBERÁ mostrar solo «Sube tu CV» (entradilla y un
  botón de elegir archivo). Al elegir el archivo, DEBERÁ subirse sin otro clic, como CV de perfil.
- **RF-10.5b** Con perfil, Perfil DEBERÁ mostrar *(orden cambiado el 22-nov)*:
  - **Izquierda** (a 1280 px): **Tu perfil**, por secciones plegables con su número («Experiencia (4)») y «Añadir».
  - **Derecha**, en este orden: 1. **Subir archivo** (botón claro, clase CV o Carta; varios CV, uno por sector,
    se juntan en un solo perfil); 2. **Tu CV completo** (RF-10.4); 3. **Por resolver (n)**, abierto CUANDO haya
    algo; 4. **Documentos subidos (n)**, abierto, solo la lista; 5. **Cómo escribes**, plegado.

  A 1280 px, dos columnas de igual ancho; a 390 px, una columna: Subir archivo, Tu perfil, Tu CV completo,
  Por resolver, Documentos subidos, Cómo escribes (RF-6.4b).
- **RF-10.5c** *(reescrito en S7)* «Por resolver» DEBERÁ reunir arriba las preguntas pendientes (RF-2.3), con
  «Responder», y debajo un desplegable **«Avisos (n)»** con los huecos (RF-9.1) y los avisos (RF-9.2), agrupados
  según RF-10.13. Cada aviso DEBERÁ tener dos acciones: la que lo resuelve («Corregir» o «Añadir») y «Dar por
  visto», como antes de la 010. Lo visto no vuelve mientras no cambie su causa (RF-9.2c).
- **RF-10.5d** La elección de longitud del CV DEBERÁ aparecer en un solo sitio: en el aviso de CV largo de
  «Por resolver» (RF-9.2d).
- **RF-10.5e** *(la elección de clase, sustituida en S8 por RF-10.14b)* Al subir un documento, las clases DEBERÁN ser dos: «CV» (por defecto) y «Carta». La clase
  «estético» se retira (P10); los ya subidos siguen en «Documentos subidos». Ningún documento subido se
  modifica.
- **RF-10.5f** *(22-nov)* Perfil DEBERÁ dejar añadir o modificar el **nombre** de la usuaria, que encabeza «Tu CV
  completo» y su PDF. «Subir archivo» DEBERÁ decir los formatos admitidos (PDF, DOCX, Markdown) y el peso máximo.

### Ofertas (RF-10.6)
- **RF-10.6** «Recomendadas» DEBERÁ llamarse **Ofertas** (`/ofertas`), con el contenido de la fase 8
  («Qué buscas», compatibilidad, descartar, estado de candidatura).
- **RF-10.6b** Ofertas DEBERÁ tener el botón «+ Añadir oferta», que abre una ventana (componente «Ventana» de
  la guía) para pegar el texto o la URL. La oferta añadida aparece en la lista con «Añadida por ti».
- **RF-10.6c** SI la usuaria aún no tiene perfil, Ofertas NO DEBERÁ quedarse en blanco: DEBERÁ decir «Sube tu
  CV para ver qué ofertas encajan contigo» con un botón a Perfil.
- **RF-10.6d** «Puntuar ahora» se queda en el detalle de una oferta sin compatibilidad (RF-8.5e), dentro del
  presupuesto del día (RF-10.9), sin límite propio de sueltas. Los avisos de gasto DEBERÁN verse solo CUANDO se
  haya llegado al presupuesto; entonces «Puntuar ahora» se desactiva con el aviso de RF-10.9c.
- **RF-10.6e** *(S7)* En «Qué buscas», los términos excluidos DEBERÁN ser lo último, justo antes de «Guardar y
  buscar».
- **RF-10.6f** *(22-nov)* «Qué buscas» DEBERÁ ir sin «Área»: Puestos sugeridos, Sector y Condiciones en la primera
  fila; Tipo de contrato, Nivel, País e Idiomas en la segunda; después Términos excluidos. Al guardar, el área se
  vacía y el CV deja de rellenarla.
- **RF-10.6g** *(22-nov, sustituye a RF-7.1f)* «Condiciones» DEBERÁ tener la casilla «Incluir las ofertas que
  añado», marcada por defecto. Marcada, las ofertas que añade la usuaria DEBERÁN verse siempre, pasen o no
  «Qué buscas» y el rango de compatibilidad; desmarcada, NO DEBERÁN verse. SI una oferta añadida queda oculta
  por la casilla, al terminar su análisis Horma DEBERÁ decirlo.
- **RF-10.6h** *(22-nov)* CUANDO se analiza una oferta añadida cuyo título no cubre ninguno de los puestos
  marcados, ese título DEBERÁ añadirse a los puestos de «Qué buscas», con un aviso; ella puede quitarlo como
  cualquier otro. Con la lista de puestos vacía NO DEBERÁ añadirse (empezaría a filtrar).

### Candidatura (RF-10.7)
- **RF-10.7** La usuaria DEBERÁ ver un solo estado por candidatura, que junta `estado` y `preparacion`:
  **Preparando → Por revisar → Lista para enviar → Enviada → Entrevista → Cerrada** (y «No se pudo preparar»
  con «Reintentar»). La máquina interna no cambia (RT-10).

  | Estado visible | Interno |
  |---|---|
  | Preparando | `borrador` con la preparación en marcha |
  | Por revisar | `borrador`, preparación `lista` o `pendiente_de_ti` |
  | Lista para enviar | `aprobada` |
  | Enviada · Entrevista · Cerrada | `enviada` · `entrevista` · `cerrada` |
  | No se pudo preparar | `borrador` con la preparación en `error` |

- **RF-10.7b** «Revisa esto» DEBERÁ usar el texto de RF-10.2c para lo que la oferta pide y no consta.

### Avance donde ocurre la acción (RF-10.8, reescrito en S7)
- **RF-10.8** Mientras Horma trabaje en una tarea de la usuaria, la pantalla donde ocurre DEBERÁ mostrar una
  sola barra con la frase y el porcentaje (RF-8.7): «Estamos leyendo tu CV… 40 %» en Perfil, «Preparando tu
  candidatura… 40 %» en la candidatura, «Calculando la compatibilidad… 40 %» en Ofertas. La cabecera NO DEBERÁ
  mostrar ningún indicador: nunca se ven dos barras a la vez. Vuelve P8 de la 008 («sin aviso en la cabecera»).
- **RF-10.8b** La barra DEBERÁ tener `role="status"` y no depender solo del color (RF-6.7e).
- **RF-10.8c** *(prueba del 22-nov; revisado el 25-nov en la spec 011, T08g y T08s, D-035)* La barra DEBERÁ verse
  rellenándose en lima desde el primer momento y nunca parecer parada: entre un paso real del servidor y el
  siguiente avanza sola según lo que suele tardar esa tarea (leer un CV, 37 s; analizar una oferta, 55 s; preparar
  una candidatura, 106 s), rápida al principio y cada vez más despacio, acercándose al 95 % sin llegar (a su
  duración típica va por el 60 %). Un paso real la adelanta si va por detrás; nunca baja ni llega al 100 % antes
  de terminar. SI el porcentaje no cambia en 3 s, el relleno late. Al repintar la pantalla o al volver a ella
  conserva su punto y cuenta el tiempo que la usuaria pasó en otra pestaña. Sin animación si se pide reducir el
  movimiento (entonces solo avanza con los pasos reales).

### Gasto (RF-10.9)
- **RF-10.9** Horma NO DEBERÁ gastar más de **1 USD al día** (día natural, hora de Madrid) por usuaria, en
  todo lo que hace para ella: perfil, puntuar, ofertas propias, candidaturas, estilo y lectura de URL (P11).
  Sustituye a RF-8.5b (0,50 USD solo para puntuar) y al límite de 30 sueltas de RF-8.5e y RF-8.5f.
- **RF-10.9b** El presupuesto DEBERÁ comprobarse en un solo sitio, al encolar la tarea. Cada tarea lleva como
  tope lo que quede del día, sin pasar de su tope por tarea, que se mantiene como red de seguridad (RT-14).
- **RF-10.9c** CUANDO no quede presupuesto, Horma NO DEBERÁ encolar la tarea y DEBERÁ decir: «Hoy ya hemos
  trabajado todo lo posible para ti. Mañana seguimos.» Lo ya hecho se conserva.
- **RF-10.9e** Una oferta que la usuaria añade sin presupuesto DEBERÁ guardarse y procesarse en cuanto vuelva
  a haberlo (al día siguiente), con el aviso «La analizamos mañana: hoy ya hemos trabajado todo lo posible para
  ti.». Sustituye a RF-8.5c (las propias se puntuaban también con el tope alcanzado).
- **RF-10.9d** La cifra de 1 USD es provisional: la definitiva sale del estudio de costes, con los precios
  oficiales del modelo (RF-10.11c).

### Ahorro (RF-10.10)
- **RF-10.10** Un solo agente, `analizador-oferta`, DEBERÁ leer cada oferta en una llamada y devolver lo que
  hoy devuelven `extractor-oferta`, `clasificador-oferta` y `auditor-oferta` (P7). Las comprobaciones que ya son
  código (fecha, repetición, salario, dominio) siguen en código.
- **RF-10.10b** `analizador-oferta` DEBERÁ pasar los evals reales `ofertas` y `red-teaming` con los umbrales de
  hoy (precisión ≥ 0,9 por campo; adversarias 100 %). SI no los pasa, `procesar_oferta` DEBERÁ volver a las
  tres llamadas de hoy.
- **RF-10.10c** La compatibilidad guardada DEBERÁ reutilizarse mientras no cambie nada del perfil que la afecte
  (experiencia, formación, habilidades, idiomas, titular). Corregir una errata en otra parte NO DEBERÁ obligar
  a volver a puntuar.
- **RF-10.10d** `clasificar_perfil` DEBERÁ lanzarse solo SI cambia la experiencia, la formación o el titular.
  *(Los campos de RF-10.10c y 10.10d cambian con la spec 012, RF-12.30h.)*

### Orden interno (RF-10.11)
- **RF-10.11** Solo los servicios DEBERÁN encolar tareas; los routers DEBERÁN llamar solo a servicios, nunca a
  repositorios. Qué tarea lanza a cuál DEBERÁ estar en una sola tabla del worker.
- **RF-10.11b** `HORMA_FLOW_IMPL` DEBERÁ valer `langgraph` por defecto en el código (P6). `PlainFlow` se queda
  como referencia en la suite (RT-12).
- **RF-10.11c** Los precios del modelo de la configuración DEBERÁN ser los oficiales, con la fecha de consulta.
- **RF-10.11d** DEBERÁN aparcarse, con su código conservado y fuera de los evals de la CI:
  `clasificador-respuesta` (y su eval `respuestas`) y `generador-cv-base` (y su eval `cv-base`) (P12). La
  tarea `extraer_oferta`, sin uso, DEBERÁ borrarse. Lo aparcado no se puede encolar desde la web.
- **RF-10.11e** `system.md` DEBERÁ ponerse al día con lo que hace el código (anexo de la auditoría): agentes
  activos, `langgraph` por defecto, número de esquemas, herramientas que usan la red y umbrales de las
  alertas.

### Fase 9b (RF-10.12)
*Sin construir: la entrevista pasa a la spec 016 (paso 6 del [PRD](../prd.md)), que parte de estos dos requisitos.*
- **RF-10.12** La 9b DEBERÁ hacerse solo con texto (P9): sin audio (RF-9.8 en lo del audio, RF-9.8b) ni
  `valorador_entrevista` (RF-9.9 a RF-9.9d), que quedan aplazados hasta medir el uso.
- **RF-10.12b** La entrevista sigue siendo la sesión de 20-30 minutos de RF-9.7i (P8), en su propio bloque
  «Tu entrevista» de Perfil, debajo de «Por resolver». «Por resolver» sigue reuniendo preguntas, huecos y
  avisos. Sustituye a RF-9.11 en dónde vive la entrevista. El plan de la 9b se escribe después de S6.

### Avisos agrupados (RF-10.13, S7)
- **RF-10.13** Los avisos de una candidatura («Revisa esto») y los de Perfil («Avisos») NO DEBERÁN repetir el
  mismo mensaje con distinto dato. DEBERÁN ir en tres grupos, cada uno con su título, y un grupo vacío no sale:
  1. **No consta en tu CV:** una sola línea con todo lo que la oferta pide y no consta («La oferta pide Python,
     SQL y AWS, y no constan en tu perfil», RF-10.2c).
  2. **Revisa:** los avisos de las reglas (RF-9.2), uno por regla, con los elementos afectados debajo (p. ej.
     «Sin cifras» con sus experiencias).
  3. **Dato dudoso:** las frases sin origen o con un dato nuevo, cada una con su frase.
- **RF-10.13b** En Perfil, «Dar por visto» de un aviso agrupado DEBERÁ marcar todos sus elementos; si después
  cambia la causa de uno, vuelve solo ese.
- **RF-10.13c** SI no hay nada que revisar, la candidatura NO DEBERÁ mostrar el bloque «Revisa esto» vacío. Las
  candidaturas antiguas, sin grupo guardado, DEBERÁN verse con sus avisos en «Revisa».

### Correcciones de la pasada del 22-nov (RF-10.14, S8)
Salen de la prueba completa de Mar con la usuaria inventada Irene (C1-G1). Decisiones de Mar del 22-nov: C1, F1
y E6.

**Documentos y perfil**
- **RF-10.14** CUANDO la usuaria elimine un CV, Horma DEBERÁ rehacer el perfil con los CV que queden,
  conservando lo que ella escribió o corrigió (origen «usuaria»), y quitar de «Por resolver» y de «Tu CV
  completo» lo que solo salía de ese CV. SI no queda ningún CV, el perfil DEBERÁ borrarse y Perfil vuelve a «Sube
  tu CV» (RF-10.5). La confirmación DEBERÁ decirlo antes: «¿Eliminar este CV? Rehacemos tu perfil sin él. No se
  puede deshacer.». Rehacer gasta del presupuesto del día (RF-10.9). Las candidaturas ya hechas no se tocan.
  Sustituye a «Tu perfil ya construido no cambia».
- **RF-10.14b** Al subir un documento, Horma DEBERÁ detectar con reglas, sin modelo, si es un CV o una carta: un CV tiene
  secciones y fechas; una carta, saludo, párrafos y despedida. SI duda, DEBERÁ preguntarlo. Junto al
  documento subido DEBERÁ ofrecer «¿No es un CV? Cámbialo» (o «¿No es una carta?»). Sustituye a la elección de
  clase de RF-10.5e.
- **RF-10.14c** Un DOCX subido DEBERÁ tener «Ver», que enseña su texto con el aviso «Así se lee tu documento; el
  diseño original del Word no se puede mostrar aquí.», y «Descargar original».
- **RF-10.14d** El perfil DEBERÁ guardar el resumen y el titular de **cada** CV, tal como están escritos y con su
  origen. Ninguno se pierde al juntar CV. El redactor del CV DEBERÁ elegir el que más encaje con la oferta y
  adaptarlo. «Tu CV completo» DEBERÁ usar el del CV más reciente. El aviso «Sin resumen» DEBERÁ salir solo si
  ningún CV lo tiene.
- **RF-10.14e** Responder una pregunta de «Por resolver» DEBERÁ decir qué ha cambiado y dónde («Actualizado en
  Habilidades: Excel básico.»). Los nombres de cursos y títulos no se cambian.

**Tu perfil**
- **RF-10.14f** La pantalla NO DEBERÁ enseñar el número de versión del perfil (se sigue guardando por dentro). Tras
  guardar, el mensaje DEBERÁ ser «Hecho: perfil actualizado.».
- **RF-10.14g** «Formación» DEBERÁ reunir los títulos y, debajo, «Cursos y certificados» (las certificaciones).
- **RF-10.14h** El nombre DEBERÁ rotularse «Tu nombre (sale arriba en tus CV y cartas)».
- **RF-10.14i** «Añadir» en un hueco DEBERÁ preguntar «¿Fue un empleo u otra cosa?» y abrir Experiencia u «Otras
  actividades».
- **RF-10.14j** Toda fecha que se escribe o se ve en Horma DEBERÁ ir como MM-AAAA (o AAAA si solo hay año).
- **RF-10.14k** El aviso «Sin cifras» DEBERÁ tener un «Corregir» por experiencia, que abra directamente la caja
  de «Modificar» de ese puesto, y dar ejemplos de logros medibles sin ventas (mesas o cubiertos por servicio,
  aforo, caja diaria, personas formadas, temporadas repetidas, ascensos, idiomas con los que atendió).
  *(Ampliado por la spec 013, RF-13.4b: «Ideas para medirlo», con preguntas generales y del puesto.)*

**Cómo escribes**
- **RF-10.14l** «Usas» y «Evitas» DEBERÁN verse como listas, un rasgo por viñeta. SI «Evitas» está vacío, DEBERÁ
  decir «Aún no lo sabemos: sube una carta tuya.». La guía DEBERÁ llevar la etiqueta «Hecha por Horma» o
  «Editada por ti».

**Textos y ayudas**
- **RF-10.14m** Las explicaciones de cada bloque DEBERÁN ir dentro de una ayuda «?» desplegable (componente de
  RF-6.7b, que pasa a la guía como «Explicación plegable»), en todas las pantallas. Textos nuevos:
  - Tu perfil: «Con estos datos Horma escribe tus CV y cartas. Si corriges algo, Horma usa tu corrección; el
    CV que subiste no cambia. Cada dato dice de dónde sale. Al corregir, las compatibilidades y candidaturas
    que ya tenías se marcan como «desfasadas»: se hicieron con tus datos de antes.»
  - Cómo escribes: «Horma escribe tus CV y cartas imitando cómo escribes. Esta guía sale de tus documentos;
    pesan más los que marcas «Lo escribí yo». Si la editas, manda lo tuyo.»
- **RF-10.14n** Ninguna pantalla DEBERÁ enseñar a la vez dos mensajes que se contradigan. Al subir un CV: primero
  solo «Estamos leyendo tu CV · N %»; el mensaje siguiente, solo al terminar.
- **RF-10.14o** El PDF de «Tu CV completo» NO DEBERÁ dejar páginas con una o dos líneas sueltas: una sección no
  empieza al pie de una página ni deja su última línea sola en la siguiente.

**Ofertas e ingesta**
- **RF-10.14p** Un puesto marcado DEBERÁ casar con sus variantes de género y de barra: «Jefe de sala» casa con
  «Jefe/a de sala», «Jefa de sala» y «Jefe(a) de sala». Las cuentas de cada puesto en «Qué buscas» DEBERÁN
  contar igual.
- **RF-10.14q** CUANDO la lista de Ofertas salga vacía por los filtros, DEBERÁ decir por qué y qué hacer: «Ninguna
  oferta casa ahora con los puestos que marcaste. Desmarca alguno o añade una oferta.».
- **RF-10.14r** Una ejecución de ingesta que lleve más de 30 minutos «en curso» DEBERÁ cerrarse sola como error,
  con el motivo «Se cortó sin terminar».

### «Corregir explicación» que amplía la información (RF-10.15, S9 — firmada por Mar el 22-nov)
Decisiones de Mar del 22-nov: revisar antes de que entre en el perfil; solo para candidaturas nuevas.

- **RF-10.15** El formulario de «Corregir explicación» DEBERÁ tener, además de la nota y el motivo, un campo
  opcional «Información nueva sobre ti» («Algo que no consta en tu CV y que Horma puede usar en esta oferta»).
  Se guarda junto a la corrección de esa oferta, con origen «usuaria». No llama al modelo.
- **RF-10.15b** CUANDO se prepare una candidatura **nueva** para esa oferta, el redactor DEBERÁ recibir esa
  información y poder usarla en el CV y la carta de esa candidatura, solo tal como ella la escribió: Horma NO
  DEBERÁ ampliarla ni deducir nada de ella. Las candidaturas ya preparadas NO cambian.
- **RF-10.15c** Tras enviar la corrección con información, DEBERÁ preguntar: «¿Guardarla también en tu perfil
  para futuras candidaturas?», con «Sí, revisarla» y «No, solo para esta oferta».
- **RF-10.15d** CON «Sí, revisarla», la información DEBERÁ aparecer en «Por resolver» de Perfil como propuesta
  pendiente, que ella puede editar, colocar (experiencia, habilidades, formación u otra) o descartar. NADA DEBERÁ
  entrar en el perfil hasta que ella la confirme. Al confirmar se aplica RF-10.14m (compatibilidades y
  candidaturas anteriores quedan «desfasadas»). CON «No», solo se usa en esa oferta.
- **RF-10.15e** *(cambiado por la spec 012, RF-12.26: la nota corregida manda en su lista)* El texto de ayuda de «Corregir explicación» DEBERÁ decir qué toca cada cosa: la nota y el motivo
  los revisa Mar y no cambian la compatibilidad; la información nueva solo se usa en las candidaturas nuevas de
  esa oferta; el perfil no cambia sin que ella lo confirme.

### Correcciones de la prueba manual del 22-nov (RF-10.16, RF-10.17, RF-5.3i)
- **RF-5.3i** *(H5)* Además de RF-5.3g, un texto pegado o leído por una usuaria sin ninguna palabra propia de
  una oferta de empleo (puesto, contrato, salario, experiencia, empresa, se busca… o una cifra de sueldo; en
  español o en inglés) DEBERÁ rechazarse con el mismo mensaje, sin analizarlo. Ante la duda deja pasar: rechazar
  una oferta real es peor que analizar un texto que no lo es.
- **RF-10.16a** *(I5)* El CV maestro DEBERÁ titular la sección «Otros» del perfil como «Información adicional», y
  ningún título que escriba el propio maestro (Proyectos, Otras actividades…) DEBERÁ dar aviso de formato.
- **RF-10.16b** *(I5)* Cada aviso de formato del CV DEBERÁ decir, en una frase en llano y sin «ATS» ni
  «encabezado»: qué pasa, por qué importa («los programas con los que las empresas filtran los CV…») y cómo
  arreglarlo.
- **RF-10.17** *(I14)* En la candidatura enviada o en entrevista, los botones de respuesta DEBERÁN ir bajo el
  título «Estado» e incluir «Me han contratado», que cierra la candidatura con el motivo «Contratada» y abre una
  Ventana: «Nos alegramos mucho por ti, esperamos que no vuelvas por aquí.»
- **RF-10.6i** *(H8)* `/ofertas#anadir` DEBERÁ abrir la ventana «Añadir oferta» también si ya se estaba en
  Ofertas; al cerrarla se quita el `#anadir`.

### Subir varios documentos a la vez (RF-10.18, S10 — firmada el 23-nov)
Decisiones de Mar del 23-nov: máximo 5; se suben los válidos; una sola pregunta al final para los dudosos; un solo
perfil rehecho por lote; sin presupuesto, se guardan; una barra; los repetidos se ignoran; vale en las dos pantallas.

- **RF-10.18** «Sube tu CV» (sin perfil, RF-10.5) y «Subir archivo» (con perfil, RF-10.5b) DEBERÁN dejar elegir
  **hasta 5 archivos** de una vez, con el mismo selector, los mismos formatos y el mismo peso máximo por archivo
  (RF-10.5f). Los dos DEBERÁN decir el máximo de 5. Al elegirlos se suben sin otro clic. Subir uno solo sigue
  valiendo y sigue las mismas reglas.
- **RF-10.18b** SI ella elige más de 5, Horma NO DEBERÁ subir ninguno y DEBERÁ decir: «Puedes subir hasta 5
  archivos a la vez. Elige 5 o menos.»
- **RF-10.18c** SI un archivo del lote falla, Horma DEBERÁ subir los válidos y avisar de cada fallido con su nombre
  y su motivo: «formato no admitido», «pesa más de N MB» o «no se ha podido leer». Un fallo NO DEBERÁ impedir los
  demás.
- **RF-10.18d** Un archivo idéntico (mismo contenido) a otro del lote o a uno ya subido DEBERÁ ignorarse, con el
  aviso «nombre.pdf ya estaba subido». No se guarda dos veces ni rehace el perfil.
- **RF-10.18e** Horma DEBERÁ decidir si cada archivo es CV o carta con RF-10.14b. SI duda de alguno, DEBERÁ
  preguntar **al final y una sola vez**: la lista de los dudosos, con un selector «CV / Carta» por cada uno y un
  botón «Continuar». Los que no dan duda se guardan sin esperar. «¿No es un CV? Cámbialo» sigue junto a cada
  documento. SI ella cierra la pregunta sin responder, los dudosos NO DEBERÁN guardarse y Horma DEBERÁ decir
  cuáles; el perfil se rehace con los demás.
- **RF-10.18f** El perfil DEBERÁ rehacerse **una sola vez por lote**, al final: después de guardar los archivos y,
  si hubo pregunta, después de responderla. Un lote sin ningún CV nuevo (solo cartas, repetidos o fallidos) NO
  DEBERÁ rehacer el perfil. Las cartas del lote siguen la regla de hoy para «Cómo escribes» (RF-5.6d).
- **RF-10.18g** SI no queda presupuesto del día (RF-10.9), los archivos DEBERÁN guardarse y el perfil quedar por
  rehacer, con el aviso «Tus archivos están guardados; rehacemos el perfil cuando haya presupuesto». El perfil
  DEBERÁ rehacerse solo en cuanto vuelva a haberlo. No se pierde nada. Vale también al subir un solo archivo
  (hoy no se guardaba).
- **RF-10.18h** Mientras dure el lote, la pantalla DEBERÁ mostrar una sola barra continua, «Leyendo N archivos…
  40 %» (N = los archivos que se están subiendo), sin parpadeo y sin volver a 0 (RF-10.8, RF-10.8c). Con un solo
  archivo, la frase de RF-10.8.
- **RF-10.18i** Al terminar, Horma DEBERÁ decir el resultado en un solo mensaje (RF-10.14n): cuántos se han
  subido y, debajo, los ignorados y los fallidos, cada uno con su nombre y su motivo.

## Bloques de construcción
Cada bloque es una rama y un PR contra `main`; Mar prueba y firma cada uno. Cada bloque deja Horma funcionando.

| Bloque | Requisitos | Coste de modelo |
|---|---|---|
| S1 · Palabras y menú | RF-10.1, RF-10.2, RF-10.6, RF-10.7 | 0 |
| S2 · Candidatura sin CV base | RF-10.3 | ~0,5-1 USD (eval `cv`) |
| S3 · Avance y subida | RF-10.5 (subida), RF-10.8 | 0 |
| S4 · Perfil en una pantalla | RF-10.4, RF-10.5 | 0 |
| S5 · Ahorro | RF-10.9, RF-10.10, RF-10.11c | ~1-2 USD (evals `ofertas` y `red-teaming`) |
| S6 · Orden interno | RF-10.11 (salvo c) | 0 |
| S7 · Correcciones tras la prueba | RF-10.3g, RF-10.4d-e, RF-10.5c, RF-10.5f, RF-10.6e-f, RF-10.8, RF-10.13, RF-6.4b | ~0,7-1,2 USD (eval `cv` y una candidatura) |
| S8 · Correcciones de la pasada del 22-nov | RF-10.14 a RF-10.14r, RF-10.16, RF-10.17 | ~2,2-3,3 USD (eval `cv` y subir y borrar CV en la prueba) |
| S9 · «Corregir explicación» amplía la información | RF-10.15 a RF-10.15e | ~0,2 USD (una candidatura de prueba); sin eval: los prompts no cambian |
| S10 · Subir varios documentos a la vez | RF-10.18 a RF-10.18i | 0 al construir; ~0,1-0,3 USD la prueba (un lote = un perfil rehecho); sin eval: los prompts no cambian |

## Criterios de aceptación
- Una usuaria nueva entra con Google, sube su CV y, sin pasar por ninguna otra pantalla, ve sus ofertas con
  compatibilidad y prepara y descarga una candidatura: 4 pantallas y 4 clics.
- Ninguna pantalla de la usuaria dice «CV base», «CV maestro», «nota», «puntuación», «match», «Apify», «el
  auditor», «tope de coste» ni «Mar».
- `/recomendadas`, `/anadir-oferta`, `/cv-base` y `/entrar` redirigen.
- Una candidatura se prepara sin CV base y pasa el eval `cv`; una antigua con CV base se sigue viendo.
- «Descargar PDF» de Tu CV completo da un PDF con los datos del perfil; otra usuaria recibe 404.
- Ofertas sin perfil enseña la invitación a subir el CV.
- Con un trabajo en marcha, su pantalla enseña una sola barra con el porcentaje y la cabecera no enseña ninguna.
- Una oferta con 20 requisitos que no constan da una sola línea «No consta en tu CV»; cuatro experiencias sin
  cifras dan un solo aviso con las cuatro.
- En Perfil, «Por resolver» tiene el desplegable «Avisos» con «Corregir» y «Dar por visto».
- El PDF del CV tiene el diseño de RF-10.4d y su texto extraído sale en orden; la carta se ve como carta.
- La carta de una candidatura real sigue la estructura de RF-10.3g y pasa el eval `cv`.
- En «Qué buscas» no hay «Área» y los términos excluidos son lo último.
- Los PDF de una candidatura aprobada se llaman `cv-puesto-empresa.pdf` y `carta-puesto-empresa.pdf`.
- Con 1 USD gastado hoy, no se encola ninguna tarea y se ve el aviso de RF-10.9c.
- Una oferta nueva hace 1 llamada al modelo (Admin › Costes). Corregir una errata en el resumen del perfil no
  vuelve a puntuar.
- Sin `HORMA_FLOW_IMPL` en el entorno, `candidatura` corre con LangGraph.
- Ningún router importa un repositorio ni encola (test de arquitectura).
- *(S8)* Con dos CV, borrar uno deja el perfil sin sus datos y con las correcciones de ella; borrar el último
  devuelve a «Sube tu CV». Una carta subida se reconoce sola como carta. Con dos CV, el perfil conserva los dos
  resúmenes. «Jefe de sala» encuentra «Jefe/a de sala». Ninguna pantalla enseña «versión N» ni fechas AAAA-MM.
- *(S9)* Una corrección con información nueva se usa en la candidatura nueva de esa oferta y no en las ya
  hechas; con «Sí, revisarla» aparece en «Por resolver» y el perfil no cambia hasta confirmarla; con «No», no
  aparece en Perfil.
- *(S10)* Con 5 archivos elegidos (dos CV, una carta, uno repetido y uno de formato no admitido) se guardan tres,
  se avisa de los otros dos con su nombre y su motivo, se ve una sola barra y el perfil se rehace una vez (una
  tarea en Admin › Costes). Con 6, no se sube ninguno. Con un dudoso, hay una sola pregunta y el perfil se rehace
  después de responderla. Sin presupuesto, los archivos quedan en «Documentos subidos» y el perfil se rehace al
  volver a haberlo. Funciona igual en «Sube tu CV» y en «Subir archivo».
- Todo comprobado a 1280 y 390 px, en claro y en oscuro (RF-6.4b).

## Requisitos que sustituye
| Spec | Requisitos | Por |
|---|---|---|
| 002 | RF-2.1b (nombres de CV base y estético), RF-2.4 (CV base desfasados), RF-2.9 a RF-2.9e, RF-2.10 | RF-10.3, RF-10.5e |
| 003 | RF-3.1b, RF-3.2 y RF-3.3 (CV base como fuente), RF-3.7b (pedir CV base), RF-3.8 («Detalles» del CV base), RF-3.8d | RF-10.3 |
| 005 | RF-5.1e, RF-5.1g, RF-5.3b (pestaña «Añadir oferta»), RF-5.4 y RF-5.4d-e (en lo del CV base) | RF-10.3, RF-10.6b |
| 008 | RF-8.1, RF-8.1b-e, RF-8.5b, RF-8.5c, RF-8.5e-g (P8 vuelve a valer desde S7) | RF-10.1, RF-10.9 |
| 009 | RF-9.4 (nombre), RF-9.5, RF-9.8 y RF-9.8b (audio), RF-9.9-RF-9.9d, RF-9.11 | RF-10.4, RF-10.5b, RF-10.12 |

## Fuera de alcance
- **Mejoras próximas, prioridad alta, justo después de la simplificación:** el aplicador autónomo de ofertas y
  leer el correo con `clasificador-respuesta` desaparcado. El aplicador toca una línea roja («Toda candidatura
  necesita la aprobación de la usuaria antes de cualquier envío»): antes hay que cambiar la constitución y
  volver a firmar las líneas rojas.
- Puntuar al acabar de leer el CV (P5).
- Entrevista por tandas (P8); audio y valoración en la 9b (P9).
- Plantillas de CV para elegir y el CV estético (spec 013). El diseño sobrio único de RF-10.4d sí entra (S7).
- Perfeccionar el `matcher` (spec 012, paso 2 del PRD): sigue siendo obligatorio antes de usuarias reales.
- Prueba con cinco personas: las cinco las hace Mar (21-nov), con perfiles y casos distintos; no hay usuarias externas en esa prueba. Coincide con RF-4.8 y P8 de la spec 004.
- Otras formas de entrar además de Google (tocan la constitución).

## Supuestos
- Una candidatura cuesta del orden de céntimos y 1 USD al día cubre un día normal (perfil, puntuar y unas 10
  candidaturas). Sin medir con los precios oficiales.
- La compatibilidad no depende de las partes del perfil que no están en RF-10.10c.
- Las candidaturas de hoy no pierden calidad al partir del CV maestro con la condensación de RF-10.3b; lo
  decide el eval `cv`.
- *(S10)* Rehacer el perfil con un lote de 5 CV cabe en el tope de una tarea `perfilar` (0,50 USD). Sin medir: se
  mira en la prueba de cierre.
