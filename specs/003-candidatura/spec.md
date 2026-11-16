---
type: spec
title: candidatura — Spec funcional
description: Requisitos funcionales de la fase 3 (CV y carta adaptados con verificador y un juez, aprobación, envío por cuenta propia y seguimiento en un tablero), en notación EARS. Regenerada el 16-nov-2026 con el cambio «simplificar la candidatura» (bloque H).
tags: [spec, candidatura, seguimiento]
status: active
sources: [./clarifications.md, ../system.md, ../002-perfil-recomendacion/spec.md, ../../docs/Horma v2_ requerimientos por fases.pdf, ../../docs/mejora-simplificar-candidatura.md]
generated: { by: claude-code, at: 2026-11-16 }
verified: { by: human, at: 2026-11-16 }
stale_after: null
---

# candidatura — Especificación

## Contexto
La usuaria elige una oferta recomendada. Horma elige por código el más adecuado de sus CV base, le
prepara un CV y una carta adaptados a esa oferta, los comprueba con código (verificador) y con un
segundo agente (juez), y le deja un borrador. Ella lo lee, lo corrige si hace falta, pulsa «Aprobar
y descargar», envía la candidatura por su cuenta y la sigue en un tablero con dos botones: «Me han
llamado» y «Me han rechazado».

**Cambio del 16-nov-2026 (bloque H).** La fase 3 se construyó con seis agentes, dos jueces y hasta
11 llamadas al modelo por candidatura, y una pantalla con hasta 9 decisiones antes de tener los PDF.
Se simplifica a leer → (editar) → aprobar y descargar, y de 3 a 5 llamadas. La seguridad no cambia:
no se inventa nada y cada línea conserva su origen. Las decisiones están en
[clarifications.md](./clarifications.md) (P12-P17 y «Lo que sustituye a respuestas anteriores»).

Entran el flujo `candidatura` (el único con bucle, el que define cómo tiene que ser `Flow` para que
LangGraph lo sustituya en la fase 4), el flujo `clasificar_respuesta` (solo consola por ahora) y
cuatro agentes: `redactor-cv`, `redactor-carta`, `juez-candidatura` y `clasificador-respuesta`. Los
requisitos transversales (RT-xx) están en [system.md](../system.md) y las respuestas del Clarify en
[clarifications.md](./clarifications.md) (se citan como P1…P17).

## Requisitos (EARS)

### Flujo `candidatura`
- **RF-3.1** El flujo `candidatura` DEBERÁ tener un estado tipado (`EstadoCandidatura`) y pasos con
  nombre: `elegir_cv_base` → `redactar_cv` → `redactar_carta` → `comprobar` → `juzgar` →
  (vuelta única si hace falta) → `componer`. La vuelta única DEBERÁ volver a redactar solo lo que
  falla: si el CV tiene algo que corregir, `redactar_cv` y después `redactar_carta`; si solo la
  carta, `redactar_carta`; tras la vuelta, `comprobar` y `componer`, sin volver a juzgar (P12). Cada
  documento DEBERÁ redactarse como máximo 2 veces y el juez DEBERÁ llamarse una sola vez: de 3 a 5
  llamadas al modelo por candidatura. El flujo DEBERÁ terminar en `lista` si no queda ningún aviso o
  en `pendiente_de_ti` si queda alguno; en los dos casos la candidatura queda en `borrador`.
- **RF-3.1b** `elegir_cv_base` DEBERÁ elegir con código, sin llamar al modelo, el CV base de la
  usuaria más adecuado para la oferta: entre los suyos no rechazados, primero el que coincide en
  familia y sector, después en familia, después en sector y, si no coincide ninguno, el más
  reciente; a igualdad, el más reciente. DEBERÁ anotar el motivo en una frase. La usuaria NO lo
  elige (P9, P14). SI no tiene ninguno válido, ENTONCES el flujo DEBERÁ terminar en error sin
  redactar. El redactor parte también del CV maestro, que siempre está al día, así que no hay aviso
  de CV base desfasado.
