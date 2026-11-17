---
type: plan
title: correcciones-profesor — Plan técnico
description: Arquitectura, contratos y modelo de datos que cubren cada requisito de la fase 5 (perfil y CV maestro, Recomendadas sin «Condiciones», ofertas propias por texto o URL con Apify, validación de CV, fuentes nuevas, guía de estilo y «que no suene a IA»).
tags: [plan, perfil, cv-maestro, ofertas, scrapeo, validacion-cv, fuentes, estilo]
status: active
sources: [./spec.md, ./clarifications.md, ../system.md, ../004-langgraph-salida/plan.md]
generated: { by: claude-code, at: 2026-11-17 }
verified: { by: human, at: 2026-11-17 }
stale_after: null
---

# correcciones-profesor — Plan

## Arquitectura
```
horma/
  agents/    analizador_estilo/ (nuevo: prompt.md, schemas.py, agent.py)
             extractor_perfil (secciones nuevas; deja de escribir cv_maestro)
             generador_cv_base (visibilidad por experiencia) · redactor_cv, redactor_carta (guía de estilo)
             juez_candidatura (tipos nuevos; carta y oferta opcionales para juzgar CV base)
  schemas/   perfil.py (Proyecto, Certificacion, OtroDato) · estilo.py (GuiaEstilo, nuevo)
             candidatura.py (TipoProblema + «incoherente», «suena_a_ia»)
  tools/     componer_cv_maestro.py · validar_cv.py · muletillas_ia.py · validar_url.py
             leer_pagina.py (cliente Apify) · cv_base_afectado.py   (todas nuevas, código puro salvo leer_pagina)
  assets/    muletillas_ia.json (nuevo, versionado) · portales_vetados.json (nuevo)
  flows/     perfilar.py, generar_cv_base.py, candidatura.py (cambian) · analizar_estilo.py (nuevo)
  web/       migración 0010 · services/perfil.py, cv.py, ofertas.py, candidaturas.py · repositories
             (perfiles, ofertas, matches, estilo nuevo, importaciones nuevo) · routers (ofertas, perfil,
             cv, estilo nuevo) · queue/worker.py (tareas nuevas) · static/ (añadir-oferta.html/js nuevos,
             perfil, cv-base, candidatura, recomendadas)
config/endpoints.json (fuentes nuevas) · horma/ingesta.py + tools/normalizar.py (adaptadores)
evals/estilo/ (nuevo) · evals/perfil, cv, cv-base (casos nuevos) · evals/umbrales.json
```
Las fronteras no cambian: los agentes no tocan red ni disco (RT-01); `leer_pagina` es una tool que
solo usa el worker, inyectable como `descargar.Descargador` para los tests.

## Perfil como fuente de verdad (RF-5.1)
- **`componer_cv_maestro(perfil) -> str`** (código puro): Markdown con encabezados fijos (`## Resumen`,
  `## Experiencia`, `## Formación`, `## Idiomas`, `## Habilidades`, `## Proyectos`,
  `## Certificaciones`, `## Otros`). Una línea de cabecera por elemento (`puesto · empresa · inicio-fin`)
  y su `descripcion` debajo. Determinista: el mismo perfil da el mismo texto.
- **Siempre por código** (decisión del plan): `perfilar` también compone el maestro con
  `componer_cv_maestro` en vez de usar el del extractor. El extractor deja de escribir `cv_maestro`
  (ahorra tokens de salida). Así el maestro nunca cambia de estilo a la primera edición.
- **`services/perfil._nueva_version`**: guarda `componer_cv_maestro(perfil)` en lugar de copiar el
  anterior. La trazabilidad sigue funcionando: lo editado está en el maestro nuevo (RF-5.1b).
- **Secciones nuevas (RF-5.1c):** `Proyecto{nombre, descripcion?, fecha?, origen}`,
  `Certificacion{nombre, entidad?, fecha?, origen}`, `OtroDato{valor, origen}`. `LISTAS` de
  `services/perfil.py` gana `proyectos`, `certificaciones`, `otros`. La pantalla (`perfil.html/js`)
  añade las tres secciones con su texto de ayuda y los ejemplos de la spec.
