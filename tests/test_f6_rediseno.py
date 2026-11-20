"""Fase 6 · rediseño 2c «Editorial»: tokens, estilos, cabecera, PWA y guardas de textos (spec 006)."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from horma.config import Ajustes
from horma.web import main as principal

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
FUENTES = ("familjen-grotesk-latin-wght.woff2", "dm-mono-latin-400.woff2", "dm-mono-latin-500.woff2")


def leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


def sin_comentarios(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def tokens_de(bloque: str) -> set[str]:
    return set(re.findall(r"(--[a-z0-9-]+)\s*:", bloque))


def bloque_css(css: str, cabecera: str) -> str:
    """Contenido del bloque `{...}` que sigue a la cabecera dada (con llaves anidadas)."""
    i = css.index(cabecera)
    j = css.index("{", i)
    nivel, k = 1, j + 1
    while nivel:
        nivel += {"{": 1, "}": -1}.get(css[k], 0)
        k += 1
    return css[j + 1:k - 1]


@pytest.fixture
def cliente(monkeypatch):
    ajustes = Ajustes(_env_file=None, app_env="development")
    monkeypatch.setattr(principal, "ajustes", lambda: ajustes)
    app = principal.crear_app(engine=create_engine("sqlite://"), identidad=object())
    with TestClient(app, follow_redirects=False) as c:
        yield c


# --- T02 · tokens y fuentes ---------------------------------------------------------------------
def test_tokens_declara_las_fuentes_y_los_archivos_se_sirven(cliente):
    css = leer("tokens.css")
    assert "Familjen Grotesk" in css and "DM Mono" in css and css.count("@font-face") >= 3
    assert "font-display: swap" in css
    for f in FUENTES:
        assert f"/static/fuentes/{f}" in css
        r = cliente.get(f"/static/fuentes/{f}")
        assert r.status_code == 200 and len(r.content) > 5000
    assert "SIL Open Font License" in leer("fuentes/OFL.txt")
    assert cliente.get("/static/tokens.css").status_code == 200


def test_el_oscuro_define_los_mismos_tokens_de_color_que_el_claro():
    css = sin_comentarios(leer("tokens.css"))
    claro = tokens_de(bloque_css(css, ":root {"))
    oscuro = tokens_de(bloque_css(css, ':root[data-theme="dark"]'))
    por_media = tokens_de(bloque_css(css, ':root:not([data-theme="light"])'))
    colores = {t for t in claro if t in {
        "--bg", "--surface", "--surface-2", "--ink", "--muted", "--line", "--line-strong", "--accent",
        "--on-accent", "--accent-text", "--btn-border", "--bar-track", "--bar-fill", "--tab-active-bg",
        "--tab-active-fg", "--panel-border", "--error", "--tag-l"}}
    assert len(colores) == 18
    assert colores <= oscuro and oscuro == por_media


def test_tokens_trae_la_escala_y_las_medidas_de_la_spec():
    css = leer("tokens.css")
    for token in ("--f-head", "--f-body", "--f-mono", "--fs:", "--fs-title", "--fs-h1:", "--fs-h1-m", "--fs-num",  # noqa: E501
                  "--fs-label", "--ls-head", "--ls-label", "--fw-head", "--fw-num", "--radius: 0", "--bw",
                  "--pad-page", "--pad-page-m", "--row-py", "--col-gap", "--bar-h", "--tap: 44px", "--focus"):
        assert token in css, token
    for valor in ("#f6f6f2", "#c8f031", "#0a0a0a", "#a3201a", "#ff8f87"):
        assert valor in css, valor


# --- T03 · estilo.css ---------------------------------------------------------------------------
def test_estilo_no_escribe_colores_ni_familias_fuera_de_tokens():
    css = sin_comentarios(leer("estilo.css"))
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", css)
    assert "rgb(" not in css and "rgba(" not in css and "hsl(" not in css
    assert not re.search(r"font-family\s*:\s*(?!\s|var\()", css)
    for malo in ("box-shadow", "text-shadow"):
        assert malo not in css


def test_estilo_no_tiene_radios_distintos_de_cero():
    css = sin_comentarios(leer("estilo.css"))
    for valor in re.findall(r"border-radius\s*:\s*([^;}]+)", css):
        assert valor.strip() in ("0", "var(--radius)", "var(--radius-round)"), valor
    assert ".pp" not in css and "--pp-" not in css


def test_el_foco_siempre_se_ve_y_se_respeta_reducir_movimiento():
    css = sin_comentarios(leer("estilo.css"))
    assert re.search(r":focus-visible\s*\{[^}]*outline:\s*var\(--focus\)", css)
    assert "prefers-reduced-motion: reduce" in css
    assert "@media (max-width: 900px)" in css


def test_estilo_trae_los_componentes_de_la_guia():
    css = leer("estilo.css")
    for clase in (".titulo-pantalla", ".entradilla", ".etiqueta-mono", ".secundario", ".boton-texto", ".panel",  # noqa: E501
                  ".panel-desplegado", ".lista-editorial", ".fila-desplegable", ".chevron", ".etiqueta-puesto",  # noqa: E501
                  ".tono-0", ".tono-5", ".barra-compat", ".ayuda-globo", ".aviso", ".tabla-datos", ".cv-hoja",
                  ".cabecera", ".marca", ".linea-anadida", ".linea-quitada", ".tablero", ".tabla-costes"):
        assert clase in css, clase


# --- T04 · cabecera común y tema ----------------------------------------------------------------
PAGINAS_USUARIA = ("perfil", "preferencias", "cv-base", "anadir-oferta", "recomendadas", "candidaturas",
                   "candidatura")
TODAS = [p.stem for p in sorted(ESTATICOS.glob("*.html")) if p.stem != "offline"]


@pytest.mark.parametrize("nombre", TODAS)
def test_toda_pagina_enlaza_tokens_antes_que_estilo_y_carga_tema_sin_marco(nombre):
    html = leer(f"{nombre}.html")
    assert 'class="pp"' not in html
    assert html.index("/static/tokens.css") < html.index("/static/estilo.css")
    assert re.search(r'<script src="/static/tema\.js"></script>', html[:html.index("</head>")])
    assert "tema.js" not in html[html.index("</head>"):]  # en <head>, sin defer, para no parpadear


@pytest.mark.parametrize("nombre", PAGINAS_USUARIA)
def test_las_paginas_de_usuaria_tienen_cabecera_nav_principal_y_un_h1(nombre):
    html = leer(f"{nombre}.html")
    assert 'id="cabecera"' in html and 'id="pestanas"' in html and 'aria-label="Principal"' in html
    assert html.count("<h1") == 1 and "titulo-pantalla" in html


def test_la_cabecera_de_comun_js_pinta_pestanas_persona_tema_y_salir():
    js = leer("comun.js")
    assert "aria-current" in js and "/api/perfil" in js and "nombre" in js
    assert '"img"' not in js and "<img" not in js                         # nunca una foto (RF-6.3)
    assert "vincularTema" in js and '"Salir"' in js and '"Tema oscuro"' in js
    assert len(re.findall(r'\["[^"]+", "/[a-z-]+"\]', js)) == 6           # las seis pestañas (P2)


@pytest.mark.parametrize("nombre", ("index", "ingesta", "costes"))
def test_portada_e_ingesta_y_costes_llevan_cabecera_minima(nombre):
    html = leer(f"{nombre}.html")
    assert 'class="cabecera' in html and 'class="marca"' in html
    assert 'id="tema"' in html and 'id="salir"' in html


def test_tema_js_aplica_el_tema_guardado_con_try_catch_y_expone_el_boton():
    js = leer("tema.js")
    assert "horma-tema" in js and "try" in js and "catch" in js
    assert "data-theme" in js and "aria-pressed" in js
    assert "vincularTema" in js and "alternarTema" in js
    assert "innerHTML" not in js


# --- T05 · PWA ----------------------------------------------------------------------------------
def test_el_manifiesto_y_los_theme_color_son_los_de_2c(cliente):
    m = cliente.get("/manifest.webmanifest").json()
    assert m["theme_color"] == "#f6f6f2" and m["background_color"] == "#f6f6f2"
    for nombre in TODAS:
        html = leer(f"{nombre}.html")
        assert '<meta name="theme-color" content="#f6f6f2" media="(prefers-color-scheme: light)">' in html, nombre  # noqa: E501
        assert '<meta name="theme-color" content="#0a0a0a" media="(prefers-color-scheme: dark)">' in html, nombre  # noqa: E501
        assert "#6b3f2a" not in html


def test_el_service_worker_precarga_tokens_tema_y_fuentes_con_cache_nueva():
    js = leer("sw.js")
    assert 'const VERSION = "horma-v2"' in js
    for archivo in ("/static/tokens.css", "/static/estilo.css", "/static/tema.js", "/static/offline.html",
                    *(f"/static/fuentes/{f}" for f in FUENTES)):
        assert archivo in js, archivo


def test_sin_conexion_se_ve_con_la_paleta_2c_y_solo_con_estilos_precargados():
    html = leer("offline.html")
    assert "Sin conexión" in html and "<h1" in html and 'class="pp"' not in html
    assert html.index("/static/tokens.css") < html.index("/static/estilo.css")
    assert "/static/tema.js" in html and 'class="marca"' in html
    assert "#6b3f2a" not in html and "<script src=\"/static/app.js\"" not in html


# --- T06 · guardas de textos (RF-6.8) -----------------------------------------------------------
PROHIBIDAS = re.compile(r"\bmatch(?:es)?\b|\bATS\b|trazabilidad", re.I)


def textos_visibles_html(html: str) -> list[str]:
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    atributos = re.findall(r'\b(?:aria-label|placeholder|title|alt)="([^"]*)"', html)
    return [t for t in re.split(r"<[^>]+>", html) if t.strip()] + atributos


def textos_de_js(js: str) -> list[str]:
    js = re.sub(r"(?m)^\s*//.*$|\s//\s.*$", "", js)                  # comentarios
    js = js.replace("[*_`]", "")  # clase de regex con comilla invertida
    cadenas = re.compile(r'"((?:[^"\\\n]|\\.)*)"|`((?:[^`\\]|\\.)*)`')
    return [a or b for a, b in cadenas.findall(js)]


@pytest.mark.parametrize("nombre", TODAS + ["offline"])
def test_ningun_html_dice_match_ats_ni_trazabilidad(nombre):
    for t in textos_visibles_html(leer(f"{nombre}.html")):
        assert not PROHIBIDAS.search(t), f"{nombre}.html: {t.strip()[:80]}"


@pytest.mark.parametrize("js", sorted(p.name for p in ESTATICOS.glob("*.js")))
def test_ningun_js_dice_match_ats_ni_trazabilidad_en_sus_textos(js):
    for t in textos_de_js(leer(js)):
        if t.startswith(("/", "http")) or "${" in t and "/api/" in t:     # rutas de la API, no texto visible
            continue
        assert not PROHIBIDAS.search(t), f"{js}: {t[:80]}"


# --- Bloque C · Recomendadas (T07-T10) ----------------------------------------------------------
def test_recomendadas_estructura_h1_entradilla_filtros_contador_y_guia():  # T07
    html = leer("recomendadas.html")
    assert 'class="titulo-pantalla">Recomendadas' in html and "sin fraudes ni ofertas fantasma" in html
    assert re.search(r'<form id="filtros"[^>]*role="search"', html)
    for ident in ("grupos", "solo-remoto", "solo-salario", "sueldo-minimo", "rango-min", "rango-max", "orden",
                  "buscar", "recomendar", "contador"):
        assert f'id="{ident}"' in html, ident
    assert re.search(r'id="contador"[^>]*aria-live="polite"|aria-live="polite"[^>]*id="contador"', html)
    assert '<details class="leer' in html and "Cómo leer las recomendaciones" in html
    assert "Corregir explicación" in html and "Modificar" not in html
    assert "Condiciones" not in html


def test_recomendadas_tabla_con_columnas_barra_meter_y_sin_progress():  # T08
    js = leer("recomendadas.js")
    for columna in ("Oferta", "Puesto", "Compatibilidad", "Salario", "Lugar", "Publicado"):
        assert f'["{columna}",' in js, columna
    assert '"Candidatura"' not in js.split("const MAX_PUNTUANDO")[0]  # ya no es columna
    assert '"meter"' in js and "aria-valuenow" in js and "aria-valuemin" in js and "aria-valuemax" in js
    assert "barra-compat" in js and "progress" not in js
    assert "Sin puntuar" in js and "No publicado" in js
    assert "Condiciones" not in js and "cond-" not in js and "celdaCandidatura" not in js


def test_recomendadas_fila_desplegable_con_acciones():  # T09
    js = leer("recomendadas.js")
    for pieza in ("aria-expanded", "aria-controls", "Por qué te la recomendamos", "Corregir explicación",
                  "/correccion", "Preparar candidatura", "Preparar otra igualmente", "Generar CV base",
                  "fila-detalle", "stopPropagation", "accionesCandidatura"):
        assert pieza in js, pieza
    assert '"Modificar' not in js and "details.porque" not in js
    assert re.search(r"abiertas?\b", js)  # la primera sale abierta


def test_recomendadas_movil_mas_filtros_y_ayuda_como_globo():  # T10
    css, js, html = leer("estilo.css"), leer("recomendadas.js"), leer("recomendadas.html")
    assert re.search(r"@media \(max-width: 900px\)\s*\{[^@]*\.tabla-ofertas[^@]*attr\(data-", css, re.S)
    assert 'id="mas-filtros"' in html and 'aria-expanded="false"' in html and "Más filtros" in html
    assert "Menos filtros" in js
    assert "Qué significa" in js and "aria-describedby" in js and "Escape" in js and "ayuda-globo" in js
    assert ".title" not in js and 'title="' not in html


def test_resto_de_pantallas_usan_los_componentes_2c():  # T11-T15
    for pagina in ("perfil", "preferencias", "anadir-oferta", "cv-base", "candidaturas", "candidatura"):
        html = leer(f"{pagina}.html")
        assert 'class="titulo-pantalla"' in html and 'class="pp"' not in html, pagina
    assert "lista-editorial" in leer("index.html") and "lista-editorial" in leer("perfil.html")
    assert 'class="fila panel"' in leer("perfil.html")  # subida en un panel
    assert 'class="grupo panel"' in leer("preferencias.html")
    assert leer("anadir-oferta.html").count('class="panel"') == 2
    assert "cond-" not in leer("candidaturas.js")
    js = leer("candidatura.js")
    assert '"Revisa esto"' in js and '"panel"' in js
    assert js.count('"boton secundario"') >= 1  # las descargas no compiten
    assert ".columna-cerrada > summary" in leer("estilo.css")


def test_objetivos_tactiles_de_44_px():  # T17 · RF-6.7b
    css = sin_comentarios(leer("estilo.css"))
    cerradas = re.search(r"\.columna-cerrada > summary\{[^}]*min-height: var\(--tap\)", css)
    assert cerradas, "«Cerradas» debe medir al menos var(--tap) de alto"
    assert re.search(r"a\.bloque\{[^}]*min-height: var\(--tap\)", css)


def test_pais_en_texto_en_recomendadas():  # T17b · hallazgo 6
    js = leer("recomendadas.js")
    assert "Intl.DisplayNames" in js and "nombrePais(o.pais)" in js