- **RF-3.2** `redactor-cv` DEBERÁ adaptar el CV base a la oferta aplicando la regla de los huecos:
  cambia qué se muestra y cómo se cuenta, nunca fechas, cargos, empresas ni titulaciones. Lo que la
  oferta pide y el perfil no tiene DEBERÁ ir a `huecos` con una propuesta para la usuaria, nunca al
  CV. Cada frase DEBERÁ llevar en la traza el fragmento literal del que sale. En la vuelta recibe
  los errores, los problemas y las palabras que le toca corregir.
- **RF-3.3** `comprobar` (código) DEBERÁ pasar `verificar_trazabilidad` al CV y a la carta: fechas,
  cargos, empresas y titulaciones idénticos a los de las fuentes y cada entrada de la traza apuntando
  a un fragmento real. Las fuentes del CV son el CV maestro y el CV base elegido (origen «usuaria» si
  ella lo editó, P9); las de la carta, también la oferta. DEBERÁ buscar además rasgos personales en
  los dos documentos y medir el CV con `medir_ats` (RF-3.5).
- **RF-3.4** `juez-candidatura` DEBERÁ revisar a la vez el CV y la carta y devolver un veredicto por
  documento (`aprobado` o `corregir`) y una lista tipada de problemas (`sin_origen`, `inflado`,
  `promesa`, `rasgo_personal`, y `repite_cv` solo para la carta), cada uno con su documento y la
  frase afectada. NUNCA DEBERÁ reescribir.
- **RF-3.5** `medir_ats` (código) DEBERÁ comprobar el formato ATS (sin tablas, imágenes ni HTML;
  encabezados estándar) y calcular la cobertura de las palabras clave de la oferta (requisitos y
  stack). Las palabras que falten y tengan origen en las fuentes DEBERÁN pedirse al redactor dentro
  de la vuelta única, aunque el juez lo apruebe todo (P13); las que no tengan origen DEBERÁN quedar
  en `huecos` y NO DEBERÁN insertarse. La cobertura se mide y se guarda; su umbral se fija en la
  fase 4 (RF-4.4).
- **RF-3.6** `redactor-carta` DEBERÁ escribir la carta a partir del CV maestro, el CV adaptado, la
  oferta y el sector, sin carta base (P1). NO DEBERÁ repetir el CV. Cada frase con un dato DEBERÁ
  llevar su fragmento en la traza; el saludo y la despedida DEBERÁN salir de una lista cerrada de
  fórmulas.
- **RF-3.6b** CUANDO una oferta o un CV contenga instrucciones dirigidas a una IA, los agentes
  DEBERÁN registrarlas en `instrucciones_embebidas` y NO DEBERÁN ejecutarlas (RT-07). El CV y la
  carta NO DEBERÁN mencionar rasgos personales (RT-09).
- **RF-3.6c** `componer` DEBERÁ reunir en una sola lista de avisos, en lenguaje llano y sin prefijos
  técnicos, los errores de `comprobar` sobre el texto final y los problemas del juez cuya frase siga
  literalmente en ese texto; cada aviso DEBERÁ decir a qué documento y a qué frase se refiere.

### Candidatura y seguimiento
- **RF-3.7** La `Candidatura` DEBERÁ seguir la máquina de estados `borrador → aprobada → enviada →
  entrevista`. Desde cualquier estado la usuaria DEBERÁ poder pasarla a `cerrada` con un motivo
  (`rechazo`, `descartada` o `retirada`); `cerrada` es final (P8). Cualquier otra transición DEBERÁ
  rechazarse. Cada transición DEBERÁ quedar en el historial con su fecha.
- **RF-3.7b** CUANDO la usuaria pulse «Preparar candidatura» en una oferta recomendada, el sistema
  DEBERÁ crear la candidatura y lanzar su preparación sin pedirle que elija CV base. SI no tiene
  ningún CV base válido, ENTONCES DEBERÁ pedirle que genere uno primero. NO DEBERÁ haber dos
  candidaturas no cerradas para la misma oferta. SI la oferta ya tuvo una candidatura cerrada,
  ENTONCES DEBERÁ avisar de que ya se preparó (con su fecha y motivo de cierre) y solo crear otra si
  la usuaria lo confirma.