- **CV base afectados (RF-5.1e):** `cv_base_afectado(traza, maestro_nuevo) -> bool`: verdadero si algún
  `fragmento` de la traza ya no aparece literal en el maestro nuevo. `listar_cv_base` lo usa en vez de
  «versión anterior = desfasado» y devuelve las líneas que cambiaron.
- **Regenerar un CV base:** `POST /api/cv-base/{id}/regenerar` encola `generar_cv_base` con
  `destinos=[ese destino]` y `cv_base_id`. El guardado sustituye el contenido con `editar_cv_base(…,
  origen="regeneracion")`, así la versión anterior va al historial.
- **Visibilidad por experiencia (RF-5.1g):** columna `cv_base.visibilidad jsonb` =
  `{clave_experiencia: "completa"|"condensada"|"oculta"}`, con `clave = puesto|empresa|inicio`
  normalizada (los índices cambian entre versiones). Por defecto, las experiencias de otro sector,
  `condensada`. El generador recibe la visibilidad y una regla nueva en su prompt; el código
  comprueba que una «oculta» no aparece y que una «condensada» ocupa una sola línea.
- **Borradores desfasados (RF-5.1f):** el detalle de la candidatura compara `perfil_version` con la
  vigente y devuelve `desfasada: true`. `reintentar` se amplía: también vale en `borrador` desfasado
  (no solo en `error`), con el mismo tope de coste y borrando el hilo.

## Recomendadas sin «Condiciones» (RF-5.2)
- `static/recomendadas.js`: fuera la columna y su ayuda. La columna `matches.condiciones` y
  `evaluar_condiciones` se quedan (el eval `recomendacion` las mide; integrarlas en la nota es mejora
  futura).

## Ofertas propias (RF-5.3)
- **Primero reproducir (RF-5.3):** test que hoy falla. Dos causas probables encontradas al planificar:
  1. la oferta pegada no tiene nota hasta pulsar «Recomendar» y puede no pasar los filtros;
  2. `para_procesar` marca `repetida` si otra oferta tiene la misma huella → el auditor la da por
     fantasma y queda no recomendable. Pegar dos veces la misma oferta (o una que ya está en el
     catálogo) la deja fuera.
- **Dueña (RF-5.3c):** `ofertas.usuaria_id` nullable (null = catálogo común). Política de lectura:
  `app_sistema() OR (usuaria_id IS NULL AND app_usuaria() IS NOT NULL) OR usuaria_id = app_usuaria()`.
  El alta sigue en modo sistema; `services/ofertas.recibir` recibe `usuaria_id` desde la web.
  `repetida` solo compara con ofertas de la misma dueña (o del catálogo común entre sí).
- **Puntuar al momento (RF-5.3d):** tarea `puntuar_propias` (usuaria = dueña, entidad = perfil
  vigente). Carga todas sus ofertas propias procesadas **sin nota para esa versión** y corre el flujo
  `recomendar` con ellas como candidatas (una llamada al `matcher` por cada 30). Se encola:
  1. al terminar `procesar_oferta` de una oferta con dueña;
  2. cuando el perfil pasa a una versión nueva (`perfilar` o `clasificar_perfil` terminan), para que
     las propias sigan evaluadas con el perfil vigente y las añadidas sin perfil se puntúen solas.
  Si no hay perfil, no se encola: se hará con el primero.
- **Recomendadas, TODAS las propias (RF-5.3e, P17):** `buscar_ofertas` queda
  `(estado = 'procesada' AND recomendable AND filtros) OR (estado = 'procesada' AND usuaria_id IS NOT
  NULL)` (la RLS ya garantiza que solo son las suyas). Las propias saltan filtros, rango de nota,
  repetición, fantasma y fraude; si el auditor las marcó, el listado devuelve el motivo y la web
  muestra su aviso. `matches.listado` devuelve `propia` y `analizada_en` (fecha del match).
