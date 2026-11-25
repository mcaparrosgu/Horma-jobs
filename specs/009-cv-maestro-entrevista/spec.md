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
- **RF-9.3b** *(cambiado por la spec 012, RF-12.6: solo llegan marcados los de nivel 1)* «Qué buscas» DEBERÁ separar **Área** (las 19 familias de hoy) y **Puestos** (títulos). Los
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
- **RF-9.4** *(sustituido en parte por la spec 010, RF-10.4)* «Tu CV maestro» DEBERÁ enseñar el CV maestro de la última versión del perfil con formato
  (títulos, listas, párrafos), su fecha y su número de versión (P12), y la frase «Es el texto del que Horma saca
  tus CV y cartas. Se cambia desde Mi perfil.»
- **RF-9.4b** Cada sección DEBERÁ tener «Editar», que lleva a esa sección de Mi perfil. El texto NO DEBERÁ
  poder editarse aquí (RF-5.1b).
- **RF-9.4c** Lo que se ve DEBERÁ ser exactamente lo que usan los redactores, y solo lo ve su dueña (RLS).
  Se muestra sin interpretar HTML (RF-8.3b).

### Perfil en 9a (RF-9.5)
- **RF-9.5** *(sustituido por la spec 010, RF-10.5b)* Perfil DEBERÁ mostrar sus bloques en este orden (sustituye a RF-7.5):
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

**Sin construir. Retirada el 25-nov-2026:** la entrevista se especifica de nuevo en la spec 016 (paso 6 del
[PRD](../prd.md)), solo con texto y dictado. Lo que este documento dice de la 9b en el contexto queda como historia.

---

## Fuera de alcance
- Accesibilidad específica para personas sordas o ciegas en la entrevista (P4).
- Entrevista en otros idiomas oficiales de España (P4).
- Simulacro de entrevista para una oferta concreta (P16).
- Entrevista por llamada de voz en vivo (P18): idea futura; costaría varios euros por sesión frente a céntimos.
- Más tandas de preguntas a petición (P14).
- Revisar cómo el extractor asigna la familia a cada oferta (P10).
- Descargar el CV maestro (P12).
