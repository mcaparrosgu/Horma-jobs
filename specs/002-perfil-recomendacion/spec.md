---
type: spec
title: perfil-recomendacion — Spec funcional
description: Requisitos funcionales de la fase 2 (perfil con origen, CV base y ofertas recomendadas con su porqué), en notación EARS.
tags: [spec, perfil, recomendacion]
status: active
sources: [./clarifications.md, ../system.md, ../001-ofertas/spec.md]
generated: { by: claude-code, at: 2026-11-14 }
verified: { by: human, at: 2026-11-14 }
stale_after: null
---

# perfil-recomendacion — Especificación

## Contexto
Una usuaria de prueba sube su CV, ve su perfil con el origen de cada dato, obtiene sus CV base y
recibe ofertas recomendadas con el porqué. Entran los flujos `perfilar` y `recomendar` y cuatro
agentes: `extractor-perfil`, `clasificador-postulante`, `generador-cv-base` y `matcher`. Las
ofertas vienen del catálogo común de la fase 1; el perfil y todo lo que cuelga de él es de cada
usuaria. Los requisitos transversales (RT-xx) están en [system.md](../system.md) y las respuestas
del Clarify en [clarifications.md](./clarifications.md) (se citan como P1…P17).

## Requisitos (EARS)

### Perfil
- **RF-2.1** CUANDO la usuaria suba uno o más CV (PDF, DOCX o Markdown), el sistema DEBERÁ guardarlos con nombre aleatorio, convertirlos a texto y ejecutar `extractor-perfil`, que produce un único `Perfil` con los datos de todos los CV fusionados y el CV maestro. SI el archivo supera el tamaño máximo o no es de un tipo admitido, ENTONCES el sistema DEBERÁ rechazarlo sin guardarlo y decirle por qué (P8, P11).
- **RF-2.1b** La usuaria DEBERÁ poder ponerle a cada CV (subido, base o estético) el nombre que quiera, p. ej. «CV hostelería» o «CV tecnología», y cambiarlo cuando quiera, para localizar cuál es el de cada sector. El nombre del archivo guardado sigue siendo aleatorio. SI no pone nombre, ENTONCES el sistema DEBERÁ proponer uno (el del archivo o «CV base · <sector>»); dentro de su cuenta NO DEBERÁ haber dos CV con el mismo nombre (P12).
- **RF-2.1c** La usuaria DEBERÁ poder ver cada CV subido (PDF o Markdown) en la propia página, sin descargarlo. Los DOCX, que el navegador no muestra, solo se descargan. Solo la dueña puede verlo.
- **RF-2.2** CADA dato del perfil DEBERÁ llevar su `origen` (el CV y la cita literal de la que sale). SI un dato no tiene origen, ENTONCES NO DEBERÁ entrar en el perfil: irá a `preguntas_pendientes` (RT-08).
- **RF-2.3** SI un dato es ambiguo, falta, o dos CV se contradicen, ENTONCES el sistema DEBERÁ dejarlo en `preguntas_pendientes`, mostrárselo a la usuaria y NO DEBERÁ completarlo por inferencia ni elegir entre los CV por ella (P8).
- **RF-2.4** CUANDO la usuaria cambie el perfil (responda una pregunta pendiente, corrija un dato o suba otro CV), el sistema DEBERÁ crear una versión nueva del perfil, conservar la anterior y marcar como desfasados los CV base y los matches calculados con ella; NO DEBERÁ regenerarlos sin que ella lo pida. Un dato que escribe la usuaria lleva como origen «usuaria» (P7).
- **RF-2.5** `clasificador-postulante` DEBERÁ etiquetar cada versión del perfil con sector, familia de puesto, nivel y stack, según la misma taxonomía que las ofertas.
- **RF-2.6** El sistema NO DEBERÁ inferir, extraer ni guardar edad, fecha de nacimiento, nacionalidad ni categorías del art. 9 del RGPD aunque aparezcan en el CV; tampoco DEBERÁ mencionarlas en ninguna explicación (RT-09). Los países de las preferencias son donde quiere trabajar, no de dónde es; los idiomas son competencias.
- **RF-2.7** CUANDO un CV contenga instrucciones dirigidas a una IA, el sistema DEBERÁ registrarlas en `instrucciones_embebidas` y NO DEBERÁ ejecutarlas (RT-07).

