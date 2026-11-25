---
type: spec
title: portada-ofertas — Spec funcional
description: Requisitos de la fase 8 en notación EARS — landing y página de entrada, catálogo común en Admin, oferta original, «Qué buscas» dentro de Recomendadas, puntuación sin botón con tope diario, estado de candidatura y descartar, y avance con % que se retoma al volver.
tags: [spec, frontend, landing, recomendadas, candidaturas, worker, matcher]
status: active
sources: [./clarifications.md, ../system.md, ../constitution.md, ../002-perfil-recomendacion/spec.md, ../005-correcciones-profesor/spec.md, ../006-rediseno-2c/spec.md, ../007-ajustes-pantalla/spec.md]
generated: { by: claude-code, at: 2026-11-20 }
verified: { by: human, at: 2026-11-20 }
stale_after: null
---

# portada-ofertas — Especificación

## Contexto
La usuaria se queda con un camino claro: entra por una landing, ve en Recomendadas las ofertas que encajan
con lo que busca (ya puntuadas, sin pulsar nada) y prepara sus candidaturas. El catálogo común sale de su vista.
No hay agentes nuevos ni cambia el prompt del `matcher`: cambian cuándo se puntúa, cómo se guarda (por tandas)
y las pantallas. Todo lo nuevo sigue la guía de la fase 6 (RF-6.9).
Las respuestas del Clarify están en [clarifications.md](./clarifications.md) y se citan como P1…P9.

Esta spec modifica: RF-2.15c (puntuar ya no espera a un botón), RF-6.3b (pestañas), RF-6.3d (enlaces de
admin), RF-6.3e (portada sin sesión), RF-6.5, RF-6.5d y RF-6.5f (Recomendadas) y la fila «Portada» de RF-6.6.

## Requisitos (EARS)

### Landing y entrada (RF-8.1)
- **RF-8.1** *(sustituido por la spec 010, RF-10.1)* CUANDO alguien sin sesión abra `/`, Horma DEBERÁ mostrar la landing (P6), con la cabecera de la
  marca y, arriba a la derecha, «Crear cuenta» (botón primario) y «Entrar» (botón de texto). Sustituye a RF-6.3e.
- **RF-8.1b** *(sustituido por la spec 010, RF-10.1)* La landing DEBERÁ decir lo que Horma hace hoy, sin prometer nada más (P9). Texto propuesto (Mar lo
  corrige al firmar):
  - **h1:** «Ofertas que encajan contigo, y tu CV listo para cada una.»
  - **Entradilla:** «Horma busca ofertas de empleo, te dice cuáles encajan con tu experiencia y por qué, y
    prepara tu CV y tu carta para cada una con lo que tú has hecho.»
  - **Qué hace Horma** (cinco bloques, título y una frase):
    1. «Ofertas revisadas» — «Reúne ofertas de varias webs de empleo y aparta las que parecen fraude o ya no
       existen.»
    2. «Compatibilidad explicada» — «Puntúa cada oferta según tu experiencia y tu formación, y te dice por qué
       con frases de tu CV y de la oferta.»
    3. «También las que encuentras tú» — «¿Has visto una oferta en otro sitio? Pega el texto o el enlace y
       Horma la analiza igual. Solo la ves tú.»
    4. «CV y carta a medida» — «Adapta tu CV y escribe tu carta para cada oferta, con tu forma de escribir.
       No inventa: cada frase sale de lo que tú has contado.»
    5. «Tú decides» — «Sigues cada candidatura de borrador a entrevista. Nada sale sin tu aprobación.»
  - **Cómo empezar** (tres pasos): «Crea tu cuenta con Google» · «Sube tu CV» · «Mira tus ofertas
    recomendadas». Debajo, otra vez «Crear cuenta».
- **RF-8.1c** *(sustituido por la spec 010, RF-10.1)* «Crear cuenta» y «Entrar» DEBERÁN llevar a `/entrar`: marca, h1 «Entra en Horma», la frase «Usa tu
  cuenta de Google. Si es la primera vez, se crea tu cuenta.» y el botón primario «Continuar con Google».
- **RF-8.1d** *(sustituido por la spec 010, RF-10.1)* CUANDO alguien con sesión abra `/` o `/entrar`, o vuelva de Google, Horma DEBERÁ llevarla a
  Recomendadas; SI aún no tiene perfil, a Perfil (P6). La marca «Horma» de la cabecera común DEBERÁ llevar a
  Recomendadas.
