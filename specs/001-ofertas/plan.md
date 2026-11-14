---
type: plan
title: ofertas — Plan técnico
description: Arquitectura, contratos y modelo de datos que cubren cada requisito de la fase 1.
tags: [plan, ofertas]
status: active
sources: [./spec.md, ./clarifications.md, ../system.md]
generated: { by: claude-code, at: 2026-11-12 }
verified: { by: human, at: 2026-11-14 }
stale_after: null
---

# ofertas — Plan

## Arquitectura
Se añade a lo de la fase 0:

```
horma/
  schemas/   oferta.py (+ Auditoria, Oferta), taxonomia.py, fuente.py (Fuente, CalificacionFuente)
  agents/    auditor_oferta/, clasificador_oferta/, auditor_fuentes/
  tools/     origen_oferta.py, dominio.py, robots.py, descargar.py, normalizar.py
  flows/     base.py (Flow, ErrorDePaso), plain.py (PlainFlow), procesar_oferta.py, calificar_fuente.py
  ingesta.py cliente sin BD: lee el endpoint, normaliza y entrega por HTTP a la API
  cli.py     + flujo listar/correr, ingestar, fuente calificar
  web/       routers/ingesta.py (dashboard, claves, ejecuciones), auth/claves.py, static/ingesta.*
config/endpoints.json   semilla de `fuentes`
evals/ofertas/ (25 casos) · evals/fuentes/ (5 casos)
```

- **Camino de una oferta:** fuente → `horma ingestar` (sin BD) → `POST /ofertas` con clave → API guarda la oferta `pendiente` y encola una tarea `procesar_oferta` con el id → el worker ejecuta el flujo → guarda la `Oferta` completa y sus `origen`.
- **Ingesta sin credenciales de BD:** el proceso de ingesta solo conoce `HORMA_API_URL`, `HORMA_CLAVE_INGESTA` y las claves de las fuentes. Pide la ejecución y la configuración de la fuente a la API, y le entrega las ofertas. El botón del dashboard crea una ejecución `pendiente`; `horma ingestar --escuchar` (servicio `ingestor` de Compose) la recoge.
- **Calificar:** la consola y el dashboard piden la calificación a la API; el worker ejecuta `calificar_fuente` y la guarda. Con `--local`, la consola corre el flujo en su proceso y solo imprime (no guarda).
- **Modo sistema:** las sesiones de BD que no actúan por una usuaria fijan `app.sistema = on`. Como en la fase 0, la RLS protege de errores del código, no de un rol comprometido.

## Flujos
`PlainFlow(nombre, pasos, aristas, inicio, finales)`: `run(estado)` recorre las aristas; `run_step(paso, estado)` ejecuta uno; `pasos()` los lista en orden. Un fallo en un paso se lanza como `ErrorDePaso(paso, causa)`. Las dependencias (proveedor del modelo, resolvedor DNS, descargador) se inyectan al construir el flujo.

| Flujo | Pasos |
|---|---|
| `procesar_oferta` | `extraer` (extractor-oferta) → `verificar_origen` (código, RT-08) → `auditar` (auditor-oferta) → `comprobar_empresa` (DNS) → `clasificar` (clasificador-oferta) → `componer` (código) |
| `calificar_fuente` | `regla_exclusion` (LinkedIn/Indeed → fin) → `descargar` (condiciones + robots.txt) → `auditar` (auditor-fuentes) → `robots` (urllib.robotparser) → `decidir` |

`componer` decide lo determinista: fantasma = sin fecha ∨ repetida ∨ genérica; solo conserva señales de fraude, dominio y stack que aparecen literalmente en el texto; `salario_publicado`, rango y frase para pedirlo; `recomendable = ¬fantasma ∧ ¬fraude`.

## Contratos
**Esquemas**
- `Auditoria`: `fantasma`, `motivos_fantasma[]` (`sin_fecha` · `repetida` · `generica`), `fraude`, `senales_fraude[]` (citas), `dominio_empresa`, `empresa_validada` (`null` = sin comprobar), `salario_publicado`, `salario_rango`, `frase_pedir_salario`.
- `Taxonomia`: `sector`, `familia`, `nivel` (literales cerrados) y `stack[]` (minúsculas, presentes en el texto).
- `Oferta` = `OfertaExtraida` + `auditoria` + `taxonomia` + `recomendable`.
- `Fuente`: `nombre`, `web`, `url` (https), `metodo`, `parametros`, `cabeceras`, `variable_clave`, `mapeo`, `activa`.
- `CalificacionFuente`: `url`, `apta`, `excluida_por_regla`, `permite_uso_automatizado`, `robots_permite`, `requiere_clave`, `motivos[]`, `citas[]`, `instrucciones_embebidas[]`.

**Agentes**
| Agente | Modelo | Entrada → salida |
|---|---|---|
| `auditor-oferta` | pequeño | `{oferta, texto}` → `{generica, fraude, senales_fraude, dominio_empresa, instrucciones_embebidas}` |
| `clasificador-oferta` | pequeño | `{oferta}` → `Taxonomia` |
| `auditor-fuentes` | mayor | `{url, condiciones, robots}` → `{permite_uso_automatizado, requiere_clave, motivos, citas, instrucciones_embebidas}` |

