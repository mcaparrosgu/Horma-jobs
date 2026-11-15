---
type: clarifications
title: candidatura — Aclaraciones
description: Preguntas abiertas de la fase 3 resueltas con la persona antes de escribir la spec, más los supuestos.
tags: [clarify, candidatura, seguimiento]
status: active
sources: [../system.md, ../002-perfil-recomendacion/clarifications.md, ../../docs/Horma v2_ requerimientos por fases.pdf]
generated: { by: claude-code, at: 2026-11-15 }
verified: { by: human, at: 2026-11-15 }
stale_after: null
---

# candidatura — Aclaraciones

## Preguntas y respuestas
- P1: El PDF parte de una «carta base del sector» (RF-3.6) que ningún agente de la fase 2 genera. → R: **sin carta base**: `redactor-carta` escribe desde el CV adaptado, la oferta y el sector. Cambia el RF-3.6 del PDF (el pedido gana). Para que no repita el CV, el prompt lo prohíbe y `juez-carta` añade el problema «repite el CV». La carta nacida de una entrevista a la usuaria queda fuera de la fase (ver «Fuera de alcance»).
- P2: ¿Formato de descarga del CV adaptado y la carta (RF-3.8)? → R: **PDF**, generado por código fuera del agente. Sin .docx. (Corregido al planificar: el PDF lo hace una herramienta nueva, `generar_pdf`; `convertir_cv` solo lee CV y no escribe PDF.)
- P3: ¿Cómo se elige el canal de envío? → R: **lista cerrada ampliable**: correo, web de la empresa, LinkedIn y «otro» (texto corto opcional), más la fecha. El futuro envío automático podrá añadir su propio valor sin cambiar la máquina de estados.
- P4: ¿Qué puede hacer la usuaria en `pendiente_de_ti`? → R: **ver los problemas y los huecos, editar a mano o descartar**. Si edita el CV, vuelve a pasar `verificar_trazabilidad` (código). No hay botón de reintento ni gasto extra de modelo.
- P5: ¿Cómo es el tablero (RF-3.10)? → R: **por descripción**, con el marco Passe-Partout: una columna por estado (borrador, aprobada, enviada, entrevista), tarjeta con puesto, empresa y fecha del último cambio, e historial al abrir la candidatura. Mar lo corrige al verlo en el navegador.
- P6: ¿Tamaño de los evals y tope de coste? → R: **12 variantes de CV con errores sembrados** (`evals/cv/`) y **15 correos** (`evals/respuestas/`, 3 con instrucciones escondidas); **tope de 1 USD por ejecución de eval**. El tope por candidatura completa se fija en el plan. (Precisado por Mar al revisar la spec: el tope de 1 USD es **solo para las pruebas durante la construcción**; el tope de uso real se fija al medir el coste, antes de usuarias reales.)
- P7: Mar propuso que Horma lea su correo para comprobar si las empresas han contestado. → R: **en la fase 3 la usuaria pega la respuesta (RF-3.9); el acceso al correo queda para después** de cerrar privacidad y RGPD (permiso restringido de Gmail, datos del art. 9, correo como texto no fiable). El estado de la candidatura debe poder recibir la respuesta de cualquier origen.
- P8: La máquina borrador → aprobada → enviada → entrevista no tiene sitio para un rechazo de la empresa ni para una candidatura que la usuaria descarta. → R: **un 5.º estado final, `cerrada`, con motivo** (`rechazo`, `descartada` o `retirada`), al que se llega desde cualquier estado. En el tablero, columna plegable «Cerradas». Cambia el esquema `Candidatura` de `system.md`.
- P9: ¿De qué CV parte cada candidatura? (En la fase 2 la usuaria puede editar un CV base, RF-2.9e, y ese texto ya no está en el CV maestro.) → R: **el agente elige el CV base más adecuado**, no la usuaria (cambiado por Mar al revisar la spec, 15-nov-2026): `selector-cv-base` compara sus CV base con la oferta y la candidatura muestra cuál eligió y por qué. Un CV base editado cuenta como fuente válida igual que el maestro (origen «usuaria»). Si no tiene ninguno, se le pide generar uno primero.
- P9b: (Añadida por Mar al revisar la spec.) ¿Qué pasa con lo que la usuaria edita en un CV adaptado? → R: **puede guardarlo encima del CV base** del que partió, con el nombre que ella quiera, para que las próximas candidaturas partan ya de ese texto y no tenga que corregirlo otra vez. **La versión anterior no se pierde**: cada CV base tiene un historial de versiones (fecha, origen y nombre), con lo añadido y lo quitado marcado respecto a la versión siguiente, y la usuaria puede volver a cualquiera.
- P10: ¿Qué impide aprobar si la usuaria edita a mano y su texto no está en el maestro? → R: **avisos; decide ella**. Lo que escribe lleva origen «usuaria», como en el perfil. Los errores de `verificar_trazabilidad` y los problemas del juez se muestran, y para aprobar marca «He revisado los avisos». La IA nunca aprueba (RT-10).
- P11: ¿Se guarda el texto del correo que pega la usuaria? → R: **no; solo etiqueta, fecha y transición** en el historial (minimización de datos: un correo puede traer datos de terceros). El texto vive solo mientras el worker lo clasifica y se borra al acabar, con éxito o con error.

