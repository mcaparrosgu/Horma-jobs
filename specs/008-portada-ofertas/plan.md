---
type: plan
title: portada-ofertas — Plan técnico
description: Archivos y cambios que cubren cada requisito de la fase 8 — landing y /entrar, catálogo en Admin, oferta original, «Qué buscas», puntuación sin botón con topes, descartes, estado de candidatura y avance con % guardado por tandas.
tags: [plan, frontend, worker, flujos, migracion]
status: active
sources: [./spec.md, ./clarifications.md, ../system.md]
generated: { by: claude-code, at: 2026-11-20 }
verified: { by: human, at: 2026-11-20 }
stale_after: null
---

# portada-ofertas — Plan

## Arquitectura
Sin agentes nuevos y sin cambios en el prompt del `matcher`. Se respetan RT-01, RT-02 y RT-12: el flujo
`recomendar` sigue sin tocar la base de datos; el worker le inyecta una función que guarda cada tanda, igual
que hoy le inyecta el `proveedor`. Solo la API y el worker leen y escriben en Postgres.

| Requisito | Dónde |
|---|---|
| RF-8.1 landing y entrada | `main.py` (`/`), `static/index.html` (landing), `static/entrar.html` nuevo, `routers/paginas.py` (`/entrar`), `routers/auth.py` (callback a `/`) |
| RF-8.1e pestañas | `static/comun.js` (`PESTANAS`, marca → `/recomendadas`), `estilo.css` (rejilla móvil) |
| RF-8.2 catálogo | `static/catalogo.html` y `catalogo.js` nuevos (lo de `app.js`), ruta `/catalogo` con `exigir_admin`; `routers/ofertas.py` (`GET /ofertas` y `/ofertas/total` con `exigir_admin`; `GET /api/ofertas/propias` nuevo); `ingesta.html`, `costes.html` (subpestañas); `anadir-oferta.js` |
| RF-8.3 original | `routers/ofertas.py` (`GET /api/ofertas/{id}/original`), `repositories/ofertas.py`; `comun.js` (`verOriginal`); `recomendadas.js`, `candidatura.js`, `catalogo.js`; guía (spec 006, RF-6.4) y `estilo.css` |
| RF-8.4 «Qué buscas» | `recomendadas.html` / `.js` (panel con el formulario de `preferencias.*`, que se borran); `/preferencias` ya no existe (P20) |
| RF-8.4c-d vista | `recomendadas.js` (filtra y ordena en el navegador, `localStorage`); `routers/recomendaciones.py` (deja de aplicar rango y orden); `queue/worker.py` (rango 40-100 y orden «compatibles» fijos) |
| RF-8.5 sin botón y topes | `routers/recomendaciones.py` (`POST /api/recomendar` decide), `repositories/tareas.py`, `config.py`, `queue/worker.py` (`_PuntuarUna`) |
| RF-8.6 candidatura y descartes | migración `0020`; `repositories/descartes.py` nuevo; `routers/recomendaciones.py` (`PUT`/`DELETE /api/descartes/{oferta_id}`); `repositories/matches.py` (`listado` con candidatura y descarte) |
| RF-8.7 avance | migración `0020`; `flows/plain.py` y `flows/grafo.py` (`al_paso`); `flows/recomendar.py` (`al_tanda`); `queue/worker.py`; `routers/tareas.py` nuevo; `comun.js` (`seguirTarea`); `recomendadas.js`, `anadir-oferta.js`, `candidatura.js` |

## Datos (migración `0020_fase8_descartes_progreso.py`)
- `tareas.progreso smallint NOT NULL DEFAULT 0 CHECK (progreso BETWEEN 0 AND 100)` y
  `tareas.actualizada_en timestamptz NOT NULL DEFAULT now()`.
- Índice `tareas (usuaria_id, tipo, creada_en)`: lo usan el intervalo de 1 h y los topes del día.
- Tabla `descartes (usuaria_id, oferta_id → ofertas, creada_en, PRIMARY KEY (usuaria_id, oferta_id))`, RLS
  `propia` FOR ALL y `GRANT SELECT, INSERT, DELETE` al rol de la app (patrón de `0013`).

## Landing, entrada y Admin (RF-8.1, RF-8.2)
- `GET /`: con sesión → 302 a `/recomendadas`, o a `/perfil` si `perfiles.vigente` es `None`; sin sesión →
  `index.html`, que pasa a ser la landing (texto de RF-8.1b, solo HTML y CSS, sin JS de datos).
  `/entrar` hace lo mismo con sesión y, sin ella, sirve `entrar.html`. El callback sigue yendo a `/`, que decide.