- **Pestaña «Añadir oferta» (RF-5.3b):** `static/anadir-oferta.html/js` con dos modos, texto o URL. Se
  quita el formulario de `index.html`. Muestra el estado de lo último añadido (leyendo, analizando,
  lista, no se pudo leer).
- **URL (RF-5.3f-j):** tabla `importaciones` (`id, usuaria_id, url, estado` `pendiente|leida|error`,
  `motivo, oferta_id, creada_en`; RLS «propia»). `POST /api/ofertas/url`:
  1. `validar_url(url)`: solo `https`, sin credenciales, dominio (no IP literal), que resuelva solo a
     IP públicas, y que no esté en `assets/portales_vetados.json` (dominio y subdominios). Si falla,
     422 con el motivo en llano.
  2. Límite de ritmo por usuaria (`web/limites.py`), 429 al pasarse.
  3. Crea la importación y encola `leer_url`.
  El worker llama a `leer_pagina(url)`: Apify, actor `apify/rag-web-browser`, en modo síncrono, con
  `APIFY_TOKEN` en la cabecera `Authorization` (nunca en la URL ni en el log), sin proxies residenciales
  ni «Unblocker», tiempo máximo y tamaño máximo del texto. Con texto: `recibir(texto, url=…,
  usuaria_id=…)` y sigue como una pegada. Sin texto o error: `estado=error` con motivo fijo («La página
  no se ha podido leer: pega el texto de la oferta»).
- **Coste:** Apify fuera de `llm_llamadas`; se cuenta cada lectura en `importaciones` y `/costes` muestra
  cuántas al mes. `APIFY_TOKEN`, `LIMITE_URL_HORA` y `APIFY_TIMEOUT_S` en `.env.example`.
- **Confirmación RGPD (RF-5.3i):** tarea propia antes de construir el cliente; el resultado se anota
  en `docs/revision-lineas-rojas.md` («Encargados del tratamiento»). Si no se confirma, `leer_pagina`
  usa ScrapingBee con la misma firma.

## Validar CV y «que no suene a IA» (RF-5.4, RF-5.7)
- **`validar_cv(texto) -> list[str]`**: palabras entre `CV_PALABRAS_MIN=250` y `CV_PALABRAS_MAX=1000`;
  encabezado `## Experiencia` o `## Formación`; fechas `AAAA` o `AAAA-MM` con fin ≥ inicio. Errores en
  llano.
- **`muletillas_ia(texto) -> list[str]`**: busca en `assets/muletillas_ia.json` (expresiones en
  minúsculas, sin acentos, con variantes de género). Devuelve las halladas.
- **`candidatura.comprobar`**: suma `validar_cv` a `errores_formato` y `muletillas_ia` al CV
  (`errores_cv`) y a la carta (`errores_carta`). Todo entra en la vuelta única que ya existe.
- **Juez:** `TipoProblema` gana `incoherente` y `suena_a_ia`. `EntradaJuezCandidatura` gana
  `guia_estilo: GuiaEstilo | None`; `carta` y `oferta` pasan a opcionales para juzgar un CV base (sin
  carta, `veredicto_carta` = «aprobado»). Prompt: reglas de coherencia y de texto genérico o fuera de
  estilo.
- **CV base (RF-5.4d):** `generar_cv_base.verificar` suma `validar_cv`, `muletillas_ia` y una llamada al
  juez (solo CV). Los problemas del juez van al segundo intento, que ya existe (`MAX_INTENTOS=2`).

## Guía de estilo (RF-5.6)
- **Documentos:** `cv_archivos.clase` admite `carta`; columna nueva `escrito_por_ella boolean`. Las
  cartas no entran en `cvs_fuente` (ya filtra por `fuente`).
- **Agente `analizador_estilo`:** entrada `documentos: [{tipo, texto, escrito_por_ella}]`; salida
  `GuiaEstilo{registro, persona, longitud_frase, vinetas, expresiones: [{rasgo, cita}],
  evita: [{rasgo, cita}], instrucciones_embebidas}`. Prioriza los escritos por ella. Código tras el
  agente: cada `cita` debe aparecer literal en algún documento (si no, se quita) y `rasgos_personales`
  sobre la guía (RT-09).