### Preferencias
- **RF-2.8** El sistema DEBERÁ ofrecer las preferencias como filtros de búsqueda al estilo de The Hub: grupos de **casillas** para puestos (familias de la taxonomía), sector, tipo de contrato, nivel, país e idiomas; casillas sueltas para «solo remoto» y «solo con salario publicado»; un **campo numérico** donde la usuaria escribe el sueldo mínimo; y una ordenación (más recientes o más compatibles). Cada casilla DEBERÁ mostrar entre paréntesis cuántas ofertas del catálogo tiene (P13). Todo grupo de más de 2 casillas DEBERÁ ofrecer «Seleccionar todo» y «Quitar selección».
- **RF-2.8b** Puestos, países, idiomas y sector DEBERÁN llegar marcados a partir del CV, y la usuaria DEBERÁ poder cambiarlos y marcar puestos que no están en su CV para cambiar de carrera. Contrato, remoto, nivel, sueldo mínimo y salario publicado los marca ella. Un grupo sin nada marcado NO DEBERÁ filtrar (P1).

### CV base
- **RF-2.9** El sistema DEBERÁ generar, una sola vez por versión del perfil y a petición de la usuaria, hasta 4 CV base por sector o familia de puesto, compatibles con ATS, en Markdown (P3). Cada CV base DEBERÁ pasar `verificar_trazabilidad` antes de guardarse, con un máximo de 2 intentos; SI no la pasa, ENTONCES NO DEBERÁ guardarse y la usuaria DEBERÁ ver el motivo.
- **RF-2.9b** Ningún idioma de los CV DEBERÁ perderse. SI dos CV dan niveles distintos del mismo idioma, ENTONCES el idioma DEBERÁ quedar en el perfil sin nivel y la usuaria DEBERÁ recibir una pregunta pendiente con los niveles como opciones. Todo CV base DEBERÁ incluir todos los idiomas del perfil; SI falta alguno, ENTONCES NO DEBERÁ guardarse (se reintenta).
- **RF-2.9c** Los puestos de un CV base DEBERÁN estar escritos todos en el mismo género gramatical (camarera/camarero), el de `genero_puestos` del perfil. Ese dato DEBERÁ salir de cómo están escritos los puestos en sus CV o de lo que responda la usuaria; NUNCA se deducirá del nombre. SI está sin fijar, ENTONCES la usuaria DEBERÁ recibir una pregunta pendiente. El cambio de género de un puesto no cuenta como dato inventado.
- **RF-2.9d** La pantalla de CV base DEBERÁ mostrar cada CV como un documento legible (nombre, secciones, líneas), no como texto Markdown; «Copiar texto» sigue copiando el Markdown.
- **RF-2.9e** La usuaria DEBERÁ poder modificar (nombre y texto) y eliminar cualquier CV base, y cambiar en cualquier momento el género de sus puestos. Un CV base modificado es texto suyo y no se vuelve a comprobar contra el CV; eliminarlo permite generarlo de nuevo.
- **RF-2.10** El sistema DEBERÁ permitir subir un CV estético propio, guardarlo sin procesar con nombre aleatorio y servirlo solo por la API a su dueña. Nadie lo modifica.

