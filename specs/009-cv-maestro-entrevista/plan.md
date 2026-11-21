---
type: plan
title: cv-maestro-entrevista — Plan técnico (9a)
description: Archivos y cambios que cubren la parte 9a de la fase 9 — huecos y avisos por reglas, otras actividades del CV, elección de longitud, puestos recomendados con coincidencia por frase y términos excluidos, y CV maestro visible en Perfil. El plan de 9b se escribe al cerrar 9a.
tags: [plan, perfil, preferencias, agentes, frontend, migracion]
status: active
sources: [./spec.md, ./clarifications.md, ../system.md, ../008-portada-ofertas/plan.md]
generated: { by: claude-code, at: 2026-11-21 }
verified: { by: human, at: 2026-11-21 }
stale_after: null
---

# cv-maestro-entrevista — Plan (9a)

## Arquitectura
Sin agentes nuevos. Cambian dos prompts: `extractor_perfil` (otras actividades, RF-9.1d) y
`clasificador_postulante` (puestos, RF-9.3). Huecos, avisos y coincidencia de títulos son **código puro** en
`horma/tools/`, sin modelo (P2). Los flujos siguen sin tocar la base de datos (RT-12); solo API y worker
leen y escriben en Postgres.

| Requisito | Dónde |
|---|---|
| RF-9.1, 9.1b | `tools/detectar_huecos.py` nuevo |
| RF-9.1d | `schemas/perfil.py` (`Actividad`, `PeriodoCubierto`); `extractor_perfil/prompt.md`; `flows/perfilar.py` (`quitar_sensibles`); `tools/componer_cv_maestro.py`; `perfil.js` (sección «Otras actividades») |
| RF-9.1c, 9.2, 9.2b | `tools/avisos_perfil.py` nuevo; `routers/perfil.py` (`GET /api/perfil/avisos`) |
| RF-9.2c | migración `0021`, tabla `avisos_vistos`; `repositories/perfiles.py`; `PUT /api/perfil/avisos/visto` |
| RF-9.2d | migración `0021`, tabla `ajustes_perfil`; `PUT /api/perfil/longitud`. La usa `redactor_cv` en 9b (RF-9.10f) |
| RF-9.3 | `clasificador_postulante/schemas.py` y `prompt.md`; `flows/perfilar.py` y `flows/clasificar_perfil.py` |
| RF-9.3b | `schemas/preferencias.py`; migración `0021`; `repositories/perfiles.py`; `recomendadas.js` («Qué buscas») |
| RF-9.3c, 9.3d | `tools/normalizar_titulo.py` nuevo; `tools/buscar_ofertas.py`; migración `0021` (`ofertas.titulo_norm`); `tools/normalizar_oferta.py` |
| RF-9.3e | `tests/fixtures/titulos_puestos.json` (etiquetado por Mar) y su test |
| RF-9.4, 9.5 | `perfil.html` / `perfil.js` («Tu CV maestro» con `cvBonito`; orden de bloques) |

## Datos (migración `0021_fase9a_huecos_puestos.py`)
- `preferencias`: `puestos text[] NOT NULL DEFAULT '{}'`, `puestos_sugeridos jsonb NOT NULL DEFAULT '[]'`
  (título + dato que lo justifica) y `excluidos text[] NOT NULL DEFAULT '{}'`.
- `ofertas.titulo_norm text`: se rellena con `normalizar_titulo` en la migración (por lotes, en Python) y al
  procesar cada oferta nueva.
- `avisos_vistos (usuaria_id, clave text, huella text, creado_en, PRIMARY KEY (usuaria_id, clave))`.
- `ajustes_perfil (usuaria_id PRIMARY KEY, longitud_cv text CHECK (longitud_cv IN ('mantener','sintetizar')))`.
- Las dos tablas nuevas: RLS `propia` FOR ALL y `GRANT SELECT, INSERT, UPDATE, DELETE` (patrón de `0013`).
- El perfil se guarda como JSON: `actividades` y `periodos_cubiertos` no necesitan columnas; los perfiles
  antiguos los leen vacíos.

## Otras actividades (RF-9.1d)
- `Actividad(descripcion, inicio, fin, origen)`: voluntariado, cuidados, viajes, excedencias… con su cita
  literal (RT-08). Sale en el CV maestro en «Otras actividades».
- `PeriodoCubierto(inicio, fin)`: sin motivo ni cita. Lo crea **solo el código**: en `quitar_sensibles`, una
  actividad cuyo texto o cita tenga un rasgo personal (`rasgos_personales`: salud, familia…) se convierte en
  periodo cubierto y se descarta el resto. No sale en el CV maestro ni en Mi perfil; solo cuenta para los huecos.
- Mi perfil: sección «Otras actividades» editable (descripción, inicio, fin), igual que Proyectos. Lo que
  escribe ella también pasa por `rasgos_personales`: si tiene un rasgo, se guarda como periodo cubierto y se
  avisa con el texto de RF-9.8e.

## Huecos (RF-9.1)
- `detectar_huecos(perfil, hoy) -> list[Hueco(inicio, fin, meses)]`. Intervalos de experiencias, formación,
  actividades y periodos cubiertos. `AAAA` → enero a diciembre; `AAAA-MM` → ese mes; «actual» → hoy; sin
  fecha de inicio → no cuenta. Se funden los solapados y se mide desde el primer inicio hasta hoy.
  Hueco = 6 meses o más.
