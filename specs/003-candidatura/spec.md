---
type: spec
title: candidatura — Spec funcional
description: Requisitos funcionales de la fase 3 (CV y carta adaptados con verificador y juez, aprobación, envío por cuenta propia y seguimiento en un tablero), en notación EARS.
tags: [spec, candidatura, seguimiento]
status: active
sources: [./clarifications.md, ../system.md, ../002-perfil-recomendacion/spec.md, ../../docs/Horma v2_ requerimientos por fases.pdf]
generated: { by: claude-code, at: 2026-11-15 }
verified: { by: human, at: 2026-11-15 }
stale_after: null
---

# candidatura — Especificación

## Contexto
La usuaria elige una oferta recomendada. Horma elige el más adecuado de sus CV base, le prepara un
CV y una carta adaptados a esa oferta, los comprueba con código (verificador) y con un segundo
agente (juez), y le deja un borrador. Ella lo revisa, lo corrige si hace falta (y puede guardar la
corrección encima de su CV base), lo aprueba, descarga los PDF, envía la candidatura por su cuenta
y la sigue en un tablero. Cuando una empresa contesta, pega la respuesta y Horma le propone
el cambio de estado, que ella confirma.

Entran el flujo `candidatura` (el único con bucle, el que define cómo tiene que ser `Flow` para que
LangGraph lo sustituya en la fase 4), el flujo `clasificar_respuesta` y seis agentes:
`selector-cv-base`, `redactor-cv`, `juez-cv`, `redactor-carta`, `juez-carta` y
`clasificador-respuesta`. Los requisitos
transversales (RT-xx) están en [system.md](../system.md) y las respuestas del Clarify en
[clarifications.md](./clarifications.md) (se citan como P1…P11).

## Requisitos (EARS)

### Flujo `candidatura`
- **RF-3.1** El flujo `candidatura` DEBERÁ tener un estado tipado (`EstadoCandidatura`) y pasos con
  nombre: `elegir_cv_base` → `redactar_cv` → `verificar` → `juzgar_cv` → (`redactar_cv` si hay que
  corregir) → `medir_ats` → (`redactar_cv` si faltan palabras clave con origen) → `redactar_carta` →
  `verificar_carta` → `juzgar_carta` → (`redactar_carta` si hay que corregir) → `componer`. El CV
  DEBERÁ redactarse como máximo 3 veces (la primera y 2 vueltas de corrección, incluida la que pida
  `medir_ats`) y la carta como máximo 2 (una vuelta). El flujo DEBERÁ terminar en `lista` si el
  último veredicto de los dos jueces es «aprobado» y la verificación no deja errores, o en
  `pendiente_de_ti` si no; en los dos casos la candidatura queda en `borrador` (P4).
- **RF-3.1b** `elegir_cv_base` DEBERÁ elegir, con el agente `selector-cv-base`, el CV base de la
  usuaria más adecuado para la oferta (sector, puesto y requisitos) y anotar el motivo en una frase;
  la usuaria NO lo elige. El código DEBERÁ comprobar que el elegido es suyo, no está rechazado y
  estaba entre los candidatos; SI no lo cumple, ENTONCES el flujo DEBERÁ terminar en error sin
  redactar. Con un solo CV base válido NO DEBERÁ llamarse al modelo. Si el CV base elegido es de una
  versión anterior del perfil, NO DEBERÁ mostrarse aviso: el redactor también parte del CV maestro,
  que siempre está al día (P9).
- **RF-3.2** `redactor-cv` DEBERÁ adaptar el CV base a la oferta aplicando la regla de los huecos:
  cambia qué se muestra y cómo se cuenta, nunca fechas, cargos, empresas ni titulaciones. Lo que la
  oferta pide y el perfil no tiene DEBERÁ ir a `huecos` con una propuesta para la usuaria, nunca al
  CV. Cada frase DEBERÁ llevar en la traza el fragmento literal del que sale.
- **RF-3.3** `verificar_trazabilidad` (código) DEBERÁ comprobar que fechas, cargos, empresas y
  titulaciones son idénticos a los de las fuentes y que cada entrada de la traza apunta a un
  fragmento real. Las fuentes válidas son el CV maestro y el CV base elegido; si la usuaria lo
  editó, su texto cuenta con origen «usuaria» (P9). SI falla, ENTONCES DEBERÁ devolver la lista de
  errores al redactor para la vuelta siguiente.
- **RF-3.4** `juez-cv` DEBERÁ devolver un veredicto (`aprobado` o `corregir`) y una lista tipada de
  problemas (`sin_origen`, `inflado`, `promesa`, `rasgo_personal`), cada uno con la frase afectada,
  y NUNCA DEBERÁ reescribir el CV.
