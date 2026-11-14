---
type: spec
title: ofertas — Spec funcional
description: Requisitos funcionales de la fase 1 (ofertas vivas, auditadas y clasificadas), en notación EARS.
tags: [spec, ofertas]
status: draft
sources: [./clarifications.md, ../system.md]
generated: { by: claude-code, at: 2026-11-12 }
verified: { by: human, at: null }
stale_after: null
---

# ofertas — Especificación

## Contexto
Horma tiene ofertas vivas: llegan de fuentes registradas (o de una empresa con clave), pasan por
tres agentes y se ven con su auditoría. Entra el primer flujo, `procesar_oferta` (sin bucle), y con
él la interfaz `Flow`. Las ofertas forman un catálogo común. Los requisitos transversales (RT-xx)
están en [system.md](../system.md).

## Requisitos (EARS)
- **RF-1.1** El sistema DEBERÁ mantener una tabla `fuentes` (nombre, web, URL, método, parámetros, cabeceras, variable de entorno con la clave, mapeo de campos, activa), sembrada desde `config/endpoints.json` y editable desde el dashboard de ingesta.
- **RF-1.2** CUANDO se lance `horma ingestar <fuente>` o el botón del dashboard, el sistema DEBERÁ llamar al endpoint de esa fuente, normalizar cada oferta a texto crudo y entregarla por `POST /ofertas`; el proceso de ingesta NO DEBERÁ tener credenciales de la base de datos.
- **RF-1.3** `POST /ofertas` DEBERÁ aceptar una clave de API limitada por alcance, guardada como hash y rotable (crear y revocar), con límite de tamaño y de ritmo; es también la ruta por la que una empresa publica mientras no hay portal.
- **RF-1.4** CUANDO entre una oferta cruda, el worker DEBERÁ ejecutar el flujo `procesar_oferta` (extraer → verificar origen → auditar → comprobar empresa → clasificar → componer) y guardar la `Oferta` completa; SI un paso falla, ENTONCES la oferta DEBERÁ quedar en `error` con el paso y el motivo.
- **RF-1.5** `auditor-oferta` DEBERÁ marcar oferta fantasma (sin fecha, repetida, genérica), señales de fraude (pide dinero o datos bancarios, con cita literal), empresa validada (dominio real, comprobado por código) y transparencia salarial (publicado o no, rango y frase para pedirlo).
- **RF-1.6** `clasificador-oferta` DEBERÁ asignar sector, familia de puesto, nivel y stack según `horma/schemas/taxonomia.py`, la misma que usarán los perfiles.
- **RF-1.7** CUANDO se califique una URL (`horma fuente calificar <url>` o el dashboard), `auditor-fuentes` DEBERÁ leer las condiciones de uso y el `robots.txt` y guardar una `CalificacionFuente`; solo una fuente con calificación apta PODRÁ activarse. LinkedIn e Indeed quedan excluidos por regla, sin llamar al modelo.
- **RF-1.8** El dashboard de ingesta DEBERÁ mostrar fuentes, última ejecución, ofertas por estado y errores, y permitir lanzar una ingesta; el botón deja una ejecución en la cola y no ejecuta la ingesta.
- **RF-1.9** Las ofertas fantasma o fraudulentas DEBERÁN quedar marcadas y fuera de la recomendación (`recomendable = falso`); una oferta sin salario no se descarta, sale marcada.
- **RF-1.10** SI una usuaria sin rol de administradora intenta usar el dashboard o sus rutas, ENTONCES el sistema DEBERÁ responder 403.
- **RF-1.11** CUANDO una fuente entregue una oferta que ya entregó (mismo `id_externo`), el sistema NO DEBERÁ duplicarla; CUANDO dos ofertas tengan el mismo texto normalizado, la más nueva DEBERÁ marcarse como repetida.
- **RF-1.12** El sistema DEBERÁ permitir ejecutar `procesar_oferta` y `calificar_fuente` desde la consola paso a paso, mostrando entrada y salida de cada paso y guardando la traza (RT-05).

## Criterios de aceptación (puerta de salida)
- [x] `horma eval correr ofertas` sobre 25 casos inventados: precisión ≥ 0,9 por campo y adversarias al 100 %. *Medido con el modelo real el 14-nov-2026: aprobado (campos ≥ 0,96, adversarias 1,0).*
- [x] `horma eval correr fuentes` sobre 5 portales inventados con su calificación esperada. *Medido con el modelo real el 14-nov-2026: aprobado (todo a 1,0).*
- [x] Ambos sets corren en CI (simulado sin clave; real con clave de presupuesto limitado). *`ANTHROPIC_API_KEY` es secreto del repositorio desde el 14-nov-2026: el CI mide con el modelo real.*
- [x] Consola: `horma ingestar <fuente> --limite 20`, `horma agente correr auditor-oferta --entrada oferta.json`, `horma flujo correr procesar_oferta --entrada oferta.md --paso-a-paso`, `horma fuente calificar <url>`.

## Fuera de alcance
- Perfil, recomendación y candidaturas (fases 2-3); aquí solo se deja `recomendable` calculado.
- Portal de empresas: la empresa publica con una clave de alcance `ofertas`.
- Programar ingestas periódicas: en esta fase se lanzan a mano.
