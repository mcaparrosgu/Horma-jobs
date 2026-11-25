# CLAUDE.md

Las instrucciones de trabajo de este repositorio están en **[AGENTS.md](./AGENTS.md)**.
Léelo y síguelo. No dupliques reglas aquí: `AGENTS.md` es la única fuente de verdad.

## Regla crítica: documentación sincronizada
**Todo cambio de estado, decisión, cifra u orden se refleja a la vez en TODA la documentación que lo cita**
(PRD, `specs/index.md`, specs y `tasks.md`, `docs/hoja-de-ruta.md`, README, encargos). Antes de cerrar, busca el
dato con `grep` en el repo y en `docs/`. Detalle en `AGENTS.md`, primera regla de oro.

## Solo Claude Code: contexto mínimo
- En Horma solo se usan los skills, plugins y servidores MCP que sirven a Horma. Los demás están apagados en
  `.claude/settings.local.json` (`skillOverrides` y `enabledPlugins`); los servidores MCP, con `/mcp`.
- No invoques ni actives uno ajeno a Horma. Si aparece uno nuevo en el listado que no sea de Horma, avisa a
  Mar para apagarlo ahí.