**Consola**
- `horma flujo listar` · `horma flujo correr <nombre> --entrada f [--paso-a-paso] [--traza dir] [--simulado --respuestas r.json]`
- `horma ingestar <fuente> [--limite n] [--en-seco]` · `horma ingestar --escuchar`
- `horma fuente calificar <url> [--condiciones url] [--local]`
- `horma eval correr ofertas|fuentes`

**API**
| Ruta | Quién | Qué hace |
|---|---|---|
| `POST /ofertas` | sesión + CSRF, o clave (`ofertas`/`ingesta`) | Guarda la oferta cruda (≤ 20 000 caracteres; cuerpo ≤ 64 KB) y encola; idempotente por `(fuente, id_externo)`; límite de ritmo por clave |
| `GET /ofertas` | sesión | Catálogo con auditoría y taxonomía |
| `GET /api/ingesta/resumen` | admin | Fuentes, última ejecución, ofertas por estado, errores |
| `POST /api/fuentes`, `PUT /api/fuentes/{id}` | admin | Crear y editar; activar exige calificación apta (409 si no) |
| `POST /api/ingesta/ejecuciones` | admin, o clave `ingesta` | Admin: deja la ejecución pendiente. Clave: crea y reclama a la vez (consola) |
| `POST /api/ingesta/reclamar`, `POST /api/ingesta/ejecuciones/{id}/fin` | clave `ingesta` | El ingestor toma una ejecución con la configuración de su fuente y la cierra con sus números |
| `POST /api/fuentes/calificaciones`, `GET …/{id}` | admin, o clave `ingesta` | Encola la calificación y la consulta |
| `GET/POST /api/claves`, `DELETE /api/claves/{id}` | admin | Listar, crear (la clave se enseña una vez) y revocar |
| `GET /ingesta` | admin | Página del dashboard |

## Requisito → componente
| Requisito | Componente | Notas |
|---|---|---|
| RF-1.1 | `schemas/fuente.py`, migración 0002, `config/endpoints.json`, `routers/ingesta.py` | Semilla en la migración |
| RF-1.2 | `horma/ingesta.py`, `tools/normalizar.py`, `cli.py`, servicio `ingestor` | Test de arquitectura: `horma.ingesta` no importa `horma.web` ni `sqlalchemy` |
| RF-1.3 | `auth/claves.py`, tabla `claves_api`, limitador en memoria | SHA-256; prefijo visible; `revocada_en` |
| RF-1.4 | `flows/`, `queue/worker.py` | Tarea `procesar_oferta` en modo sistema |
| RF-1.5 | `agents/auditor_oferta/`, `tools/dominio.py`, paso `componer` | DNS inyectable en tests |
| RF-1.6 | `schemas/taxonomia.py`, `agents/clasificador_oferta/` | |
| RF-1.7 | `flows/calificar_fuente.py`, `agents/auditor_fuentes/`, `tools/robots.py`, `tools/descargar.py` | Regla de exclusión antes del modelo |
| RF-1.8 | `static/ingesta.html`, `static/ingesta.js`, `routers/ingesta.py` | Texto siempre con `textContent` |
| RF-1.9 | columna generada `recomendable` | |
| RF-1.10 | `auth/sesion.py` (`exigir_admin`) | `HORMA_ADMINS` = lista de `sub` |
| RF-1.11 | índice único `(fuente_id, id_externo)`, columna `huella` | La repetición se calcula al procesar |
| RF-1.12 | `cli.py` (`flujo correr`) | Traza: `NN-paso.json` |

## Modelo de datos (migración 0002)
| Tabla | Cambios / campos | RLS |
|---|---|---|
| `ofertas` | sin `usuaria_id`; `fuente_id`, `id_externo`, `huella`, columnas de `Auditoria` y `Taxonomia`, `recomendable` (generada) | Lee cualquier sesión con usuaria o sistema; escribe solo sistema |
| `origen` | `usuaria_id` admite nulo (datos del catálogo) | Nulo: lee cualquiera, escribe sistema; con usuaria: como en la fase 0 |
| `tareas` | `usuaria_id` admite nulo (tareas del sistema) | Nulo: solo sistema |
| `fuentes` | campos de `Fuente`, `nombre` único | Solo sistema |
| `calificaciones_fuente` | campos de `CalificacionFuente`, `dominio`, `estado`, `motivo_error` | Solo sistema |
| `ejecuciones_ingesta` | `fuente_id`, `limite`, `estado`, `recibidas`, `nuevas`, `repetidas`, `errores`, `motivo_error`, fechas | Solo sistema |
| `claves_api` | `nombre`, `prefijo`, `hash` (único), `alcance` (`ofertas` · `ingesta`), `creada_en`, `revocada_en` | Solo sistema |

## Decisiones del plan (revisables)
- La cola de ingesta es `ejecuciones_ingesta`, no `tareas`: la ejecuta el ingestor (sin BD), no el worker.
- Los parámetros y cabeceras de una fuente pueden usar `${VAR}` solo con las variables que declara `variable_clave` (lista separada por comas); nunca con secretos de Horma.
- `HORMA_ADMINS` admite varios `sub` separados por comas.
- El límite de ritmo vive en memoria del proceso de la API (`LIMITE_OFERTAS_POR_MINUTO`, 60 por defecto): basta con una sola instancia; en la fase 4 se revisa.
- El eval `ofertas` corre el flujo completo sin BD ni DNS: compara `dominio_empresa`, no `empresa_validada`. `stack` se compara como conjunto; si con el modelo real no llega a 0,9, se revisa la métrica antes que el umbral.