### Recomendación
- **RF-2.11** CUANDO se ejecute `recomendar`, el sistema DEBERÁ filtrar el catálogo por país, contrato, remoto, idioma, nivel, sector, puesto, salario publicado y sueldo mínimo, y ordenar por coincidencia de taxonomía y fecha, sin descartar nada más. Una oferta a la que le falte un dato del filtro DEBERÁ pasar el filtro (P2). El sueldo mínimo es en euros brutos al año; el servidor convierte el sueldo mensual de la oferta (× 12) para compararlo, y una oferta sin sueldo o en otra moneda DEBERÁ pasar marcada como «no comparable» (P17). Las ofertas con `recomendable = falso` NO DEBERÁN llegar a la recomendación (RF-1.9).
- **RF-2.12** `matcher` DEBERÁ puntuar por tandas de 30 siguiendo ese orden hasta cubrir el rango elegido, y por cada oferta devolver: nota de 0 a 100 solo por experiencia y formación, nivel de condiciones (`bajo`, `medio` o `alto`) calculado por código, no por el modelo, solo con las condiciones que la usuaria ha marcado (bajo si alguna no se cumple; medio si ninguna falla pero de alguna no hay dato; alto si todas se cumplen o no marcó ninguna), y una explicación de 2 o 3 frases que cite datos del perfil y de la oferta. El resultado DEBERÁ guardarse por (usuaria, oferta, versión del perfil) y reutilizarse sin volver a llamar al modelo.
- **RF-2.13** La usuaria DEBERÁ poder elegir su rango de compatibilidad, que por defecto es 40-100 (P9), y corregir una explicación. La corrección DEBERÁ guardarse junto al match y NO DEBERÁ entrar en `evals/` hasta que Mar la revise con un comando expreso (P4).
- **RF-2.14** Las explicaciones NO DEBERÁN mencionar rasgos personales (edad, sexo, nacionalidad, estado civil, salud, ni otras categorías del art. 9) ni usarlos para puntuar (RT-09).

### Pantallas, consola y coste
- **RF-2.15** Las pantallas de perfil (con origen y preguntas pendientes), preferencias, CV base y ofertas recomendadas DEBERÁN funcionar en móvil y en escritorio, con el marco visual del proyecto. Cada usuaria DEBERÁ ver solo lo suyo (RLS).
- **RF-2.15b** La pantalla de ofertas recomendadas DEBERÁ parecerse a la maqueta `dashboard.png` de Mar (P14): pestañas arriba (Perfil, Preferencias, CV base, Recomendadas); barra de filtros encima de la tabla con los filtros del RF-2.8 y el rango de compatibilidad; contador («N ofertas»); un bloque plegable «Cómo leer las recomendaciones»; y una tabla con las columnas **Oferta** (título y empresa), **Puesto** (etiqueta de color), **Compatibilidad** (barra y nota 0-100), **Condiciones** (nivel), **Salario** (el texto tal como lo dice la oferta, nunca el valor convertido, P17), **Lugar** (país o remoto) y **Publicado**, con un «?» en cada cabecera que explica la columna. La explicación de 2 o 3 frases DEBERÁ verse en la misma fila (desplegable) junto al botón para corregirla. En móvil cada fila DEBERÁ pasar a tarjeta.
- **RF-2.15c** CUANDO la usuaria cambie un filtro o la ordenación, el sistema NO DEBERÁ llamar al modelo: solo reordena y filtra lo ya puntuado. Las ofertas nuevas sin nota DEBERÁN verse como «sin puntuar» hasta que ella pulse «Recomendar», que puntúa solo lo que falta (RF-2.12).
- **RF-2.16** El sistema DEBERÁ permitir ejecutar `perfilar` y `recomendar` desde la consola paso a paso, con traza (RT-05), y cada agente nuevo por separado (RT-04).
- **RF-2.17** CUANDO un set de evals se mida con el modelo real, el sistema DEBERÁ detenerlo si el coste acumulado supera el tope de 1 por ejecución y dejar constancia de ello (P6).