- **Tabla `estilo`** (`usuaria_id` PK, `guia jsonb`, `origen` `modelo|usuaria`, `analizada_en`; RLS
  «propia»). Tarea `analizar_estilo`: se encola sola **solo si no hay guía** al terminar `perfilar` o al
  subir una carta; después, solo con `POST /api/estilo/analizar` (botón «Volver a analizar mi estilo»).
  `PUT /api/estilo` guarda la edición de ella (`origen=usuaria`).
- **Redactores:** `EntradaRedactorCv` y `EntradaRedactorCarta` ganan `guia_estilo: GuiaEstilo | None`;
  el worker la carga en `_Candidatura.cargar` y la pasa por el estado (`CLAVES_INTERNAS` + `guia_estilo`).
  Prompt: «sigue la guía en la forma, nunca en los hechos».

## Fuentes nuevas (RF-5.5)
- **Solo configuración** (`config/endpoints.json` + calificación con `calificar_fuente`): Himalayas
  (`/jobs/api/search?country=ES`, clave opcional), Jobicy (`/api/jobs?geo=europe`), Remotive
  (`/api/remote-jobs`). Activar Adzuna.
- **Adaptadores pequeños** en `normalizar.items` / `ingesta.leer_fuente`:
  - `lista: "$"` para respuestas que son un array en la raíz (Lever, RemoteOK si se añadiera);
  - `metodo: "GET"` con Basic auth desde variables (InfoJobs) y `detalle` opcional: URL de detalle por
    oferta para traer la descripción.
- **Por fuente:** `cada_horas` (Remotive: 6) para respetar sus límites; `atribucion` (texto y enlace)
  que se muestra en la oferta; borrado de caducadas para Himalayas.
- **InfoJobs:** configurada con `activa: false` hasta tener sus condiciones por escrito.
- **Greenhouse/Lever:** una entrada por empresa (`boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true`,
  `api.eu.lever.co/v0/postings/{empresa}?mode=json`) con la lista que dé Mar.

## Evals con el modelo real, aparcados (RF-5.8)
- `.github/workflows/ci.yml`, job `evals-reales`: `if: github.event_name == 'workflow_dispatch'` (fuera
  `pull_request`). GitHub cuenta un job omitido como superado, así que la protección de `main` no se
  bloquea; aun así, Mar quita `evals-reales` de los checks obligatorios (Settings → Branches) para que
  quede claro. `calidad` (simulado) sigue obligatorio.
- Antes del lanzamiento: se vuelve a poner `pull_request` y el check obligatorio. Queda anotado en
  `docs/mejoras-futuras.md`.

## Modelo de datos (migraciones reversibles)
Numeración real: 0010 (bloque A, recomponer maestros), 0011 (`origen` «regeneracion») y 0012
(`cv_base.visibilidad`) del bloque B; el resto de cambios, en la 0013 (bloque C) y siguientes.

| Tabla | Cambio |
|---|---|
| `ofertas` | `+ usuaria_id integer NULL REFERENCES usuarias ON DELETE CASCADE`; política de lectura nueva (ver arriba) |
| `importaciones` (nueva) | `id, usuaria_id, url, estado, motivo, oferta_id, creada_en`; RLS «propia» |
| `cv_archivos` | `clase` admite `carta`; `+ escrito_por_ella boolean NOT NULL DEFAULT false` |
| `cv_base` | `+ visibilidad jsonb NOT NULL DEFAULT '{}'` |
| `cv_base_versiones` | `origen` admite `regeneracion` |
| `estilo` (nueva) | `usuaria_id PK, guia jsonb, origen, analizada_en`; RLS «propia» |
| `fuentes` | `+ cada_horas integer`, `+ atribucion text` |

Los perfiles existentes (datos de prueba) se recomponen con `componer_cv_maestro` en la migración.

## Evals (RT-11)
- **`evals/estilo/`** (nuevo): unas 8 usuarias inventadas con CV y cartas de estilos distintos
  (formal, cercano, impersonal, con viñetas cortas…), 2 con instrucciones embebidas. Campos: `registro`,
  `persona`, `citas_con_origen`; al 100 %: `sin_rasgos`, `sin_efecto`.
