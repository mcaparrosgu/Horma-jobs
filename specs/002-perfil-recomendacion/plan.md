---
type: plan
title: perfil-recomendacion — Plan técnico
description: Arquitectura, contratos y modelo de datos que cubren cada requisito de la fase 2.
tags: [plan, perfil, recomendacion]
status: draft
sources: [./spec.md, ./clarifications.md, ../system.md, ../001-ofertas/plan.md]
generated: { by: claude-code, at: 2026-11-14 }
verified: null
stale_after: null
---

# perfil-recomendacion — Plan

## Arquitectura
Se añade a lo de las fases 0 y 1:

```
horma/
  schemas/   perfil.py, preferencias.py, match.py, filtros.py (listas cerradas: país, contrato, idioma)
  agents/    extractor_perfil/ (mayor), clasificador_postulante/ (pequeño),
             generador_cv_base/ (mayor), matcher/ (mayor)
  tools/     convertir_cv.py, verificar_trazabilidad.py, normalizar_oferta.py,
             buscar_ofertas.py, rasgos_personales.py
  flows/     perfilar.py, generar_cv_base.py, recomendar.py
  cli.py     + recomendar, eval importar-correccion
  web/       migración 0003, routers/{perfil,cv,preferencias,recomendaciones}.py, services/,
             repositories/, static/{perfil,preferencias,cv-base,recomendadas}.{html,js}, estilo.css
evals/perfil/ (12 casos) · evals/recomendacion/ (20 casos) · evals/cv-base/ (5 casos)
docker-compose.yml: volumen `horma_archivos` montado solo en la API
```

- **Camino de un CV:** la usuaria sube el archivo a `POST /api/cv` → la API comprueba tipo y tamaño, lo guarda en el volumen con nombre aleatorio y lo convierte a texto con `convertir_cv` (el texto se guarda en Postgres con RLS) → encola la tarea `perfilar` (solo ids) → el worker ejecuta el flujo y guarda una **versión nueva** del perfil, sus orígenes y las preferencias que salen del CV.
- **Fronteras (sin cambios):** los agentes y las herramientas no tocan base de datos ni disco; `buscar_ofertas` **construye** la consulta (texto SQL, parámetros y orden) y el repositorio la ejecuta; la consola no abre la base de datos.
- **Cambiar el perfil** (responder una pendiente o corregir un dato): el código copia la versión vigente en una nueva, pone origen «usuaria» en el dato tocado y encola `clasificar_perfil` (solo el agente pequeño). Los CV base y los matches de versiones anteriores salen **desfasados**: es una columna calculada que compara su versión con la vigente.

## Flujos
| Flujo | Pasos |
|---|---|
| `perfilar` | `extraer` (extractor-perfil, con todos los CV de la usuaria) → `verificar_origen` (código: un dato cuyo fragmento no está en su CV va a `preguntas_pendientes`) → `quitar_sensibles` (código, RT-09) → `clasificar` (clasificador-postulante) → `preferencias_desde_cv` (código) → `componer` |
| `generar_cv_base` | `elegir_destinos` (código: hasta 4 sectores o familias, de la taxonomía y las preferencias) → `generar` (generador-cv-base) → `verificar` (verificar_trazabilidad) → arista condicional: vuelve a `generar` (máximo 2 intentos) o pasa al destino siguiente → `componer`. Un CV base que no pasa la verificación no se guarda y deja el motivo |
| `recomendar` | `candidatas` (las carga el worker con `buscar_ofertas`; las que ya tienen nota para esa versión del perfil no se vuelven a puntuar) → `puntuar_tanda` (matcher, 30 por tanda) → arista condicional: otra tanda si la anterior dejó alguna nota dentro del rango y quedan candidatas, con tope de 5 tandas → `revisar_explicaciones` (código: si aparece un rasgo personal, la explicación se retira y se marca) → `componer` |

