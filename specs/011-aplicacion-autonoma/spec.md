---
type: spec
title: aplicacion-autonoma — Spec funcional
description: Requisitos en notación EARS de la spec 011. Parte 1 (paso 1 del PRD) — medición de destinos, sin enviar nada, y mejoras pequeñas de pantalla. Las partes 2 (envío y correo en modo prueba) y 3 (envío real) se especifican al llegar su paso.
tags: [spec, envio, medicion, frontend]
status: active
sources: [../prd.md, ../constitution.md, ../system.md, ../006-rediseno-2c/spec.md, ../008-portada-ofertas/spec.md]
generated: { by: claude-code, at: 2026-11-25 }
verified: { by: human, at: 2026-11-25 }
stale_after: null
---

# aplicacion-autonoma — Especificación

**PRD:** US-001 (solo medir) · RF-001, RF-016 · NFR-09 · R-02.

## Contexto
La spec 011 se construye en tres partes, cada una en su paso del [PRD](../prd.md):

| Parte | Paso del PRD | Qué | Estado |
|---|---|---|---|
| 1 | 1 | Medición de destinos y mejoras pequeñas | **Esta spec** |
| 2 | 7 | Envío y correo, en modo prueba | Sin especificar: se escribe al llegar el paso 7 |
| 3 | 10 | Envío real | Sin especificar: se escribe al llegar el paso 10 |

La parte 1 no envía nada, no añade llamadas al modelo y no cambia la constitución ni los requisitos transversales.
Sin aclaraciones propias: las decisiones son de Mar (23 y 25-nov) y se citan aquí.

## Requisitos (EARS)

### A · Medición de destinos (PRD RF-001)
- **RF-11.1** El sistema DEBERÁ contar, sin enviar nada, a qué portal lleva el enlace de cada oferta del
  catálogo y cuántas exigen cuenta, y enseñarlo en Admin y en la consola.
- **RF-11.1b** `resolver_destino` DEBERÁ reconocer el portal por la dirección final del enlace, siguiendo las
  redirecciones, y devolver un canal o «no automático». LinkedIn e Indeed
  DEBERÁN dar siempre «no automático»; InfoJobs y Welcome to the Jungle se resuelven como cualquier portal.
- **RF-11.1c** La medición NO DEBERÁ hacer ninguna petición que no sea `GET` ni llamar al modelo.

### M · Mejoras pequeñas (PRD RF-016)
Pedidas por Mar el 23-nov. No dependen de la medición.
- **RF-11.25** CUANDO Horma quite un dato personal que no guarda, la usuaria DEBERÁ ver el aviso «Hemos quitado
  un dato personal que Horma no guarda» en la pantalla donde ocurre. Hoy se genera y no se ve.
- **RF-11.25b** Calificar una fuente DEBERÁ terminar siempre con un resultado, «apta» o «no apta» con su
  motivo. SI la fuente responde 403 (hoy, Adzuna), el resultado DEBERÁ ser «no apta» con ese motivo, no un error.
- **RF-11.26** Los botones de archivo DEBERÁN seguir la norma de los demás botones de la guía: primario si
  subir el archivo es la acción principal de la pantalla y secundario si no. «Subir mi CV» en Ofertas y
  «Elegir archivo» en Perfil DEBERÁN verse iguales en la misma situación.
- **RF-11.26b** En «Añadir oferta», el resaltado del bloque seleccionado DEBERÁ verse igual en sus cuatro lados.
- **RF-11.26c** Todas las barras (compatibilidad y avance) DEBERÁN dibujarse sin línea de borde.
- **RF-11.27** En Ofertas, la compatibilidad mínima y la máxima DEBERÁN elegirse con una sola barra de rango,
  con dos tiradores y sus dos números a la vista. DEBERÁ manejarse con el teclado y cumplir los 44 px de zona
  táctil. Sustituye a las dos casillas de RF-8.4c; el componente se añade antes a la guía (RF-6.9).
- **RF-11.28** Cada pantalla cambiada DEBERÁ comprobarse a 1280 y 390 px, en claro y en oscuro, mirando
  alineación y simetría (RF-6.4b). SI algo falla, se arregla en la misma tarea; SI no se pudo comprobar, se dice.
- **RF-11.29** *(Mar, 25-nov, D-030)* CUANDO la usuaria añada por URL una oferta cuya dirección ya añadió (se
  comparan sin los parámetros de seguimiento `utm_*`, `gclid`, `fbclid` y `msclkid`), Horma NO DEBERÁ leerla ni
  analizarla otra vez: DEBERÁ decir «Ya añadiste esta oferta el DD/MM/AAAA» con «Ver oferta» y «Leer de nuevo».
  «Leer de nuevo» DEBERÁ volver a leer la página y actualizar esa misma oferta (mismo id; sus candidaturas siguen
  enlazadas), sin crear otra; SI el texto no ha cambiado, no se analiza de nuevo. SI esa dirección ya se está
  leyendo, DEBERÁ seguirse esa lectura en vez de empezar otra.
- **RF-11.30** *(Mar, 25-nov, D-031)* Añadir una oferta DEBERÁ enseñar una sola barra «Analizando la oferta» desde
  que se pide hasta que sale en la lista: la lectura de la página y el análisis van en la misma barra, sin cambiar
  de frase y sin bajar nunca (RF-10.8c).

## Criterios de aceptación
- Con el catálogo real, Admin y la consola enseñan la tabla portal · ofertas · exige cuenta, sin coste.
- Una oferta de un portal vetado da «no automático».
- Subir un CV con un dato que Horma no guarda enseña el aviso.
- Calificar Adzuna termina en «no apta» con su motivo.
- El filtro con la barra de rango da las mismas ofertas que daban las dos casillas.
- Añadir dos veces la misma URL, con o sin `utm_*`, no la lee ni la analiza la segunda vez.
- Añadir por URL enseña una sola barra que nunca baja.

## Fuera de alcance
- Enviar candidaturas, leer correo, la regla de envío y sus ajustes: parte 2.
- Los cambios de constitución, RT-09 y RT-10 que pide el envío: parte 2.
- Elegir el primer portal real: lo decide Mar al leer la medición.

## Riesgos
- Seguir redirecciones de muchas ofertas puede ser lento o topar con límites de ritmo: se usa el límite que ya
  tiene `descargar` y la medición se puede repetir.