- **RF-3.8** MIENTRAS la candidatura esté en `borrador`, la usuaria DEBERÁ ver el CV y la carta
  adaptados y una sola lista «Revisa esto» con los huecos (con su propuesta) y los avisos, cada
  aviso junto a la frase que señala. El CV base elegido, su motivo y la cobertura ATS DEBERÁN ir
  plegados en «Detalles». DEBERÁ poder editar el CV y la carta a mano o descartar la candidatura
  (P4). Lo que ella escribe lleva origen «usuaria», se queda en esa candidatura y vuelve a pasar
  `comprobar` sin llamar al modelo; los problemas del juez cuya frase siga en el texto DEBERÁN
  conservarse, también los del documento que no ha editado. El CV base solo se cambia en su propia
  pantalla (RF-2.9e).
- **RF-3.8a** Solo la dueña, con su sesión, DEBERÁ poder aprobar. Los avisos NO DEBERÁN bloquear:
  pulsar «Aprobar y descargar» cuenta como haberlos revisado (P10) y descarga los dos PDF. Siempre
  se usa el CV adaptado.
- **RF-3.8b** CUANDO la candidatura esté `aprobada` o en un estado posterior, la usuaria DEBERÁ poder
  descargar el CV adaptado y la carta en PDF (P2). Después envía por su cuenta y la marca como
  `enviada` en un clic: la fecha es la de hoy y el canal (`correo`, `web`, `linkedin` u `otro` con
  texto corto) es opcional (P3).
- **RF-3.8c** MIENTRAS una candidatura no esté `aprobada` por su dueña, el sistema NO DEBERÁ marcarla
  como enviada, servir sus PDF ni exponerla a terceros (RT-10).
- **RF-3.8d** CUANDO se edite un CV base (RF-2.9e) o se vuelva a una versión anterior, el sistema
  DEBERÁ guardar antes la versión actual (texto, nombre, fecha y origen: edición o restauración) en
  su historial. La usuaria DEBERÁ poder ver ese historial, con lo añadido y lo quitado marcado entre
  cada versión y la siguiente, y volver a cualquier versión, de modo que ningún texto se pierda. Solo
  la dueña ve su historial (RLS). Al eliminar un CV base se elimina también su historial.
- **RF-3.8e** CUANDO la preparación termine en `error`, la usuaria DEBERÁ ver el motivo y poder
  pulsar «Reintentar», que vuelve a lanzar la preparación de esa misma candidatura con el mismo tope
  de coste.
- **RF-3.9** CUANDO la candidatura esté `enviada`, la usuaria DEBERÁ poder pulsar «Me han llamado»
  (pasa a `entrevista`) o «Me han rechazado» (pasa a `cerrada` con motivo `rechazo`); desde
  `entrevista`, solo «Me han rechazado». Que la empresa pida información no cambia el estado (P15).
- **RF-3.9b** `clasificador-respuesta` y el flujo `clasificar_respuesta` DEBERÁN seguir funcionando
  desde la consola y con su set de evals, sin conexión con la web hasta que Horma lea el correo
  (P7, P17): etiquetan un correo (`entrevista`, `rechazo`, `piden_informacion` u `otro`) y proponen
  la transición legal, que nunca aplican. Un correo con instrucciones NO DEBERÁ producir ninguna
  propuesta. El texto del correo NO DEBERÁ guardarse (P11).
- **RF-3.10** El tablero DEBERÁ listar las candidaturas de la usuaria en columnas por estado
  (borrador, aprobada, enviada, entrevista y «Cerradas», plegable), cada una con puesto, empresa y
  fecha del último cambio, y una marca «Te toca revisar» si su preparación quedó en
  `pendiente_de_ti`. Al abrir una candidatura DEBERÁ verse su historial. Funciona en móvil y en
  escritorio, con el marco visual del proyecto, y cada usuaria ve solo lo suyo (RLS) (P5).