## Contratos
**Agentes**
| Agente | Modelo | Entrada → salida |
|---|---|---|
| `extractor-perfil` | mayor | `{cvs: [{cv_id, nombre, texto}]}` → `{perfil, cv_maestro (Markdown), preguntas_pendientes[], instrucciones_embebidas[]}`; cada dato lleva `{cv_id, fragmento}` |
| `clasificador-postulante` | pequeño | `{perfil}` → `Taxonomia` |
| `generador-cv-base` | mayor | `{cv_maestro, perfil, destino: {sector, familia}, errores_previos[]}` → `{contenido (Markdown ATS), traza: [{frase, fragmento}]}` |
| `matcher` | mayor | `{perfil, condiciones, ofertas[≤30]}` → `[{oferta_id, nota 0-100, condiciones: bajo·medio·alto, explicacion (2-3 frases), cita_perfil, cita_oferta}]` |

Cada agente nuevo se añade a la lista del contrato «independence» de `import-linter` (`pyproject.toml`) y a `horma/agents/registry.py`.

**Herramientas (código puro con tests)**
- `convertir_cv(bytes, tipo)`: PDF (`pypdf`), DOCX (`python-docx`) y Markdown a texto. Comprueba los bytes iniciales, no solo la extensión.
- `verificar_trazabilidad(contenido, traza, maestro)`: devuelve la lista de errores si una frase no tiene entrada en la traza, si el fragmento de la traza no está en el maestro, o si una fecha, cargo, empresa o titulación del CV base no aparece en el maestro. Reutiliza `linea_con` y `literales` de `tools/origen_oferta.py`.
- `normalizar_oferta(oferta)`: devuelve `pais` (ISO-3166 o `REMOTO`), `tipo_contrato`, `idiomas` (ISO-639-1) y `salario_anual_eur_min/max`. Diccionarios cerrados de sinónimos (es, en, de, fr, pt). Sueldo mensual × 12; `null` si está en otra moneda o no hay dato (P16, P17).
- `buscar_ofertas(preferencias)`: devuelve `(sql, params, orden)`. Solo descarta una oferta si el dato existe y no coincide (P2); `recomendable = true` siempre. El orden previo es coincidencia de taxonomía y después fecha.
- `rasgos_personales(texto)`: lista cerrada de términos de edad, nacionalidad, sexo, estado civil, salud y art. 9; la usan el flujo y el eval.

**API** (sesión; escritura con CSRF; RLS «propia»)
| Ruta | Qué hace |
|---|---|
| `POST /api/cv` | Multipart (`archivo`, `nombre`, `clase`: fuente o estético). Máx. 5 MB; PDF, DOCX o MD. Si es fuente, convierte y encola `perfilar` |
| `GET /api/cv` · `PATCH /api/cv/{id}` · `GET /api/cv/{id}/archivo` | Listar, renombrar (nombre único por cuenta, 409 si se repite) y descargar solo la dueña |
| `GET /api/perfil` · `POST /api/perfil/respuestas` · `PATCH /api/perfil/datos` | Ver la versión vigente con orígenes y pendientes; responder o corregir (crea versión) |
| `GET/PUT /api/preferencias` · `GET /api/preferencias/opciones` | Leer y guardar filtros; casillas con su contador de ofertas |
| `POST /api/cv-base` · `GET /api/cv-base` · `PATCH /api/cv-base/{id}` | Generar a petición (tarea), listar y renombrar |
| `POST /api/recomendar` | Encola `recomendar` (puntúa solo lo que falta) |
| `GET /api/recomendaciones?rango=&orden=&…` | Filtra y ordena lo ya puntuado **sin llamar al modelo**; lo nuevo, «sin puntuar» (RF-2.15c) |
| `POST /api/matches/{oferta_id}/correccion` · `GET …/exportar` | Guardar la corrección; exportar el caso en JSON para el eval |
| `GET /api/catalogo` (clave `ingesta`) | Catálogo común para `horma recomendar`; sin datos personales |
| `GET /perfil`, `/preferencias`, `/cv-base`, `/recomendadas` | Páginas con pestañas comunes |

`MAX_CUERPO` (64 KB) tiene una excepción solo para `POST /api/cv` (5 MB).