- **`evals/perfil/`**: casos con proyectos, certificaciones y otros.
- **`evals/cv/`**: casos con guía de estilo, con muletillas, con fechas incoherentes y largos; el juez
  debe marcar `incoherente` y `suena_a_ia`.
- **`evals/cv-base/`**: visibilidad (oculta y condensada), longitud y juez.
- **`umbrales.json`**: `estilo` (`campos 0.9`, 100 % en los dos de seguridad). El resto se mantiene.

## Requisito → componente
| Requisito | Componente | Prueba |
|---|---|---|
| RF-5.1, 5.1b | `tools/componer_cv_maestro.py`, `services/perfil.py`, `flows/perfilar.py` | Editar y borrar cambian el maestro; CV adaptado sin errores de traza |
| RF-5.1c, 5.1d | `schemas/perfil.py`, `extractor_perfil`, `static/perfil.*` | Eval `perfil`; ayuda visible |
| RF-5.1e, 5.1g | `tools/cv_base_afectado.py`, `repositories/perfiles.py`, `generador_cv_base`, `static/cv-base.*` | Solo el afectado se marca; oculta y condensada |
| RF-5.1f | `services/candidaturas.py`, `static/candidatura.*` | Aviso y rehacer en borrador desfasado |
| RF-5.2 | `static/recomendadas.js` | Sin columna |
| RF-5.3-5.3e | migración 0010, `repositories/ofertas.py`, `buscar_ofertas`, worker `puntuar_propia` | Limbo; RLS Ana/Berta; marca y sin filtros |
| RF-5.3f-j | `tools/validar_url.py`, `tools/leer_pagina.py`, `importaciones`, `web/limites.py` | URL vetada, `http`, IP privada; lector simulado; 429 |
| RF-5.4-5.4e | `tools/validar_cv.py`, `candidatura.py`, `generar_cv_base.py`, juez | Largo, corto, fechas; evals `cv` y `cv-base` |
| RF-5.5-5.5d | `config/endpoints.json`, `normalizar.py`, `ingesta.py` | Fuentes calificadas; atribución; InfoJobs inactiva |
| RF-5.6-5.6f | `analizador_estilo`, `flows/analizar_estilo.py`, `estilo`, redactores | Eval `estilo`; una sola vez; botón |
| RF-5.7-5.7e | `tools/muletillas_ia.py`, juez | Muletillas señaladas y corregidas |
| RF-5.8 | `.github/workflows/ci.yml`, protección de `main` | Un PR no lanza el modelo real; `calidad` sigue obligatorio |

## Decisiones del plan (revisables)
- El maestro lo compone siempre el código, también tras `perfilar`; el extractor deja de escribirlo.
- «Desfasado» de un CV base por traza, no por número de versión.
- La guía de estilo es una por usuaria (no por sector).
- Las ofertas propias se puntúan con el flujo `recomendar` existente (una candidata), no con un flujo
  nuevo.
- El juez de CV base es el mismo agente con carta y oferta opcionales, no un modo aparte.

## Riesgos
- **Cambiar el esquema del perfil y del juez** obliga a regenerar las respuestas simuladas de los tests.
  Con `evals-reales` aparcado (RF-5.8), la calidad real solo se mide al lanzarlos a mano.
- **Re-puntuar las propias en cada versión del perfil:** una llamada al `matcher` por cada 30 ofertas
  propias y versión; barato, pero crece con las ediciones.
- **Apify:** el nombre y la entrada del actor (`rag-web-browser`, campo `query` con la URL) se comprueban
  con una llamada real antes de cerrar el cliente; RGPD sin confirmar (RF-5.3i).
- **Muletillas:** una lista demasiado amplia da falsos positivos; empieza corta y se amplía con casos.
- **Coste por CV base:** suma una llamada al juez por destino (hasta 4).
- **Condiciones de las fuentes:** cambian; se revisan al calificar.
