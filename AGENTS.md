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

## Flujo de trabajo
Constitución → Clarify → Spec (EARS) → Plan → Tareas → Implementación (TDD) → Validación → Cambio

## Git
- NO hagas commits salvo que la persona lo pida expresamente.
- Nunca añadas a Claude ni a ninguna IA como coautor o colaborador. Sin líneas `Co-Authored-By`.
  Los commits los firma la persona.

## Estructura
- `specs/`                 artefactos SDD (OKF)
- `horma/`                 paquete de la aplicación (schemas, llm, agents, tools, flows, cli, web)
- `evals/`                 fixtures, ejecutor y resultados de los evals
- `tests/`                 tests unitarios, de arquitectura, de flujos y de RLS
- `config/endpoints.json`  semilla de la tabla de fuentes de ofertas
- `.env` / `.env.example`  variables de entorno
- `AGENTS.md`              este archivo: única fuente de verdad del comportamiento de los agentes
- `CLAUDE.md`              puntero a este archivo