- **RF-8.1e** *(sustituido por la spec 010, RF-10.1)* Las pestañas de la usuaria DEBERÁN ser cinco: Perfil · CV base · Añadir oferta · Recomendadas ·
  Candidaturas, más «Admin» para las administradoras (RF-7.7). Sustituye a RF-6.3b. En móvil, la rejilla se
  ajusta al número de pestañas (RF-6.3c).

### Catálogo común en Admin (RF-8.2)
- **RF-8.2** El catálogo común DEBERÁ verse solo en una pantalla «Catálogo» de Admin (P7), con el contenido de la
  portada actual (contador por estado, etiquetas de auditoría) y, en cada oferta, «Ver oferta original» (RF-8.3).
- **RF-8.2b** Admin DEBERÁ enlazar entre sí Ingesta, Catálogo y Costes. Sustituye al enlace a «Ofertas» de RF-6.3d.
- **RF-8.2c** SI quien pide el catálogo común no es administradora, el servidor DEBERÁ responder 403. Las ofertas
  propias de la usuaria (Añadir oferta) DEBERÁN servirse aparte, solo a su dueña.

### Oferta original (RF-8.3)
- **RF-8.3** En el detalle de cada oferta de Recomendadas y en el de cada candidatura DEBERÁ haber un botón «Ver
  oferta original» (P5). Abre una ventana encima con:
  - título, empresa, fuente (o «Añadida por ti») y fecha de publicación (o «No consta fecha de publicación»);
  - el texto tal como entró;
  - SI hay URL `http(s)`, el enlace «Abrir en la web de origen», en pestaña nueva.

  Al cerrarla (botón «Cerrar» o tecla Esc), la pantalla DEBERÁ quedar donde estaba, con el foco en el botón.
- **RF-8.3b** El texto DEBERÁ mostrarse como texto plano: sus enlaces e instrucciones no se activan (constitución:
  las ofertas son texto no fiable). Se conservan los saltos de línea.
- **RF-8.3e** El texto DEBERÁ mostrarse con formato legible según el diseño de Horma (apartados en negrita, listas
  y párrafos), sin tocar su contenido y sin interpretar HTML (P20).
- **RF-8.3f** Una oferta propia cuya dirección no sea de ninguna fuente del banco de Horma, o que no tenga
  dirección, DEBERÁ marcarse como «Fuente no reconocida por Horma» / «Sin fuente indicada» en Añadir oferta,
  Recomendadas y Admin › Catálogo (P20). Ampliar el banco de fuentes es trabajo aparte (`config/endpoints.json`).
- **RF-8.3g** En Admin › Catálogo, una oferta propia de fuente no reconocida con dirección DEBERÁ tener el botón
  «Calificar fuente», que pide la calificación (RF-1.7) del sitio de esa dirección. El resultado sale en
  Admin › Ingesta; si es apta, la administradora la da de alta y activa allí como cualquier fuente (P20).
- **RF-5.3g** Un texto pegado o leído por una usuaria que, sin etiquetas ni enlaces, no tenga al menos 5 palabras
  y 25 letras DEBERÁ rechazarse con «Ese texto no parece una oferta de trabajo…» (422), sin analizarlo ni
  puntuarlo (P20). Es un filtro sin modelo: no juzga la calidad de la oferta.
- **RF-8.3c** Una oferta propia SOLO DEBERÁ verla su dueña (RLS); si otra persona la pide, 404.
- **RF-8.3d** La ventana es un componente nuevo («Ventana»): DEBERÁ añadirse antes a la guía (RF-6.4, RF-6.9).

### «Qué buscas» dentro de Recomendadas (RF-8.4)
- **RF-8.4** *(Cambiado por la spec 009, RF-9.3b: «Puestos» pasa a ser «Área» y se añaden los puestos y los términos excluidos.)* Recomendadas DEBERÁ tener arriba un panel plegable «Qué buscas» con: puestos, sector, contrato, nivel,
  país, idiomas, «Solo remoto», «Solo con salario» y sueldo mínimo (P2). Cerrado por defecto; abierto si aún no
  hay nada guardado. Su botón primario es «Guardar y buscar».
- **RF-8.4b** La pestaña Preferencias DEBERÁ desaparecer y `/preferencias` NO DEBERÁ existir (enmienda P20, 20-nov:
  nunca fue una pantalla de la usuaria). Se mantiene que el CV rellena lo que la usuaria no ha tocado.
- **RF-8.4e** Al pulsar «Guardar y buscar», MIENTRAS Horma busca y arranca la puntuación, la pantalla DEBERÁ
  mostrar una barra de espera con el texto «Buscando y puntuando ofertas…», para que no parezca bloqueada (P20).