## Decisiones derivadas
- `redactor-carta` recibe CV maestro, CV adaptado, oferta y sector; no hay carta base ni plantillas por sector.
- El estado `enviada` guarda fecha y canal; el canal es un enumerado ampliable.
- `pendiente_de_ti` es un estado terminal del flujo, no de la máquina de la candidatura (borrador → aprobada → enviada → entrevista, y `cerrada` desde cualquiera). La candidatura guarda los dos por separado: `estado` (la máquina) y `preparacion` (el resultado del flujo).
- `elegir_cv_base` llama a `selector-cv-base` (modelo pequeño) y el código valida lo que elige: que sea suyo, no rechazado y de su lista. Con un solo CV base no se llama al modelo (P9).
- Guardar encima de un CV base guarda antes la versión anterior en su historial. Lo añadido y lo quitado se calcula con código al mostrarlo; no se guarda. Volver a una versión también guarda antes la actual, así que ningún texto se pierde. El historial cubre también la edición manual de la fase 2 (RF-2.9e), porque las dos usan la misma función del repositorio (P9b).
- Las fuentes válidas de una frase son el CV maestro y el CV base elegido; para la carta, también la oferta (P9).
- La respuesta de la empresa solo propone; la transición la confirma la usuaria (RF-3.9, P11).

## Fuera de alcance (anotado, no se construye aquí)
- Entrevista a la usuaria sobre sus valores y su personalidad para redactar cartas personalizadas (anotada en la bitácora el 15-nov-2026; enlaza con la «entrevista del perfil» del plan posterior del PDF). Se retoma cuando todo Horma esté construido.
- Envío automático de la candidatura (plan posterior a la fase 4).
- Lectura del correo de la usuaria para detectar respuestas de empresas (P7).
- «Reabrir» una candidatura aprobada para volver a editarla: en esta fase solo se edita en `borrador` (decidido al planificar; revisable).
- `horma flujo correr --desde <paso>` (reanudar desde una traza): está en la consola del PDF, pero no lo pide RF-3.11.

## Supuestos (revisables)
- El umbral de cobertura ATS no se fija ahora: se fija con las primeras ejecuciones (RF-4.4).
- El CV estético que la usuaria puede elegir al aprobar (RF-3.8) es el ya subido en la fase 2; no se genera ninguno nuevo.
- Máximo 2 vueltas de corrección del CV y 1 de la carta, como en el PDF. La vuelta que pide `medir_ats` cuenta dentro de las 2 del CV (decidido al planificar).