- **RF-3.5** `medir_ats` (código) DEBERÁ comprobar el formato ATS (sin tablas, imágenes ni HTML;
  encabezados estándar) y calcular la cobertura de las palabras clave de la oferta (requisitos y
  stack). Las palabras que falten y tengan origen en las fuentes DEBERÁN sugerirse al redactor en
  una vuelta más si quedan vueltas; las que no tengan origen DEBERÁN quedar en `huecos` y NO DEBERÁN
  insertarse. La cobertura se mide y se guarda; su umbral se fija en la fase 4 (RF-4.4).
- **RF-3.6** `redactor-carta` DEBERÁ escribir la carta a partir del CV maestro, el CV adaptado, la
  oferta y el sector, sin carta base (P1). NO DEBERÁ repetir el CV. Cada frase con un dato DEBERÁ
  llevar su fragmento en la traza; el saludo y la despedida DEBERÁN salir de una lista cerrada de
  fórmulas. `verificar_carta` (código) DEBERÁ aplicar las mismas comprobaciones que RF-3.3 con el CV
  maestro, el CV base elegido y la oferta como fuentes. `juez-carta` DEBERÁ seguir el patrón de
  `juez-cv`, con el problema añadido `repite_cv`.
- **RF-3.6b** CUANDO una oferta o un CV contenga instrucciones dirigidas a una IA, los agentes
  DEBERÁN registrarlas en `instrucciones_embebidas` y NO DEBERÁN ejecutarlas (RT-07). El CV y la
  carta NO DEBERÁN mencionar rasgos personales (RT-09).

### Candidatura y seguimiento
- **RF-3.7** La `Candidatura` DEBERÁ seguir la máquina de estados `borrador → aprobada → enviada →
  entrevista`. Desde cualquier estado la usuaria DEBERÁ poder pasarla a `cerrada` con un motivo
  (`rechazo`, `descartada` o `retirada`); `cerrada` es final (P8). Cualquier otra transición DEBERÁ
  rechazarse. Cada transición DEBERÁ quedar en el historial con su fecha.
- **RF-3.7b** CUANDO la usuaria pulse «Preparar candidatura» en una oferta recomendada, el sistema
  DEBERÁ crear la candidatura y lanzar su preparación sin pedirle que elija CV base. SI no tiene
  ningún CV base válido, ENTONCES DEBERÁ pedirle que genere uno primero. NO DEBERÁ haber dos
  candidaturas no cerradas para la misma oferta (P9).
- **RF-3.8** MIENTRAS la candidatura esté en `borrador`, la usuaria DEBERÁ poder ver qué CV base
  eligió Horma y por qué, el CV y la carta adaptados, los huecos con su propuesta y los avisos
  (errores de verificación y problemas de los jueces), editarlos a mano o descartarla (P4). Lo que
  ella escribe lleva origen «usuaria» y vuelve a pasar `verificar_trazabilidad`, sin llamar al
  modelo. CUANDO haya editado el CV adaptado, DEBERÁ poder guardarlo encima del CV base del que
  partió, poniéndole el nombre que quiera (por defecto, el que ya tenía; único en su cuenta, como
  RF-2.1b), para que las próximas candidaturas partan de ese texto (P9b).
- **RF-3.8d** CUANDO se sobrescriba un CV base (al guardar encima desde una candidatura o al
  editarlo, RF-2.9e), el sistema DEBERÁ guardar antes la versión anterior (texto, nombre, fecha y
  origen: candidatura o edición manual) en su historial. La usuaria DEBERÁ poder ver ese historial,
  con lo añadido y lo quitado marcado entre cada versión y la siguiente, y volver a cualquier
  versión; volver DEBERÁ guardar antes la versión actual, de modo que ningún texto se pierda. Solo
  la dueña ve su historial (RLS). Al eliminar un CV base se elimina también su historial. Solo la dueña, con su sesión, DEBERÁ poder
  aprobar; SI hay avisos, ENTONCES DEBERÁ marcar «He revisado los avisos» antes (P10). Al aprobar
  elige entre el CV adaptado y uno de sus CV estéticos.
- **RF-3.8b** CUANDO la candidatura esté `aprobada` o en un estado posterior, la usuaria DEBERÁ poder
  descargar el CV adaptado y la carta en PDF (P2); si eligió un CV estético, se descarga su archivo
  tal cual. Después envía por su cuenta y marca la candidatura como `enviada` con fecha y canal
  (`correo`, `web`, `linkedin` u `otro` con texto corto opcional; lista ampliable, P3).
- **RF-3.8c** MIENTRAS una candidatura no esté `aprobada` por su dueña, el sistema NO DEBERÁ marcarla
  como enviada, servir sus PDF ni exponerla a terceros (RT-10).