- Landing y `/entrar` usan la cabecera de marca (RF-6.3e sustituido) con tokens y estilo de la guía; los
  bloques de «Qué hace Horma» como lista editorial; «Cómo empezar» como lista numerada.
- `PESTANAS` sin Preferencias; la rejilla móvil usa `repeat(var(--n-pestanas), 1fr)`.
- Catálogo: se mueve `app.js` a `catalogo.js` sin cambiar su contenido, más «Ver oferta original» por oferta.
  Subpestañas de Admin: Ingesta · Catálogo · Costes. `app.js` se borra.
- `GET /api/ofertas/propias`: las ofertas de la usuaria (`usuaria_id = ella`, RLS), con su estado y el avance
  de su tarea (RF-8.7). Añadir oferta deja de pedir `/ofertas`.

## Oferta original (RF-8.3)
- `GET /api/ofertas/{id}/original` con `sesion_de` (RLS): `titulo`, `empresa`, `atribucion`, `propia`,
  `fecha_publicacion`, `url` (solo si empieza por `http://` o `https://`) y `texto` (`texto_crudo`). Sin fila → 404.
- Componente «Ventana»: se generaliza el `dialog.visor` de Perfil a `dialog.ventana` (borde de 1 px, ancho de
  lectura, «Cerrar» de 44 px, Esc, foco de vuelta al botón). Se añade antes a la tabla de RF-6.4 (spec 006).
- El texto se pinta con `textContent` dentro de un bloque con `white-space: pre-wrap`; nunca `innerHTML`.

## «Qué buscas» y vista (RF-8.4)
- El formulario de `preferencias.html` (grupos con `grupoCasillas`, condiciones, sueldo) pasa a un `details`
  `#que-buscas` en Recomendadas, con «Guardar y buscar»: `PUT /api/preferencias` y luego
  `POST /api/recomendar {motivo: "buscar"}`. Abierto si todas las listas están vacías o la URL trae `#que-buscas`.
- Vista: rango, orden y estado, en una fila de rejilla (`--tap`, RF-6.4b). Se guarda en `localStorage`
  (`horma.vista.recomendadas`) dentro de `try/catch`; sin él, valores por defecto (40-100, recientes, Nuevas).
- `GET /api/recomendaciones` devuelve todo lo que pasa «Qué buscas», con `candidatura` y `descartada` por oferta;
  rango, orden y estado se aplican en el navegador. Los parámetros de URL de filtros se quitan.
- Worker: `_Recomendar` usa `prefs.model_copy(update={"rango_min": 40, "rango_max": 100, "orden": "compatibles"})`.

## Puntuar sin botón (RF-8.5)
- `config.py`: `tope_gasto_diario_puntuar = 0.50`, `max_sueltas_dia = 30`, `intervalo_recomendar_min = 60`,
  `tope_coste_puntuar_una = 0.05`. Provisionales (RF-8.5g).
- `repositories/tareas.py`:
  - `gasto_hoy(s, usuaria, tipos)`: suma de `coste_acumulado` de `recomendar`, `puntuar_propias` y `puntuar_una`
    creadas hoy, con el día en `Europe/Madrid`;
  - `ultima(s, usuaria, tipo)`, `sueltas_hoy(s, usuaria)`, `activas(s, usuaria, tipos)`;
  - `avanzar(s, tarea_id, progreso)`: `progreso = greatest(progreso, :p)`, `actualizada_en = now()`.
- `POST /api/recomendar {motivo: "abrir" | "buscar"}` responde 200 con `{tarea_id}` o `{tarea_id: null, motivo}`:
  `sin_perfil`, `en_marcha` (devuelve la tarea en curso), `sin_pendientes`, `reciente` (solo con «abrir») o
  `tope`. Las pendientes se cuentan con `buscar_ofertas` excluyendo puntuadas y descartadas, con `limite=1`.
  El tope de la tarea es `min(tope_coste_recomendar, 0,50 − gasto_hoy)`; si lo que queda es < 0,01, `tope`.
- `puntuar_propias` no mira el tope del día (RF-8.5c), pero su gasto se suma.
- «Puntuar ahora»: `POST /api/matches/{oferta_id}/puntuar` → tarea `puntuar_una` (entidad = oferta). 409 si ya
  tiene nota para la versión vigente o si la oferta está en una tarea en marcha; 429 con el texto de RF-8.5f si
  `sueltas_hoy ≥ 30`. `_PuntuarUna(_Recomendar)` carga esa oferta (RLS: catálogo o propia) y corre el flujo con
  una candidata.
- `_Recomendar.cargar` añade las descartadas a `excluir_ids`.

