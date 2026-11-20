# Instrucciones de trabajo para agentes

Estas reglas se aplican a CUALQUIER agente de IA que trabaje en este repositorio (Claude Code u otros).
Los principios del proyecto están en `specs/constitution.md` (OKF): léelo primero; este archivo es
la capa operativa por encima. La arquitectura del sistema y los requisitos transversales (RT-xx)
están en `specs/system.md`.

## Reglas de oro
- Primero la spec: nunca se escribe código de la aplicación antes de que existan su spec, su plan
  y sus tareas en `specs/NNN-<feature>/`.
- Aclarar antes de especificar: haz las preguntas abiertas y ESPERA las respuestas de la persona
  antes de escribir una spec.
- TDD: un test que falla precede a cada tarea de implementación.
- Cada agente del producto se entrega con su set de evals y su umbral (`evals/<set>/`).
- Secretos: solo en `.env` (nunca se versiona). Las claves se documentan en `.env.example`.
- Los artefactos de conocimiento usan el Open Knowledge Format (OKF): markdown + frontmatter YAML.
- Idioma: toda la documentación y todo lo generado, en español de España.

## Reglas de arquitectura del producto (de specs/system.md)
- Los agentes del producto son módulos Python: `prompt.md` + esquemas Pydantic de entrada y
  salida + `run()`. Sin estado, sin acceso a base de datos ni a disco, y nunca llaman a otro
  agente (RT-01, RT-13).
- Solo `horma/llm/` importa el SDK de Anthropic; toda llamada al modelo pasa por
  `horma.llm.completar` (RT-02).
- La composición de agentes vive solo en `horma/flows/`, detrás de la interfaz `Flow` (RT-12).
- Solo la API y el worker leen y escriben en Postgres.

## Frontend: simetría y alineación (prioridad alta, RF-6.4b)
- Cada pantalla se construye con `tokens.css` y `estilo.css` (spec 006): sin colores ni medidas sueltas.
- **Pantalla nueva (RF-6.9, spec 006):** enlaza `tokens.css` antes de `estilo.css` y `tema.js`; usa la
  cabecera común; se construye con los componentes de la guía; cumple contraste, 44 px y los textos
  de RF-6.8 (nada de «match», «ATS» ni «trazabilidad»). Un componente nuevo se añade antes a la guía.
- Etiquetas, controles y botones de una misma fila comparten alto (`--tap`), separación y línea base.
  Los formularios van en rejilla, nunca con elementos de alturas distintas.
- Incluye los controles nativos (`input[type=file]`, `select`, casillas): se estilan para que encajen.
- Una tarea de frontend no está hecha hasta comprobarla en el navegador a 1280 y 390 px, en claro y
  en oscuro, mirando expresamente alineación y simetría. Si no se ha podido comprobar, se dice.

## Flujo de trabajo
Constitución → Clarify → Spec (EARS) → Plan → Tareas → Implementación (TDD) → Validación → Cambio

## Specs y cambios
- Spec-anchored: la spec es la referencia viva del proyecto. Se divide en spec de sistema
  (lo global: `specs/system.md`) y spec de feature (la de cada cambio: `specs/NNN-<feature>/`).
- Constitución mínima: solo principios y líneas rojas (`specs/constitution.md`).
- Cuando un pedido de la persona contradiga una spec, el pedido gana. Propón el cambio en la spec
  y enséñaselo antes de tocar código. Con su visto bueno, actualiza la spec y regenera `tasks.md`.
- Regenera la spec en lugar de emparcharla.

## Git
- NO hagas commits salvo que la persona lo pida expresamente.
- Nunca añadas a Claude ni a ninguna IA como coautor o colaborador. Sin líneas `Co-Authored-By`.
  Los commits los firma la persona.

## Qué se sube al repo
- Solo documentación técnica: specs, plan, tareas, requisitos, arquitectura, decisiones de diseño y
  guías de uso. Nada de briefs, ideas de mejora, comparativas, planes de pruebas manuales, bitácora,
  diagramas de trabajo ni material de diseño: son documentos de trabajo y van fuera (`.gitignore`, o
  el Cuaderno de Mar). `docs/*` está ignorado salvo lo que se añada a mano con una excepción.
- Formato profesional: concisa y bien estructurada. Un tema por documento, títulos claros, listas y
  tablas cortas, sin repetir lo que ya dice otro documento (enlázalo), sin relleno ni narración de la
  conversación, y con el estado real (qué está hecho y qué no).
- Ante la duda de si un documento es técnico, no lo subas y pregunta.
- Al cambiar el estado de algo, actualiza en el mismo cambio spec, README e `index.md`.

## Estructura
- `specs/`                 artefactos SDD (OKF)
- `horma/`                 paquete de la aplicación (schemas, llm, agents, tools, flows, cli, web)
- `evals/`                 fixtures, ejecutor y resultados de los evals
- `tests/`                 tests unitarios, de arquitectura, de flujos y de RLS
- `config/endpoints.json`  semilla de la tabla de fuentes de ofertas
- `.env` / `.env.example`  variables de entorno
- `AGENTS.md`              este archivo: única fuente de verdad del comportamiento de los agentes
- `CLAUDE.md`              puntero a este archivo