- Clave estable: `hueco:AAAA-MM:AAAA-MM`. Texto: «Entre marzo de 2019 y enero de 2020 no consta trabajo ni
  formación.»

## Avisos por reglas (RF-9.2)
- `avisos_perfil(perfil, cv_maestro, textos_cv) -> list[Aviso(clave, huella, texto, seccion)]`:
  - `largo`: más de 1.000 palabras en el CV maestro. Lleva las dos opciones de RF-9.2d en lugar de «Corregir»;
    elegir una cuenta como «dado por visto».
  - `sin_descripcion:<i>` y `sin_cifras:<i>`: por experiencia (clave por puesto y empresa normalizados). Sin
    cifras = la descripción no tiene ningún dígito ni porcentaje.
  - `sin_resumen`.
  - `sin_contacto:<cv_id>`: un CV fuente sin correo ni teléfono (regex sobre el texto; no se guarda nada).
- `huella` = hash corto de lo que causa el aviso (la descripción, el número de palabras redondeado a 100,
  el texto del CV). Un aviso se oculta si hay `avisos_vistos` con la misma clave **y** la misma huella; si la
  causa cambia, vuelve (RF-9.2c).
- `GET /api/perfil/avisos`: huecos + avisos, sin los vistos. Se calcula al pedirlo; no se guarda.
- `PUT /api/perfil/avisos/visto {clave, huella}`; `PUT /api/perfil/longitud {longitud}`.

## Puestos (RF-9.3)
- `clasificador_postulante` devuelve `ClasificacionPostulante`: la `Taxonomia` de hoy más
  `puestos: list[PuestoSugerido(titulo, idioma: "es" | "en", dato)]`, 8-15. El código descarta los que no
  citen un `dato` presente en el perfil (puesto, titulación, habilidad o resumen) (RT-08).
- `preferencias_desde_cv` pasa los puestos. `aplicar_preferencias_del_cv`: `puestos_sugeridos` se sustituye
  siempre; `puestos` solo si su origen no es «usuaria» (RF-9.3b). `excluidos` es siempre de ella.
  `_ClasificarPerfil` aplica los puestos igual.
- `normalizar_titulo(t)`: NFKD sin tildes, minúsculas, guiones y signos → espacios, cada palabra en singular
  (quita «es»/«s» final con reglas cortas), espacios únicos.
- `buscar_ofertas`: con familias o puestos marcados, la condición es
  `(familia = ANY(familias) [OR familia IS NULL si hay familias] OR <título casa con un puesto>)`; casar =
  `' ' || titulo_norm || ' ' LIKE '% ' || puesto_norm || ' %'`. Con excluidos:
  `NOT (<título casa con un excluido>)`. Orden «compatibles»: +2 si el título casa con un puesto.
- Set de RF-9.3e: Claude saca ~150 títulos reales del catálogo con sus puestos candidatos; Mar marca acierto o
  falso positivo; el test mide precisión ≥ 0,95 y cobertura ≥ 0,90.

## Pantallas (RF-9.3b, RF-9.4, RF-9.5)
- «Qué buscas»: grupo **Área** (las 19 familias, como hoy) y grupo **Puestos** (casillas con los sugeridos y
  los suyos, «Seleccionar todo», «Quitar selección», campo para añadir); campo **Términos excluidos** (lista
  con quitar). Misma rejilla y `--tap` (RF-6.4b).
- Perfil, en el orden de RF-9.5: Tus CV · Mi perfil · «Preguntas pendientes y avisos (n)» · «Tu CV maestro»
  (`cvBonito`, fecha, versión, frase de RF-9.4, «Editar» por sección) · Tu estilo.
- Componentes: el aviso con dos acciones y el aviso con elección de longitud se añaden antes a la guía (RF-6.9).

## Tests
- `detectar_huecos`: 8 meses → hueco; 4 → no; año suelto no inventa huecos; solapados; voluntariado y periodo
  cubierto tapan el hueco; sin fechas no cuenta.
- `quitar_sensibles`: «baja por enfermedad 2019-2020» → periodo cubierto sin texto; voluntariado se queda con
  su cita.
- `avisos_perfil`: cada aviso; visto no vuelve con la misma huella y vuelve si cambia la descripción.
- `normalizar_titulo` y `buscar_ofertas`: «Data Analyst» casa con «Senior Data Analyst (m/f)» y no con «Data
  Entry»; plural; excluidos; título de otra familia entra por puesto.
- Set de títulos: precisión y cobertura en umbral.
- Migración: columnas, backfill de `titulo_norm`, RLS de `avisos_vistos` y `ajustes_perfil`.
- API: `/api/perfil/avisos`, visto, longitud; otra usuaria no ve lo ajeno; `GET` del CV maestro de otra → 404.
- Preferencias: una subida nueva no pisa los puestos que marcó ella.
- Estáticos: orden de bloques de Perfil; CV maestro con `textContent`.
- Navegador: Perfil y «Qué buscas» a 1280 y 390 px, en claro y en oscuro.

## Coste
- Evals de `perfil` con modelo real (cambian `extractor_perfil` y `clasificador_postulante`): se avisa con la
  estimación antes de lanzarlas. Se añaden casos con voluntariado, baja médica y puestos esperados.
- Prueba manual: subir un CV real (una llamada de perfil). Se avisa antes.