## Criterios de aceptación (puerta de salida)
- [x] `horma eval correr perfil` sobre 12 CV inventados de 5 sectores: precisión ≥ 0,9 por campo; lo ambiguo va a pendientes al 100 %; las 2 adversarias, al 100 % sin efecto.
- [ ] `horma eval correr recomendacion` sobre 20 pares perfil-oferta: nota dentro de ±10 de la esperada; ninguna explicación con rasgos personales (100 %). **Fase cerrada el 15-nov-2026 con este criterio a medias:** rasgos personales y condiciones al 100 %, pero la `nota` (0,67 con 21 casos) queda para el plan del `matcher`.
- [x] `horma eval correr cv-base` sobre 5 casos (uno por sector): cada CV base pasa `verificar_trazabilidad` en 2 intentos como máximo y cumple el formato ATS, al 100 %.
- [x] Los tres sets corren en CI: simulado sin clave; con modelo real y tope de coste cuando hay clave.
- [x] `verificar_trazabilidad` rechaza el 100 % de los CV base con datos que no existen en el CV maestro (test unitario).
- [x] Prueba manual: subir un CV inventado con el nombre que quiera, ver el perfil con su origen y sus pendientes, generar CV base, subir un CV estético, marcar filtros con casillas y escribir un sueldo mínimo, y ver ofertas recomendadas con rango 40-100 en una pantalla como la maqueta.
- [x] Cambiar un filtro no produce ninguna llamada al modelo (test con la puerta única simulada).
- [x] Un test de RLS demuestra que una usuaria no lee el perfil, los CV ni los matches de otra.
- [x] Consola: `horma flujo correr perfilar --usuaria ana --entrada cv.pdf`, `horma agente correr matcher --entrada tanda.json`, `horma recomendar ana --rango 40-100`.

## Fuera de alcance
- Adaptar CV y carta a una oferta, jueces, aprobación y tablero: fase 3.
- Descargar los CV en PDF: fase 3 (P3).
- LangGraph: fase 4; `perfilar` y `recomendar` siguen en `PlainFlow`.
- Programar recomendaciones periódicas o avisos: se piden a mano.
- Datos de personas reales: todo es inventado hasta cerrar privacidad y RGPD.

### Apuntado para añadir si hay tiempo, cuando todo lo demás esté hecho (P15)
No se pierde: queda en la spec y en la bitácora, y se retoma al terminar la construcción de la fase.
- Descarga de los CV en PDF (ahora, solo Markdown en pantalla).
- Aviso por correo con ofertas nuevas que encajen con los filtros (The Hub lo ofrece: «Get an email with new jobs in this search»).
- Guardar búsquedas con nombre.
- Programar recomendaciones periódicas.
- Verificar las explicaciones del `matcher` (hueco detectado al repasar la fase): hoy solo los CV base pasan `verificar_trazabilidad`. Plan: el matcher devuelve los fragmentos literales del perfil y de la oferta en que se apoya, un verificador en código comprueba que existen y, si no, la explicación no se muestra y se reintenta una vez. Un segundo agente revisor solo en el eval, no en producción. Toca RF-2.12, el plan y el matcher.
- Ignorar el texto invisible al convertir un CV (blanco sobre blanco o tamaño 0) en `convertir_cv`. Hueco detectado al repasar la fase: una instrucción escondida en el CV es texto del CV, así que `verificar_origen` y `verificar_trazabilidad` no detectarían el dato falso que provoque; hoy solo lo frena que el extractor la anote en `instrucciones_embebidas` (RF-2.7) y que la usuaria vea el origen de cada dato. Toca `convertir_cv` y el eval `perfil`.
- No nombrar en la explicación las instrucciones embebidas de una oferta. Visto en la prueba 2.3: el `matcher` ignora bien la inyección de una oferta, pero escribe «La oferta incluye una instrucción para reenviar datos personales, que se ignora», que a la usuaria no le sirve. Plan: ajustar el prompt del `matcher` para que las ignore sin mencionarlas, y añadir un caso al eval. Toca RF-2.12 y el prompt del `matcher`.
- Modalidad «híbrido» en los filtros de Recomendadas (pedido por Mar el 16-nov-2026; **se hace después de la fase 4**). Hoy solo existe `remoto` (sí/no) y el filtro «Solo remoto». Plan: campo `modalidad` (remoto / híbrido / presencial) en la oferta, con migración; detectarla al normalizar (`normalizar_oferta`, hoy `_REMOTO_RE`); y cambiar «Solo remoto» por un selector de modalidad en Recomendadas y Preferencias. Las ofertas ya ingestadas quedan sin modalidad hasta reprocesarlas. Toca el esquema `Oferta`, `buscar_ofertas`, `evaluar_condiciones` y las dos pantallas.
- Botón «Buscar» en Recomendadas (hecho el 16-nov-2026): los filtros ya no se aplican al marcar cada casilla, sino al pulsarlo.