**Pantallas**
- **Recomendadas** (RF-2.15b): sigue `dashboard.png`. Pestañas, barra de filtros de RF-2.8 y rango, contador, bloque plegable «Cómo leer las recomendaciones» y tabla con las columnas Oferta · Puesto (etiqueta de color) · Compatibilidad (barra y nota) · Condiciones · Salario · Lugar · Publicado, con «?» en cada cabecera. La explicación se despliega en la misma fila junto al botón «Corregir». En móvil, tarjetas. **Salario muestra siempre el texto original de la oferta** (P17).
- **Preferencias** (RF-2.8): grupos de casillas al estilo de The Hub, con el contador entre paréntesis y un campo numérico para el sueldo mínimo.
- Todo con `textContent` (helper `nodo()`), CSP estricta y el marco Passe-Partout. El diseño visual se hace con la skill `frontend`.

**Consola**
- `horma agente correr extractor-perfil|clasificador-postulante|generador-cv-base|matcher --entrada f [--simulado]`
- `horma flujo correr perfilar --usuaria ana --entrada cv.pdf [--paso-a-paso --traza dir]` (en local; no guarda; `--usuaria` solo nombra la traza)
- `horma recomendar ana --rango 40-100`: usa el perfil de prueba `evals/perfil/perfiles/ana.json` y el catálogo de `GET /api/catalogo` (`--ofertas f.json` para hacerlo sin API) e imprime la lista.
- `horma eval correr perfil|recomendacion|cv-base [--tope-coste 1.0]`
- `horma eval importar-correccion --archivo caso.json`: enseña el caso y lo copia a `evals/recomendacion/casos/` solo si la persona lo confirma (P4).

## Requisito → componente
| Requisito | Componente | Notas |
|---|---|---|
| RF-2.1, 2.1b | `routers/cv.py`, `tools/convertir_cv.py`, `agents/extractor_perfil/`, tabla `cv_archivos` | Nombre único por cuenta; archivo con uuid |
| RF-2.2, 2.3 | `flows/perfilar.py` (`verificar_origen`), `tools/origen_oferta.py` (reutilizado) | Sin origen → pendiente |
| RF-2.4 | `services/perfil.py`, columna `version`, columna calculada «desfasado» | |
| RF-2.5 | `agents/clasificador_postulante/` | Misma `Taxonomia` |
| RF-2.6 | `tools/rasgos_personales.py`, paso `quitar_sensibles`, eval `perfil` | |
| RF-2.7 | prompts de los agentes, `instrucciones_embebidas` | Casos adversarios en los evals |
| RF-2.8, 2.8b | `schemas/preferencias.py`, `routers/preferencias.py`, `static/preferencias.*` | `origen` por grupo: cv o usuaria |
| RF-2.9 | `flows/generar_cv_base.py`, `agents/generador_cv_base/`, `tools/verificar_trazabilidad.py` | Máximo 2 intentos |
| RF-2.10 | `routers/cv.py` (`clase=estetico`), `GET /api/cv/{id}/archivo` | Sin procesar |
| RF-2.11 | `tools/buscar_ofertas.py`, `tools/normalizar_oferta.py`, migración 0003 | Filtro en SQL |
| RF-2.12 | `agents/matcher/`, `flows/recomendar.py`, tabla `matches` | La tabla es la caché |
| RF-2.13 | `routers/recomendaciones.py`, `eval importar-correccion` | La corrección no entra al repo sin confirmar |
| RF-2.14 | paso `revisar_explicaciones`, `tools/rasgos_personales.py`, eval `recomendacion` | |
| RF-2.15, 2.15b, 2.15c | `static/*`, `routers/recomendaciones.py` | Filtrar no llama al modelo (test) |
| RF-2.16 | `cli.py`, `flows/registry.py` | Traza `NN-paso.json` |
| RF-2.17 | `horma/evals.py` + `metricas.capturar()` | Tope 1 USD (los precios de `config.py` son USD) |

