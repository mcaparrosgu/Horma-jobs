---
type: tasks
title: perfil-recomendacion — Desglose de tareas
description: Tareas pequeñas y comprobables derivadas del plan de la fase 2. Cada una empieza con un test que falla.
tags: [tareas, perfil, recomendacion]
status: draft
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-14 }
verified: null
stale_after: null
---

# perfil-recomendacion — Tareas

Orden de construcción: contrato y código puro (T01-T05) → agentes y flujos (T06-T10) → evals (T11-T12) → base de datos y worker (T13-T14) → API (T15-T19) → pantallas (T20-T21) → consola y cierre (T22-T23). Cada tarea empieza con un test que falla. Todo se prueba sin llamar al modelo (puerta simulada) salvo T12.

- [ ] T01 — Dependencias (`python-multipart`, `pypdf`, `python-docx`), esquemas `Perfil`, `Preferencias`, `Match` y listas cerradas `filtros.py` (país, contrato, idioma) · test: casos válidos e inválidos (dato sin `origen`, valor fuera de lista, nota fuera de 0-100, rango invertido) · cubre: RF-2.2, RF-2.8b, RF-2.12
- [ ] T02 — Herramienta `convertir_cv` · test: PDF, DOCX y Markdown inventados salen como texto; un `.pdf` que no lo es o un archivo vacío se rechaza por sus bytes, no por la extensión · cubre: RF-2.1
- [ ] T03 — Herramienta `verificar_trazabilidad` · test: acepta un CV base fiel; rechaza al 100 % las frases sin traza, los fragmentos que no están en el maestro y las fechas, cargos, empresas o titulaciones cambiados · cubre: RF-2.9, RT-08
- [ ] T04 — Herramientas `normalizar_oferta` y `rasgos_personales` · test: «Berlin, Germany» → `DE`, «contrato fijo» → `indefinido`, «2.000 €/mes» → 24.000 anual, USD o sin dato → nulo; la lista de rasgos detecta edad, nacionalidad, sexo, estado civil y salud · cubre: RF-2.6, RF-2.11, RF-2.14
- [ ] T05 — Herramienta `buscar_ofertas` · test: el dato ausente pasa el filtro; el dato que no coincide descarta; `recomendable = falso` nunca sale; el orden es taxonomía y luego fecha; el sueldo «no comparable» pasa marcado · cubre: RF-2.11, RF-1.9
- [ ] T06 — Agentes `extractor-perfil` y `clasificador-postulante` · test: con la puerta simulada devuelven su esquema; los prompts piden pendientes ante la ambigüedad, no inferir edad ni nacionalidad y registrar instrucciones; ambos están en el registro y en el contrato «independence» · cubre: RF-2.1, RF-2.3, RF-2.5, RF-2.6, RF-2.7, RT-01
- [ ] T07 — Agentes `generador-cv-base` y `matcher` · test: con la puerta simulada devuelven su esquema; el prompt del matcher exige 2-3 frases que citen perfil y oferta, y prohíbe rasgos personales · cubre: RF-2.9, RF-2.12, RF-2.14, RT-01
- [ ] T08 — Flujo `perfilar` · test: un dato sin origen va a pendientes; dos CV que se contradicen → pendiente sin elegir; edad y nacionalidad se descartan; las preferencias salen del CV; un CV con instrucciones las registra · cubre: RF-2.2, RF-2.3, RF-2.6, RF-2.7, RF-2.8b
- [ ] T09 — Flujo `generar_cv_base` · test: hasta 4 destinos; un CV que no pasa la verificación se reintenta una vez y, si falla otra vez, no se guarda y deja el motivo · cubre: RF-2.9
- [ ] T10 — Flujo `recomendar` · test: tandas de 30; no puntúa lo que ya tiene nota para esa versión del perfil; una explicación con rasgo personal se retira; para en el tope de 5 tandas · cubre: RF-2.12, RF-2.14
- [ ] T11 — Fixtures inventadas y evals `perfil` (12 CV, 5 sectores, 2 adversarios) y `cv-base` (5 casos) · test: el harness mide por campo, exige pendientes, adversarias y sensibles al 100 %, y CV base al 100 % · cubre: RF-2.2, RF-2.3, RF-2.6, RF-2.7, RF-2.9, RT-11
- [ ] T12 — Eval `recomendacion` (20 pares) y tope de coste por ejecución · test: nota dentro de ±10, sin rasgos personales al 100 %; con un tope bajo simulado el eval se detiene y deja constancia · cubre: RF-2.12, RF-2.14, RF-2.17, RT-11
- [ ] T13 — Migración 0003 (`cv_archivos`, `perfiles`, `preferencias`, `cv_base`, `matches`, columnas normalizadas en `ofertas`), relleno de las ofertas existentes y `normalizar_oferta` en `guardar()` · test: tablas y columnas del esquema; una usuaria no lee perfil, CV ni matches de otra (RLS); una oferta nueva y una ya existente quedan normalizadas · cubre: RF-2.4, RF-2.11, RF-2.15
- [ ] T14 — Worker con `perfilar`, `clasificar_perfil`, `generar_cv_base` y `recomendar` · test: perfil nuevo con versión y orígenes guardados; error con paso y motivo; un tope bajo detiene la tarea · cubre: RF-2.1, RF-2.4, RF-2.9, RF-2.12, RT-14
- [ ] T15 — Subida y gestión de CV (`POST/GET/PATCH /api/cv`, descarga) y volumen de archivos · test: tipo o tamaño no admitido → rechazado sin guardar; nombre repetido → 409; archivo con nombre aleatorio; descarga solo de su dueña; el CV estético no se procesa · cubre: RF-2.1, RF-2.1b, RF-2.10
- [ ] T16 — Perfil con versiones (`GET /api/perfil`, respuestas y correcciones) · test: responder o corregir crea versión nueva y conserva la anterior; el dato de la usuaria tiene origen «usuaria»; los CV base y matches de versiones anteriores salen desfasados y no se regeneran solos · cubre: RF-2.2, RF-2.3, RF-2.4
- [ ] T17 — Preferencias y opciones con contadores (`GET/PUT /api/preferencias`, `/opciones`) · test: llegan marcadas desde el CV; un grupo vacío no filtra; los contadores coinciden con el catálogo; contrato, remoto y sueldo los escribe la usuaria · cubre: RF-2.8, RF-2.8b
- [ ] T18 — CV base por la API (`POST/GET/PATCH /api/cv-base`) · test: se genera a petición y no por sí solo; se renombra; el CV rechazado por la verificación no aparece · cubre: RF-2.9, RF-2.1b
- [ ] T19 — Recomendaciones (`POST /api/recomendar`, `GET /api/recomendaciones`, correcciones y exportación) · test: cambiar filtro u orden no hace ninguna llamada al modelo; lo nuevo sale «sin puntuar»; rango por defecto 40-100; la corrección se guarda y no entra al repo · cubre: RF-2.11, RF-2.12, RF-2.13, RF-2.15c
- [ ] T20 — Pantallas de perfil, preferencias y CV base (móvil y escritorio) · test: páginas solo con sesión; JS sin `innerHTML`; cada usuaria ve solo lo suyo; casillas, campo de sueldo y renombrar CV funcionan · cubre: RF-2.1b, RF-2.8, RF-2.15
- [ ] T21 — Pantalla de ofertas recomendadas según `dashboard.png` · test: pestañas, barra de filtros, contador, bloque plegable y columnas con «?»; el salario se ve como en la oferta; la explicación se despliega con «Corregir»; en móvil, tarjetas · cubre: RF-2.15, RF-2.15b, RF-2.15c
- [ ] T22 — Consola (`agente correr` de los 4 agentes, `flujo correr perfilar`, `recomendar`, `eval correr` de los 3 sets, `eval importar-correccion`) · test: cada comando corre en simulado; `--paso-a-paso` y `--traza` guardan un JSON por paso; la corrección solo se copia con confirmación · cubre: RF-2.13, RF-2.16, RT-04, RT-05
- [ ] T23 — CI, Compose (volumen `horma_archivos`), `.env.example`, README, `specs/system.md` y plan de pruebas manuales · test: CI corre los tres sets; el README documenta los comandos; el contrato de import-linter incluye los agentes nuevos · cubre: RF-2.16, RF-2.17, RT-11

## Pendiente de la persona (no se puede hacer sin ti)
- Instalar `python-multipart`, `pypdf` y `python-docx` si `uv` falla con certificados (T01); después, `UV_NO_SYNC=1`.
- Lanzar los tres evals con el modelo real (tope de 1 USD por ejecución) y revisar el resultado (T11, T12).

## Apuntado para el final, si hay tiempo (no se pierde; spec P15)
- Descarga de los CV en PDF.
- Aviso por correo con ofertas nuevas que encajen con los filtros.
- Guardar búsquedas con nombre.
- Programar recomendaciones periódicas.