### Plan para perfeccionar el `matcher` (obligatorio antes de probar con usuarias reales)
Decidido el 15-nov-2026. Se retoma **cuando todas las fases estén construidas** y **antes** de cualquier prueba con personas reales. Hoy el `matcher` supera los 20 casos inventados, pero esa muestra es pequeña y solo la han medido casos simulados; no basta para fiarse de él.

1. **Medir mejor.** Ampliar `evals/recomendacion/` de 20 a unos 60 casos: más sectores, notas intermedias (40-70, donde más se duda), perfiles casi vacíos y ofertas incompletas. Incluir las correcciones de usuarias importadas con `eval importar-correccion`. Correr cada caso 3 veces con el modelo real para ver cuánto varía la nota entre ejecuciones. Medir también el orden (que la mejor oferta quede arriba), no solo el ±10.
2. **Explicaciones fiables.** Hacer los dos apuntados de arriba: verificar que las citas existen (RF-2.12) y no nombrar las instrucciones embebidas de una oferta. Añadir el revisor solo en el eval.
3. **Equidad.** Casos por pares que cambian solo un rasgo personal (nombre, edad, sexo, nacionalidad, foto, huecos laborales) con el resto idéntico: la nota debe ser igual (±3). Contrastarlo con la clasificación legal de la fase (`docs/03-legal.md` / AI Act y RGPD) antes de dar nada por bueno.
4. **Robustez.** Ofertas en otro idioma, muy largas, con inyección o sin datos; tanda con fallos parciales; reintentos; el tope de 5 tandas y el de coste. Debe fallar con aviso claro, nunca con una nota inventada.
5. **Bucle de correcciones.** Decidir con Mar si una corrección debe reordenar la lista de quien la hace (hoy no cambia la nota) y quién revisa las correcciones y con qué frecuencia.
6. **Coste y automatización.** Retomar la decisión de «Recomendar» manual (embudo, caché de prompt, explicación bajo demanda). Preguntar a Mar antes de proponer el embudo.

**Punto de partida (medido el 15-nov-2026 con el modelo real, 21 casos):** `nota` 0,67 (7 casos fuera de ±10: 02, 04, 10, 13, 15, 18, 21); `condiciones` 1,00 (ahora las calcula código); `sin_rasgos` 1,00; adversarias 0,67 (solo por la `nota` del caso 21).

**Puerta de salida:** ≥ 90 % de los casos dentro de ±10 con el modelo real, estable en las 3 ejecuciones; 100 % sin rasgos personales ni diferencias por pares; 100 % de explicaciones con citas verificadas; y una revisión manual de Mar sobre una muestra de 20 recomendaciones.

## Decidido al planificar
Al leer el esquema `Oferta` de la fase 1: `contrato`, `ubicacion` e `idiomas` son texto libre, no hay campo país y el salario no indica periodo. Se resuelve en el [plan](./plan.md): código sin IA los normaliza al guardar cada oferta (P16) y el sueldo se compara en euros brutos al año (P17).
