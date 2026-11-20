---
type: spec
title: ajustes-pantalla — Spec funcional
description: Requisitos de la fase 7 en notación EARS — «Solo remoto» estricto, ofertas propias sin fecha, explicaciones en segunda persona, nombres enteros, Perfil por bloques, estilo compacto, buscador de Ingesta y menú Admin.
tags: [spec, frontend, preferencias, perfil, ingesta, matcher, extractor]
status: active
sources: [./clarifications.md, ../system.md, ../constitution.md, ../002-perfil-recomendacion/spec.md, ../005-correcciones-profesor/spec.md, ../006-rediseno-2c/spec.md]
generated: { by: claude-code, at: 2026-11-20 }
verified: { by: human, at: 2026-11-20 }
stale_after: null
---

# ajustes-pantalla — Especificación

## Contexto
Ajustes pedidos por Mar tras probar la fase 6. No hay agentes nuevos. Cambian el extractor de ofertas
(un campo) y las instrucciones del `matcher` (la persona gramatical). El resto es pantalla.
Todo lo nuevo sigue la guía de diseño de la fase 6 (RF-6.9).
Las respuestas del Clarify están en [clarifications.md](./clarifications.md) y se citan como P1…P8.

## Requisitos (EARS)

### Solo remoto (RF-7.1)
- **RF-7.1** Al procesar una oferta, Horma DEBERÁ guardar su **modalidad**: `remoto` (sin ninguna
  presencialidad obligatoria), `hibrido` (alguna presencialidad obligatoria, aunque sea ocasional),
  `presencial`, o vacío si el texto no lo dice. Vivir en un país concreto NO es presencialidad.
- **RF-7.1b** Las ofertas ya guardadas NO DEBERÁN volver a procesarse: quedan sin modalidad (P1).
- **RF-7.1c** CUANDO «Solo remoto» esté marcado (en Preferencias o en el filtro de Recomendadas), SOLO
  DEBERÁN pasar las ofertas con modalidad `remoto`. Las que no tienen el dato NO DEBERÁN pasar (P7).
  Las ofertas propias de la usuaria se filtran igual que las de Horma (ver RF-7.1f).
- **RF-7.1f** Los filtros de Preferencias y de Recomendadas (puestos, sector, contrato, nivel, país, idiomas,
  «Solo remoto», «Solo con salario», sueldo mínimo) y el rango de nota DEBERÁN aplicarse por igual a las
  ofertas propias y a las del catálogo (cambio pedido por Mar el 20-nov en la prueba manual; modifica RF-5.3e).
  Se mantiene que a las propias no se les exige «recomendable», y que se ven con su aviso del auditor.
- **RF-7.1d** La casilla DEBERÁ explicar en una línea: «Solo ofertas 100 % en remoto. Si piden ir a la
  oficina alguna vez, no salen.»
- **RF-7.1e** Donde hoy se enseña «Remoto», DEBERÁ enseñarse la modalidad: «Remoto», «Híbrido» o
  «Presencial»; sin dato, nada.

### Ofertas propias sin fecha (RF-7.2)
- **RF-7.2** SI una oferta propia (pegada o por URL) no trae fecha de publicación, ENTONCES NO DEBERÁ
  marcarse fantasma por ese motivo (P2). «Repetida» y «genérica» siguen igual.
- **RF-7.2b** SI una oferta propia no trae fecha, la pantalla DEBERÁ decir «No consta fecha de
  publicación» y NO DEBERÁ enseñar la fecha en que se añadió como si fuera la de publicación.
- **RF-7.2c** Las ofertas de la ingesta NO cambian.

### Segunda persona (RF-7.3)
- **RF-7.3** La explicación de compatibilidad DEBERÁ hablar a la usuaria en segunda persona («tienes
  experiencia en…»), sin su nombre ni la tercera persona. Las explicaciones ya guardadas no se rehacen (P6).

### Nombres enteros (RF-7.4)
- **RF-7.4** En todas las pantallas, los idiomas y los países DEBERÁN mostrarse con su nombre entero en
  español («Inglés», «España»). Por dentro se siguen guardando los códigos. SI un código no tiene nombre
  conocido, se muestra tal cual.

### Perfil (RF-7.5)
- **RF-7.5** Perfil DEBERÁ mostrar sus apartados en bloques separados visualmente, en este orden (P3):
  1. Tus CV, abierto;
  2. Mi perfil, abierto;
  3. Preguntas pendientes, desplegable, con el número en el título; abierto CUANDO haya alguna;
  4. Tu estilo de redacción, desplegable, cerrado.
- **RF-7.5b** El aviso de Mi perfil DEBERÁ decir el texto de P4, literal.
- **RF-7.5c** Tu estilo DEBERÁ resumirse (P5):
  - una frase con registro, persona, longitud de frase y forma de las viñetas;
  - «Usas» y «Evitas», con 5 rasgos como máximo cada uno;
  - «Ver detalle», que despliega la lista completa con sus citas.

  «Editar guía» y «Volver a analizar» se mantienen. El agente no cambia.

### Ingesta (RF-7.6)
- **RF-7.6** La lista de fuentes DEBERÁ tener un buscador por nombre (sin distinguir mayúsculas ni tildes)
  y un filtro: Todas · Activas · Inactivas · No aptas · Sin calificar.
- **RF-7.6b** CUANDO el filtro deje la lista vacía, DEBERÁ decirlo («Ninguna fuente coincide»).

### Menú Admin (RF-7.7)
- **RF-7.7** CUANDO entre una administradora, la cabecera DEBERÁ mostrar una pestaña «Admin», la
  última. Lleva a Ingesta, y desde Ingesta y Costes se pasa de una a otra.
- **RF-7.7b** A quien no sea administradora NO DEBERÁ mostrársele «Admin», ni Ingesta ni Costes en ningún
  menú. El servidor sigue respondiendo 403 (RF-1.10, RF-4.7).

## Criterios de aceptación
- Una oferta híbrida nueva no sale con «Solo remoto»; una remota nueva sí; una antigua sin modalidad, no.
- Una oferta pegada sin fecha no lleva «posible fantasma» y dice «No consta fecha de publicación».
- Una explicación nueva dice «tienes…» y no el nombre de la usuaria.
- Ningún código de idioma o país a la vista en Preferencias, Recomendadas, Candidaturas ni Perfil.
- Perfil en el orden de P3, con el texto de P4 y el estilo en una sola pantalla de móvil, cerrado.
- Ingesta filtra y busca. «Admin» solo con una cuenta de `HORMA_ADMINS`.
- Evals de `ofertas` y `recomendacion` con el modelo real en su umbral.
- Todo comprobado a 1280 y 390 px, en claro y en oscuro (RF-6.4b).

## Fuera de alcance
- Casillas de híbrido y presencial (P7).
- Volver a procesar o volver a puntuar ofertas guardadas (P1, P6).
- Landing, «Ver oferta original» y unir Preferencias con Recomendadas: fase 8.