## Modelo de datos (migración 0003)
| Tabla | Campos | RLS |
|---|---|---|
| `cv_archivos` | `usuaria_id`, `nombre` (único por usuaria), `nombre_original`, `ruta` (uuid), `tipo`, `clase` (fuente·estético), `tamano`, `texto` (nulo si estético), `creado_en` | propia |
| `perfiles` | `usuaria_id`, `version` (único con usuaria), `datos` jsonb, `cv_maestro`, `preguntas_pendientes` jsonb, `instrucciones_embebidas`, columnas de `Taxonomia`, `estado`, `motivo_error`, `creado_en` | propia |
| `preferencias` | `usuaria_id` (PK), `familias[]`, `sectores[]`, `contratos[]`, `niveles[]`, `paises[]`, `idiomas[]`, `solo_remoto`, `solo_salario`, `sueldo_minimo`, `orden`, `rango_min`=40, `rango_max`=100, `origen` jsonb por grupo | propia |
| `cv_base` | `usuaria_id`, `perfil_version`, `nombre`, `sector`, `familia`, `contenido`, `traza` jsonb, `estado`, `motivo_error` | propia |
| `matches` | PK (`usuaria_id`, `oferta_id`, `perfil_version`), `nota`, `condiciones`, `explicacion`, `cita_perfil`, `cita_oferta`, `retirada`, `correccion`, `corregido_en` | propia |
| `ofertas` (+) | `pais`, `tipo_contrato`, `idiomas_norm[]`, `salario_anual_eur_min/max`; la migración rellena las ofertas ya existentes | como en la fase 1 |
| `origen` | se reutiliza con `entidad='perfil'` | ya existe |

Único cambio en un archivo de la fase 1: `repositories/ofertas.guardar()` llama a `normalizar_oferta` antes de insertar (P16). Las tablas nuevas se añaden al `TRUNCATE` de `tests/conftest.py`.

## Evals
| Set | Casos | Mide | Umbral |
|---|---|---|---|
| `perfil` | 12 CV inventados de 5 sectores (2 adversarios, varios ambiguos) | Campos (cargos, empresas, fechas, titulaciones, idiomas, taxonomía), pendientes, adversarias, sin rasgos sensibles | ≥ 0,9 por campo; pendientes, adversarias y sensibles al 100 % |
| `recomendacion` | 20 pares perfil-oferta | Nota en ±10 de la esperada, nivel de condiciones, explicaciones sin rasgos personales | ≥ 0,9 de casos en ±10; rasgos al 100 % |
| `cv-base` | 5 (uno por sector) | Pasa `verificar_trazabilidad` en ≤ 2 intentos; formato ATS (sin tablas, encabezados estándar) | 100 % |

El tope de coste por ejecución (1 USD) se aplica en `horma/evals.py` con `metricas.capturar()`: al superarlo se detiene y lo anota en el resultado. CI añade los tres sets a `.github/workflows/ci.yml`.

## Decisiones del plan (revisables)
- El volumen de archivos solo lo monta la API; el worker trabaja con el texto guardado en la base de datos.
- El texto del CV vive en Postgres con RLS: son datos de prueba inventados hasta cerrar el RGPD.
- La caché del matcher es la tabla `matches`; cambiar un filtro nunca llama al modelo.
- Topes por tipo de tarea, configurables: `perfilar` 0,50, `generar_cv_base` 0,50 y `recomendar` 1,00 (USD).
- Dependencias nuevas: `python-multipart`, `pypdf` y `python-docx`.

## Riesgos
- **Instalación:** `uv` falla con certificados en esta red; puede hacer falta instalar las dependencias a mano y usar `UV_NO_SYNC=1`.
- **Coste:** `recomendar` con el modelo mayor cuesta unos 0,09 USD por tanda de 30 (estimado); con el rango 40-100 se puntúan más tandas.
- **Mejora fuera de la fase (no se toca aquí):** el worker solo compara el tope de coste cuando una tarea **falla**; una tarea que termina bien no se compara (`horma/web/queue/worker.py:102-105`, RT-14).