- **RF-3.9** CUANDO la usuaria pegue la respuesta de una empresa, `clasificador-respuesta` DEBERÁ
  etiquetarla (`entrevista`, `rechazo`, `piden_informacion` u `otro`) y el sistema DEBERÁ proponer
  la transición que corresponda (entrevista → `entrevista`; rechazo → `cerrada` con motivo
  `rechazo`; piden información → solo una nota en el historial; otro → nada), solo si es legal desde
  el estado actual. Ella la confirma o la descarta. Un correo que contenga instrucciones NO DEBERÁ
  producir ningún cambio por sí solo. El texto del correo NO DEBERÁ guardarse: solo la etiqueta, la
  fecha y la transición (P11).
- **RF-3.10** El tablero DEBERÁ listar las candidaturas de la usuaria en columnas por estado
  (borrador, aprobada, enviada, entrevista y «Cerradas», plegable), cada una con puesto, empresa y
  fecha del último cambio, y una marca «Te toca revisar» si su preparación quedó en
  `pendiente_de_ti`. Al abrir una candidatura DEBERÁ verse su historial. Funciona en móvil y en
  escritorio, con el marco visual del proyecto, y cada usuaria ve solo lo suyo (RLS) (P5).
- **RF-3.11** El flujo `candidatura` DEBERÁ ejecutarse en el worker desde la cola con tope de coste
  (RT-14) y desde la consola con `--paso-a-paso` (pausa entre pasos, muestra entrada y salida) y
  `--traza <dir>` (guarda cada paso como JSON). Cada agente nuevo DEBERÁ poder ejecutarse por
  separado (RT-04).
- **RF-3.12** MIENTRAS Horma esté en construcción, CUANDO un set de evals se mida con el modelo
  real, el sistema DEBERÁ detenerlo si el coste acumulado supera 1 USD por ejecución y dejar
  constancia (P6). El tope de 1 USD es solo para las pruebas de construcción; el tope de uso real se
  fija al medir el coste, antes de usuarias reales.

## Criterios de aceptación (puerta de salida)
- [ ] `horma eval correr cv` sobre 12 casos con errores sembrados (cifra inventada, cargo subido,
      fecha o empresa cambiadas, titulación inventada, rasgo personal, promesa, inflado, carta que
      repite el CV): verificador y jueces rechazan el 100 %; en los casos de flujo completo, fechas,
      cargos, empresas y titulaciones idénticos al maestro al 100 % y lo que falta va a huecos; el
      caso adversario, 100 % sin efecto. La cobertura ATS queda medida (sin umbral).
- [ ] `horma eval correr respuestas` sobre 15 correos inventados: etiqueta correcta ≥ 0,9; los 3
      adversarios, 100 % sin efecto.
- [ ] Los dos sets corren en CI: simulado sin clave; con modelo real y tope de coste cuando hay clave.
- [ ] La máquina de estados rechaza toda transición no permitida y nadie salvo la dueña con su
      sesión aprueba (test).
- [ ] El texto de un correo pegado no queda guardado en ninguna tabla, ni con éxito ni con error (test).
- [ ] Un test de RLS demuestra que una usuaria no lee las candidaturas ni el historial de otra, ni
      las versiones de sus CV base.
- [ ] Guardar encima de un CV base y volver después a la versión anterior deja el texto original
      idéntico, y las dos versiones siguen en el historial (test).
- [ ] Consola: `horma flujo correr candidatura --usuaria ana --oferta 123 --paso-a-paso --traza
      trazas/ana-123/`, `horma agente correr juez-cv --entrada caso.json`, `horma eval correr cv`.
- [ ] Prueba manual: desde Recomendadas, preparar una candidatura y ver qué CV base eligió Horma y
      por qué; ver huecos y avisos; editar y guardar la edición encima del CV base con un nombre
      nuevo; ver en el historial del CV base lo añadido y lo quitado y volver a la versión
      anterior; aprobar; descargar los PDF; marcar enviada con canal y fecha; pegar una
      respuesta y confirmar el cambio; verla en el tablero con su historial.

## Fuera de alcance
- LangGraph, pausa y reanudación con checkpointer: fase 4 (RF-4.1 a RF-4.3).
- Umbral de cobertura ATS: fase 4 (RF-4.4).
- Envío automático de la candidatura: plan posterior a la fase 4.
- Leer el correo de la usuaria para detectar respuestas (P7): tras cerrar privacidad y RGPD.
- Carta nacida de una entrevista a la usuaria sobre sus valores (P1): cuando todo Horma esté construido.
- «Reabrir» una candidatura aprobada y `horma flujo correr --desde`: anotados en las aclaraciones.
- Datos de personas reales: todo es inventado hasta cerrar privacidad y RGPD.