- **RF-8.4c** Los filtros de vista DEBERÁN ser: nota mínima y máxima, orden (recientes / más compatibles) y estado
  (RF-8.6c). NO DEBERÁN guardarse en el servidor ni llamar al modelo; este navegador los recuerda (P2).
- **RF-8.4d** Lo que se puntúa NO DEBERÁ depender de la vista: Horma puntúa en orden de más a menos parecido al
  perfil y decide si sigue con otra tanda con el rango 40-100 (RF-2.13), aunque la vista enseñe otro rango.

### Puntuar sin botón (RF-8.5)
- **RF-8.5** El botón «Recomendar» DEBERÁ desaparecer. Horma DEBERÁ empezar a puntuar lo que falta (P1):
  - CUANDO la usuaria abra Recomendadas, SI hay ofertas sin nota que pasan «Qué buscas», no hay una puntuación
    en marcha y la última empezó hace más de 1 h;
  - CUANDO la usuaria guarde «Qué buscas», sin esperar a la hora.

  Sustituye a RF-2.15c y RF-6.5f en lo del botón; cambiar la vista sigue sin llamar al modelo.
- **RF-8.5b** *(sustituido por la spec 010, RF-10.8)* Horma NO DEBERÁ gastar más de **0,50 USD al día** (día natural, hora de Madrid) por usuaria en
  puntuar el catálogo. Cada puntuación tiene como tope lo que quede del día. CUANDO se llegue al tope, la pantalla
  DEBERÁ decir: «Hoy ya hemos puntuado todo lo posible. Mañana seguimos con el resto.» Las ofertas sin nota se
  siguen viendo como «Sin puntuar».
- **RF-8.5c** *(sustituido por la spec 010, RF-10.8)* Las ofertas propias se siguen puntuando al añadirlas (RF-5.3d), también con el tope alcanzado:
  la usuaria las ha pedido una a una. Su gasto sí cuenta en el total del día.
- **RF-8.5d** Las ofertas descartadas (RF-8.6) NO DEBERÁN puntuarse.
- **RF-8.5e** *(sustituido por la spec 010, RF-10.9)* El detalle de una oferta sin nota DEBERÁ tener «Puntuar ahora» (P10), que puntúa solo esa oferta
  al momento y enseña su nota y su explicación al terminar (sustituye a la invitación a pulsar «Recomendar» de
  RF-6.5d). Funciona siempre, también con el tope de RF-8.5b alcanzado o con una tanda en marcha, hasta
  **30 ofertas sueltas al día** por usuaria (unos 0,015 USD cada una). Su gasto cuenta en el total del día.
- **RF-8.5f** *(sustituido por la spec 010, RF-10.9)* CUANDO la usuaria llegue a las 30 sueltas del día, «Puntuar ahora» DEBERÁ desactivarse con el texto
  «Has puntuado 30 ofertas sueltas hoy. Mañana puedes seguir.»
- **RF-8.5g** *(sustituido por la spec 010, RF-10.9)* El tope de 0,50 USD y el de 30 sueltas son provisionales (P11): la gestión del gasto por usuaria se
  decidirá más adelante.

### Estado de candidatura y descartar (RF-8.6)
- **RF-8.6** CUANDO una oferta de Recomendadas tenga candidatura, la fila DEBERÁ enseñar su estado como etiqueta
  con texto («Borrador», «Aprobada», «Enviada», «Entrevista», «Cerrada») y un enlace «Ver candidatura» (P3).
  SI la candidatura está abierta, «Preparar candidatura» DEBERÁ sustituirse por «Ver candidatura».
- **RF-8.6b** El detalle de una oferta sin candidatura abierta DEBERÁ tener «Descartar» (botón de texto). Al
  pulsarlo, la oferta DEBERÁ salir de la vista «Nuevas» sin confirmar y con el aviso «Oferta descartada.
  Deshacer». Las ofertas con candidatura abierta NO DEBERÁN tener «Descartar» (P4).
- **RF-8.6c** El filtro de estado DEBERÁ tener: **Nuevas** (por defecto: sin candidatura y sin descartar) ·
  **Con candidatura** (abierta o cerrada) · **Descartadas**. Cada opción con su número. *(Ampliado por la spec 011,
  RF-11.31: «Añadidas por mí».)*
- **RF-8.6d** En «Descartadas», cada oferta DEBERÁ tener «Recuperar», que la devuelve a «Nuevas». Descartar no
  borra la nota guardada ni toca ninguna candidatura.
- **RF-8.6e** Los descartes DEBERÁN ser de cada usuaria (RLS): nadie ve ni cambia los de otra.

