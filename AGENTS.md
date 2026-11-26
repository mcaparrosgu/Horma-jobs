# Instrucciones de trabajo para agentes

Estas reglas se aplican a CUALQUIER agente de IA que trabaje en este repositorio (Claude Code u otros).
Los principios del proyecto están en `specs/constitution.md` (OKF): léelo primero; este archivo es
la capa operativa por encima. La arquitectura del sistema y los requisitos transversales (RT-xx)
están en `specs/system.md`.

## Reglas de oro
- **Una decisión, toda la documentación (MUY IMPORTANTE).** Cuando cambia un estado, una decisión, una cifra o
  un orden, se actualizan en el mismo cambio y el mismo día todos los documentos que lo mencionan: `specs/prd.md`,
  `specs/index.md`, las specs y sus `tasks.md`, `docs/hoja-de-ruta.md`, el README y los encargos. Antes de dar la
  tarea por cerrada, busca el dato con `grep` en todo el repo y en `docs/`; si queda un sitio sin tocar, no está
  hecha. Una versión a medias provoca contradicciones y caos.
- Primero la spec, a su medida:
  - Cambio grande (módulo, agente, esquema, tabla, pantalla o flujo nuevos): spec, plan y tareas en
    `specs/NNN-<feature>/` antes del código.
  - Cambio pequeño (corrección, refactor sin cambio de comportamiento, texto, configuración, o una pieza
    de ingesta que cumple RT-15 a RT-19 sin tocar esquemas: conector, parser, normalizador, cola o fuente
    nueva): test que falla y una línea en el `tasks.md` de la spec vigente. Sin spec nueva.
- Aclarar solo lo que cambia el resultado: pregunta antes de especificar cuando la respuesta cambie lo que
  se construye. Si la intención está clara, toma la opción más simple, anota el supuesto y sigue, sin
  bloqueos ni preguntas innecesarias.
- TDD: un test que falla precede a cada tarea de implementación.
- Cada agente del producto se entrega con su set de evals y su umbral (`evals/<set>/`).
- Secretos: solo en `.env` (nunca se versiona). Las claves se documentan en `.env.example`.
- Los artefactos de conocimiento usan el Open Knowledge Format (OKF): markdown + frontmatter YAML.
- Idioma: toda la documentación y todo lo generado, en español de España.
- Simple primero (constitución): antes de proponer un agente, una tabla, una pantalla o un paso nuevo,
  comprueba si basta con código, con algo que ya existe o con quitar algo. Si propones añadir, di qué
  opción más simple descartaste y por qué.
- Documentación mínima, también en los documentos de trabajo: nada de documentos nuevos si cabe como
  sección de uno existente; enlaza en vez de repetir; solo lo esencial.
- Comunicación eficiente: empieza por la respuesta o el resultado; sin preámbulos ni recapitulaciones;
  frases cortas y listas breves; explica el porqué en una o dos líneas. Los informes y documentos
  sintetizan: conclusiones y decisiones primero, evidencia mínima, sin repetir lo que ya está en otro
  documento. La brevedad no oculta riesgos, costes ni cosas irreversibles: se avisan siempre.
- Encargos de investigación (`docs/investigacion/encargos.md`): al entregar el informe, el encargo no se
  borra. Se le pone «(HECHA)» delante del título y, debajo, la ruta del informe.

## Reglas de arquitectura del producto (de specs/system.md)
- Los agentes del producto son módulos Python: `prompt.md` + esquemas Pydantic de entrada y
  salida + `run()`. Sin estado, sin acceso a base de datos ni a disco, y nunca llaman a otro
  agente (RT-01, RT-13).
- Solo `horma/llm/` importa el SDK de Anthropic; toda llamada al modelo pasa por
  `horma.llm.completar` (RT-02).
- La composición de agentes vive solo en `horma/flows/`, detrás de la interfaz `Flow` (RT-12).
- Solo la API y el worker leen y escriben en Postgres.
- Ingesta: los conectores, parsers y colas de fuentes viven en `horma/ingesta`, sin credenciales de
  BD (entregan por `POST /ofertas`) y cumplen RT-15 a RT-19.
- Agregación de ofertas públicas, autorizada (PRD, 7.1): se pueden desarrollar conectores, parsers, colas
  e integraciones con portales, ATS, feeds, sitemaps y API de índices públicos, con `httpx`, Apify, Zyte,
  Crawlee, Scrapy o Firecrawl. Siempre con ritmo por dominio, `Retry-After` y reintentos con espera,
  extracción incremental, sin datos personales de terceros, sin cuentas ni contraseñas, y sin eludir
  captchas ni bloqueos. Nunca LinkedIn ni Indeed.

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
- El agente hace esa comprobación: `docker compose up -d --build` y `node tests/capturas.js` (Playwright con el
  Chrome instalado; la extensión de Chrome no baja a 390 px). Mira las imágenes, no solo el «ok». Cubre las
  pantallas sin datos; las que necesitan datos o clics, se amplían en el script o se declaran sin comprobar.

## Flujo de trabajo
Constitución → Clarify → Spec (EARS) → Plan → Tareas → Implementación (TDD) → Validación → Cambio

## Specs y cambios
- Spec-anchored: la spec es la referencia viva del proyecto. Se divide en spec de sistema
  (lo global: `specs/system.md`) y spec de feature (la de cada cambio: `specs/NNN-<feature>/`).
- Constitución mínima: solo principios y líneas rojas (`specs/constitution.md`).
- Cuando un pedido de la persona contradiga una spec, el pedido gana. Propón el cambio en la spec,
  con tu recomendación, y enséñaselo SIEMPRE antes de tocar código. Con su visto bueno, actualiza la
  spec y regenera `tasks.md`.
- Regenera la spec en lugar de emparcharla.

## Git
- NO hagas commits salvo que la persona lo pida expresamente.
- Nunca añadas a Claude ni a ninguna IA como coautor o colaborador. Sin líneas `Co-Authored-By`.
  Los commits los firma la persona.
- `main` está protegida: todo entra por PR. Una rama por PR, creada desde `main` al día. Los docs de la tarea
  van en su mismo PR; el «fusionada» se anota en el PR siguiente, nunca en una rama aparte de solo docs.
- Para apartar trabajo, un commit provisional en su rama; nunca `git stash`.
- Al fusionar un PR (GitHub borra la rama remota solo): `git switch main`, `git pull --prune` y
  `git branch -d <rama>`. Si un agente trabajó en un worktree, `git worktree remove <carpeta>`.

## Qué se sube al repo
- Solo documentación técnica: specs, plan, tareas, requisitos, arquitectura, decisiones de diseño y
  guías de uso. Nada de briefs, ideas de mejora, comparativas, planes de pruebas manuales, bitácora,
  diagramas de trabajo ni material de diseño: son documentos de trabajo y van fuera (`.gitignore`, o
  el Cuaderno de Mar). `docs/*` está ignorado salvo lo que se añada a mano con una excepción.
- Formato profesional: concisa y bien estructurada. Un tema por documento, títulos claros, listas y
  tablas cortas, sin repetir lo que ya dice otro documento (enlázalo), sin relleno ni narración de la
  conversación, y con el estado real (qué está hecho y qué no).
- Ante la duda de si un documento es técnico, no lo subas y dilo al cerrar la tarea.
- El estado de cada fase vive solo en `specs/index.md`; los `tasks.md` llevan las casillas y el README enlaza.
  Al cambiar el estado de algo, actualiza en el mismo cambio `index.md` y las casillas.