- **RF-3.11** El flujo `candidatura` DEBERÁ ejecutarse en el worker desde la cola con tope de coste
  (RT-14) y desde la consola con `--paso-a-paso` (pausa entre pasos, muestra entrada y salida) y
  `--traza <dir>` (guarda cada paso como JSON). Cada agente DEBERÁ poder ejecutarse por separado
  (RT-04). El worker DEBERÁ cortar cualquier tarea antes de la siguiente llamada al modelo en cuanto
  su coste acumulado supere el tope, también cuando ningún paso falla.
- **RF-3.12** MIENTRAS Horma esté en construcción, CUANDO un set de evals se mida con el modelo
  real, el sistema DEBERÁ detenerlo si el coste acumulado supera 1 USD por ejecución y dejar
  constancia (P6). El tope de 1 USD es solo para las pruebas de construcción; el tope de uso real se
  fija al medir el coste, antes de usuarias reales.

## Criterios de aceptación (puerta de salida)
Cerrados el 16-nov-2026 para la versión anterior (606 tests, evals `cv` y `respuestas` con el modelo
real, prueba manual de Mar). Tras el bloque H se vuelven a comprobar todos:
- [ ] `horma eval correr cv` sobre los casos con errores sembrados (cifra inventada, cargo subido,
      fecha o empresa cambiadas, titulación inventada, rasgo personal, promesa, inflado, carta que
      repite el CV): `comprobar` y `juez-candidatura` rechazan el 100 %; en los casos de flujo
      completo, fechas, cargos, empresas y titulaciones idénticos al maestro al 100 % y lo que falta
      va a huecos; el caso adversario, 100 % sin efecto; en los casos de selección, el código elige
      el CV base del sector de la oferta. La cobertura ATS queda medida (sin umbral).
- [ ] `horma eval correr respuestas` sobre 15 correos inventados: etiqueta correcta ≥ 0,9; los 3
      adversarios, 100 % sin efecto.
- [ ] Los dos sets corren en CI: simulado sin clave; con modelo real y tope de coste cuando hay clave.
- [ ] Una candidatura sin problemas hace 3 llamadas al modelo y ninguna pasa de 5 (test con la puerta
      simulada); una candidatura real cuesta menos de 1 USD (medida una vez).
- [ ] Una tarea que no falla pero supera el tope se corta antes de la llamada siguiente (test).
- [ ] La máquina de estados rechaza toda transición no permitida y nadie salvo la dueña con su
      sesión aprueba (test).
- [ ] Editar el CV conserva los avisos del juez sobre la carta, y viceversa (test).
- [ ] Un test de RLS demuestra que una usuaria no lee las candidaturas ni el historial de otra, ni
      las versiones de sus CV base.
- [ ] Editar un CV base y volver después a la versión anterior deja el texto original idéntico, y
      las dos versiones siguen en el historial (test).
- [ ] Consola: `horma flujo correr candidatura --usuaria ana --oferta 123 --paso-a-paso --traza
      trazas/ana-123/`, `horma agente correr juez-candidatura --entrada caso.json`,
      `horma flujo correr clasificar_respuesta --entrada correo.json`, `horma eval correr cv`.
- [ ] Prueba manual: desde Recomendadas, preparar una candidatura; leer el CV, la carta y «Revisa
      esto»; abrir «Detalles»; editar una frase; «Aprobar y descargar» los dos PDF; marcar enviada en
      un clic; «Me han llamado»; verla en el tablero con su historial. Forzar un error y «Reintentar».

## Fuera de alcance
- LangGraph, pausa y reanudación con checkpointer: fase 4 (RF-4.1 a RF-4.3).
- Umbral de cobertura ATS: fase 4 (RF-4.4).
- Envío automático de la candidatura: plan posterior a la fase 4.
- Leer el correo de la usuaria para detectar respuestas (P7): tras cerrar privacidad y RGPD. Ahí se
  conecta `clasificador-respuesta` (P17).
- Carta nacida de una entrevista a la usuaria sobre sus valores (P1): cuando todo Horma esté construido.
- «Reabrir» una candidatura aprobada y `horma flujo correr --desde`: anotados en las aclaraciones.
- Datos de personas reales: todo es inventado hasta cerrar privacidad y RGPD.