### Avance con % (RF-8.7)
- **RF-8.7** Mientras Horma trabaja en una tarea de la usuaria, su pantalla DEBERÁ enseñar una barra de avance
  con el porcentaje y una frase (P8):
  - Recomendadas: «Puntuando ofertas · 40 %»;
  - Añadir oferta: «Analizando la oferta · 60 %» (también al leer una URL);
  - Candidatura: «Preparando tu CV y tu carta · 75 %».

  La barra es un componente nuevo («Barra de avance», `role="progressbar"` con su valor): DEBERÁ añadirse antes a
  la guía (RF-6.9). El color nunca es la única señal (RF-6.7e).
- **RF-8.7b** CUANDO la usuaria vuelva a esa pantalla (desde otra página, otra pestaña o tras cerrar la app) y la
  tarea siga en marcha, la barra DEBERÁ retomarse en su punto. El trabajo sigue en el servidor aunque nadie mire.
- **RF-8.7c** Al puntuar, Horma DEBERÁ guardar cada tanda al terminarla, con la revisión de rasgos personales
  (RF-2.14) ya hecha, y Recomendadas DEBERÁ enseñar esas notas sin esperar al final.
- **RF-8.7d** SI una tarea falla o llega a su tope, lo ya guardado se conserva y la pantalla DEBERÁ decir qué
  pasó en una frase; la barra desaparece.
- **RF-8.7e** El porcentaje DEBERÁ salir de los pasos hechos sobre los previstos (en Recomendadas, tandas hechas
  sobre tandas previstas). SI la tarea acaba antes de lo previsto, salta a 100 %. Nunca retrocede.
- **RF-8.7f** La pantalla DEBERÁ seguir consultando mientras la tarea esté en marcha, sin el límite de 90 s de hoy.

## Criterios de aceptación
- Sin sesión, `/` enseña la landing; «Crear cuenta» y «Entrar» llevan a `/entrar`, y de ahí a Google.
- Con sesión, `/` lleva a Recomendadas (a Perfil sin perfil). No hay pestaña Preferencias.
- Una cuenta que no es administradora recibe 403 al pedir el catálogo común; una administradora lo ve en
  Admin › Catálogo.
- «Ver oferta original» abre el texto completo; un enlace o una instrucción dentro del texto no se activa. Una
  oferta pegada por otra usuaria da 404.
- Cambiar nota, orden o estado no hace ninguna llamada al modelo ni ningún `PUT`.
- Al abrir Recomendadas con ofertas sin nota, empieza a puntuar sola; abrirla otra vez antes de 1 h no lanza otra.
  Guardar «Qué buscas» lanza una al momento.
- Con el gasto del día en 0,50 USD no se lanza ninguna puntuación del catálogo y se ve el aviso de RF-8.5b; una
  oferta pegada sí se puntúa, y «Puntuar ahora» puntúa una oferta en segundos.
- La oferta suelta número 31 del día no se puede puntuar y se ve el aviso de RF-8.5f.
- Una oferta con candidatura enseña su estado y «Ver candidatura»; una sin ella se descarta, aparece en
  «Descartadas», se recupera y no se puntúa mientras está descartada.
- La barra avanza por tandas, las notas aparecen por tandas y, al volver a la pantalla, la barra sigue donde iba.
- Una tarea que falla en la tercera tanda deja guardadas las dos primeras.
- Todo comprobado a 1280 y 390 px, en claro y en oscuro (RF-6.4b).

## Fuera de alcance
- Otras formas de entrar además de Google: tocan la constitución («Identidad: Google OAuth 2.0»).
- Aviso del avance en la cabecera de todas las páginas (P8).
- Unir Candidaturas en Recomendadas en una sola pestaña (P3).
- Descartar cerrando la candidatura a la vez (P4).
- Puntuar el catálogo al entrar ofertas por la ingesta, sin que la usuaria abra Recomendadas (P1).
- Aviso por correo de ofertas nuevas y búsquedas guardadas con nombre.
- Gestión del gasto por usuaria (topes por plan, avisos, abaratar el `matcher`): pendiente de decidir (P11).

## Supuestos
- Las fuentes activas tienen sus condiciones revisadas y aptas (fase 5); enseñar el texto de la oferta dentro de
  la cuenta de la usuaria, con su atribución, cabe en ellas. Si una fuente lo prohíbe, se enseña solo el enlace.
- 0,50 USD al día da para unas 150 ofertas puntuadas (unos 0,09 USD por tanda de 30, estimado en la fase 2).