## Descartes y candidatura (RF-8.6)
- `PUT /api/descartes/{oferta_id}`: 409 si hay candidatura con `estado <> 'cerrada'` (P4). `DELETE` la recupera.
- `matches.listado`: `LEFT JOIN descartes` y un `LEFT JOIN LATERAL` a la candidatura de esa oferta (la abierta
  si la hay; si no, la última cerrada): `{id, estado, motivo_cierre}`.
- Recomendadas: etiqueta de estado (texto, RF-6.7e) y «Ver candidatura»; «Descartar» como botón de texto con
  aviso `role="status"` y «Deshacer»; en «Descartadas», «Recuperar».

## Avance (RF-8.7)
- **Flujos:** `PlainFlow` y `LangGraphFlow` aceptan `al_paso: Callable[[str], None] | None`, que se llama tras
  cada paso. `recomendar.crear(proveedor, al_tanda=None)`: tras cada tanda revisa sus explicaciones (RT-09, la
  revisión pasa de `revisar_explicaciones` a dentro de `puntuar_tanda`) y llama a `al_tanda(nuevas, hechas,
  previstas)`. Previstas = `min(MAX_TANDAS, ceil(pendientes / TANDA))`.
- **Worker:** `Dependencias` lleva `tarea_id`. `_Recomendar.ejecutar` pasa un `al_tanda` que, en una sesión
  propia de la usuaria, guarda la tanda (`repo_matches.guardar`, idempotente) y llama a `avanzar`. El `guardar`
  final no cambia (upsert). Con error o tope, lo guardado se queda (RF-8.7d).
  Para el resto: `al_paso` → `avanzar(hechos / len(flujo.pasos()) × 95)`; al terminar, 100.
  `procesar_oferta` es tarea del sistema: su avance lo lee `GET /api/ofertas/propias` en sesión de sistema,
  solo para los ids de la usuaria. Con URL: `leer_url` hecha = 20 % y `procesar_oferta` escala de 20 a 100.
- **API:** `GET /api/tareas/activas?tipo=` y `GET /api/tareas/{id}` (RLS `propia_o_sistema`):
  `{id, tipo, entidad_id, estado, progreso, motivo}`; el motivo, con `motivo_seguro`.
- **Pantalla:** `comun.js` añade `barraAvance(contenedor, texto)` y `seguirTarea(id, alAvanzar, alTerminar)`
  (sondeo cada 3 s mientras esté `pendiente` o `en_curso`, sin límite). Recomendadas: al cargar pide las activas;
  si no hay, `POST /api/recomendar {motivo: "abrir"}`; recarga la lista cuando sube el progreso. Componente
  «Barra de avance» (`role="progressbar"`, `aria-valuenow`, texto con el %) añadido antes a RF-6.4.

## Tests
- Migración: columnas, `CHECK`, índice y RLS de `descartes` (una usuaria no ve ni borra los de otra).
- `/`, `/entrar` y callback: sin sesión, landing; con sesión, a Recomendadas o a Perfil.
- `GET /ofertas` → 403 sin `admin`; `/api/ofertas/propias` solo devuelve las suyas.
- Original: texto completo; una propia ajena → 404; una URL `javascript:` no sale.
- `POST /api/recomendar`: cada motivo (`reciente` antes de 1 h, `buscar` se lo salta, `tope` con 0,50 gastado,
  `en_marcha`, `sin_pendientes`); el tope de la tarea es lo que queda del día.
- `puntuar_una`: la 31.ª del día → 429; ya puntuada → 409; con el tope del día alcanzado, funciona.
- Descartes: 409 con candidatura abierta; descartada no entra en `cargar` de `_Recomendar`; recuperar.
- Flujo `recomendar` simulado: `al_tanda` se llama una vez por tanda con las explicaciones ya revisadas; un
  fallo en la tercera tanda deja guardadas las dos primeras (worker); el progreso nunca baja.
- `al_paso` en `PlainFlow` y `LangGraphFlow`.
- Estáticos: sin pestaña Preferencias; Recomendadas sin «Recomendar» ni `PUT` al cambiar la vista; ventana y
  texto con `textContent`; ningún «match», «ATS» ni «trazabilidad» en la landing.
- Navegador: landing, `/entrar`, Recomendadas, Añadir oferta, Candidatura y Catálogo a 1280 y 390 px, en claro y
  en oscuro.

## Coste
- Ninguna eval real: el prompt del `matcher` no cambia (evals de `recomendacion` en simulado, en verde).
- Prueba manual: puntuaciones reales de Mar dentro del tope de 0,50 USD al día y unas pocas «Puntuar ahora»
  (~0,015 USD cada una). Se avisa antes de la prueba.
