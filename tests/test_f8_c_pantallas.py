"""Fase 8 · bloques C, D y E (pantallas): guía, landing, pestañas, Catálogo, «Qué buscas», vista, descartes,
oferta original y barra de avance (T07-T14 y T19, spec 008). Los estáticos leen los archivos; las
rutas usan la
API con la base de pruebas."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from horma import config
from horma.schemas.perfil import Perfil
from horma.web.db import sesion_de
from horma.web.main import crear_app
from horma.web.repositories import perfiles

RAIZ = Path(__file__).resolve().parent.parent
ESTATICOS = RAIZ / "horma" / "web" / "static"
ADMIN = "google-admin"
PROHIBIDAS = re.compile(r"\b(match|ATS|trazabilidad)\b", re.IGNORECASE)


def leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


# --- T07 · guía: Ventana y Barra de avance -------------------------------------------------------------
def test_la_guia_recoge_ventana_y_barra_de_avance():
    spec = (RAIZ / "specs" / "006-rediseno-2c" / "spec.md").read_text(encoding="utf-8")
    assert "| **Ventana**" in spec and "| **Barra de avance**" in spec


def test_ventana_y_barra_de_avance_existen_con_tokens_y_perfil_usa_ventana():
    css = leer("estilo.css")
    assert "dialog.ventana" in css and ".barra-avance" in css
    assert ".visor{" not in css and "#visor-cuerpo{" not in css
    bloque = css[css.index("/* ── Ventana"):css.index("/* ── Documento")]
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", bloque)  # sin colores sueltos: solo tokens
    assert "var(--bar-track)" in bloque and "var(--bar-fill)" in bloque
    assert 'class="ventana alta"' in leer("perfil.html")


def test_la_barra_de_avance_es_un_progressbar_con_valor_y_texto():
    js = leer("comun.js")
    assert 'setAttribute("role", "progressbar")' in js and "aria-valuenow" in js
    assert "${v} %" in js and "innerHTML" not in js


# --- T08 · landing (spec 010, RF-10.1: «Continuar con Google» directo, sin pantalla /entrar) -------------
def test_la_landing_dice_lo_que_hace_horma_y_lleva_directo_a_google():
    html = leer("index.html")
    assert html.count('href="/auth/google/login"') == 2   # arriba a la derecha y al final de la página
    assert html.count(">Continuar con Google<") == 2 and 'href="/entrar"' not in html
    for frase in ("Ofertas que encajan contigo, y tu CV listo para cada una.", "Ofertas revisadas",
                  "Compatibilidad explicada", "También las que encuentras tú", "CV y carta a medida",
                  "Tú decides", "Entra con Google", "Sube tu CV", "Mira tus ofertas y prepara tu candidatura"):  # noqa: E501
        assert frase in html
    assert "<script>" not in html and "style=" not in html
    assert not PROHIBIDAS.search(re.sub(r"<[^>]+>", " ", html))


def test_la_landing_enlaza_tokens_antes_que_estilo_y_el_tema():
    h = leer("index.html")   # RF-6.9
    assert h.index("tokens.css") < h.index("estilo.css") and "tema.js" in h
    assert not (ESTATICOS / "entrar.html").exists()


class IdentidadFalsa:
    async def redirigir(self, request, redirect_uri):
        from starlette.responses import RedirectResponse
        return RedirectResponse("https://accounts.google.test/auth")

    async def sub_desde_callback(self, request) -> str:
        return request.query_params["code"]


@pytest.fixture
def app(motor_app, bd_limpia, monkeypatch):
    monkeypatch.setenv("HORMA_ADMINS", ADMIN)
    config.ajustes.cache_clear()
    yield crear_app(engine=motor_app, identidad=IdentidadFalsa())
    config.ajustes.cache_clear()


def entrar(app, sub="google-A"):
    c = TestClient(app, follow_redirects=False)
    assert c.get(f"/auth/google/callback?code={sub}").status_code == 302
    return c


def dar_perfil(motor_app, motor_migrador, sub="google-A"):
    with motor_migrador.connect() as s:
        u = s.execute(text("select id from usuarias where google_sub=:s"), {"s": sub}).scalar_one()
    base = {"taxonomia": {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion",
                          "nivel": "junior", "stack": []},
            "experiencias": [{"puesto": "Camarera", "empresa": "Bar Sol",
                              "origen": {"fuente": "cv", "cv_id": 1, "fragmento": "Camarera en Bar Sol"}}]}
    with sesion_de(motor_app, u) as s:
        pid, version = perfiles.nueva_version(s, u)
        perfiles.guardar_perfil(s, u, pid, Perfil.model_validate({**base, "version": version}), "# Ana")


@pytest.mark.bd
def test_sin_sesion_la_raiz_es_la_landing_y_entrar_redirige_a_ella(app):
    c = TestClient(app, follow_redirects=False)
    r = c.get("/")
    assert r.status_code == 200 and "Continuar con Google" in r.text and "Ofertas que encajan contigo" in r.text  # noqa: E501
    r = c.get("/entrar")
    assert r.status_code == 308 and r.headers["location"] == "/"


@pytest.mark.bd
def test_con_sesion_y_sin_perfil_va_a_perfil_y_con_perfil_a_ofertas(app, motor_app, motor_migrador):
    c = entrar(app)
    r = c.get("/")
    assert r.status_code == 302 and r.headers["location"] == "/perfil"
    dar_perfil(motor_app, motor_migrador)
    r = c.get("/")
    assert r.status_code == 302 and r.headers["location"] == "/ofertas"


@pytest.mark.bd
def test_el_callback_de_google_vuelve_a_la_raiz_que_decide(app):
    c = TestClient(app, follow_redirects=False)
    r = c.get("/auth/google/callback?code=google-A")
    assert r.status_code == 302 and r.headers["location"] == "/"


# --- T09 · pestañas sin Preferencias --------------------------------------------------------------------
def test_pestanas_son_tres_y_la_marca_lleva_a_ofertas():
    js = leer("comun.js")
    bloque = js[js.index("const PESTANAS"):js.index("];", js.index("const PESTANAS"))]
    nombres = re.findall(r'\["([^"]+)", "/[^"]+"\]', bloque)
    assert nombres == ["Ofertas", "Candidaturas", "Perfil"]
    assert 'marca.href = "/ofertas"' in js


@pytest.mark.bd
def test_preferencias_ya_no_existe(app):
    assert entrar(app).get("/preferencias").status_code == 404   # ya no existe (P20)
    assert TestClient(app, follow_redirects=False).get("/preferencias").status_code == 404


def test_ninguna_pantalla_enlaza_a_preferencias():
    for archivo in sorted(ESTATICOS.glob("*.html")) + sorted(ESTATICOS.glob("*.js")):
        assert 'href="/preferencias' not in archivo.read_text(encoding="utf-8"), archivo.name
    assert not (ESTATICOS / "preferencias.html").exists() and not (ESTATICOS / "preferencias.js").exists()
    assert '"/preferencias"' not in leer("comun.js")


# --- T10 · Admin › Catálogo -----------------------------------------------------------------------------
@pytest.mark.bd
def test_catalogo_es_solo_para_administradoras(app):
    assert entrar(app, "google-A").get("/catalogo").status_code == 403
    r = entrar(app, ADMIN).get("/catalogo")
    assert r.status_code == 200 and '<script src="/static/catalogo.js"' in r.text
    assert TestClient(app, follow_redirects=False).get("/catalogo").status_code == 401


def test_las_pantallas_de_admin_llevan_las_cuatro_subpestanas():
    for archivo in ("ingesta.html", "catalogo.html", "costes.html", "envios.html"):
        h = leer(archivo)
        sub = h[h.index('<nav class="subpestanas"'):h.index("</nav>", h.index('<nav class="subpestanas"'))]
        assert [m for m in re.findall(r'href="(/[a-z]+)"', sub)] == ["/ingesta", "/catalogo", "/costes", "/envios"], archivo  # noqa: E501
        assert sub.count("aria-current") == 1
    assert not (ESTATICOS / "app.js").exists()
    js = leer("catalogo.js")
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js and "verOriginal" in js


# --- T11 · «Qué buscas» ---------------------------------------------------------------------------------
def test_que_buscas_es_un_panel_de_ofertas_con_guardar_y_buscar():
    html, js = leer("ofertas.html"), leer("ofertas.js")
    assert '<details id="que-buscas"' in html and "Guardar y buscar" in html
    for clave in ('id="solo-remoto"', 'id="solo-salario"', 'id="sueldo-minimo"', 'id="grupos"'):
        assert clave in html
    # abierto con las listas vacías o con #que-buscas; guardar hace el PUT y luego pide puntuar «buscar»
    assert 'location.hash === "#que-buscas"' in js and "GRUPOS.every" in js
    guardar = js[js.index('$("formulario-busca").addEventListener'):]
    assert guardar.index('"/api/preferencias"') < guardar.index('lanzarPuntuacion("buscar")')
    assert 'cuerpo: { motivo }' in js and '"PUT"' in js


# --- T12 · vista en el navegador ------------------------------------------------------------------------
def test_cambiar_la_vista_no_hace_ninguna_peticion_y_el_almacenamiento_va_con_try_catch():
    js = leer("ofertas.js")
    for nombre in ("function leerCamposVista", "function pintarVista", "function pintarLista", "function ordenar"):  # noqa: E501
        i = js.index(nombre)
        cuerpo = js[i:js.index("\n}\n", i)]
        assert "api(" not in cuerpo and "fetch(" not in cuerpo, nombre
    for nombre in ("function leerVista", "function guardarVista"):
        i = js.index(nombre)
        cuerpo = js[i:js.index("\n}\n", i)]
        assert "try {" in cuerpo and "catch" in cuerpo and "localStorage" in cuerpo, nombre
    assert 'VISTA_POR_DEFECTO = { min: 40, max: 100, orden: "recientes", estado: "nuevas" }' in js
    assert 'for (const id of ["nota-min", "nota-max", "orden", "estado"])' in js
    html = leer("ofertas.html")
    for texto in ("Compatibilidad mínima", "Compatibilidad máxima", "Ordenar por", "Mostrar"):
        assert texto in html
    assert "Nuevas" in js and "Con candidatura" in js and "Descartadas" in js


# --- T13 · candidatura y descartar ----------------------------------------------------------------------
def test_estado_de_candidatura_descartar_deshacer_y_recuperar():
    js = leer("ofertas.js")
    assert "Ver candidatura" in js and "Descartar" in js and "Deshacer" in js and "Recuperar" in js
    # con candidatura abierta no hay «Descartar» ni «Preparar candidatura»
    assert 'if (o.candidatura && o.candidatura.estado !== "cerrada") return null;' in js
    assert 'c && c.estado !== "cerrada"' in js
    assert "Oferta descartada. " in js and "/api/descartes/" in js
    assert "estadoVisible(o.candidatura.estado, o.candidatura.preparacion)" in js   # RF-10.7: un solo estado
    assert 'role="status"' in leer("ofertas.html")


# --- T14 · Ver oferta original --------------------------------------------------------------------------
def test_la_ventana_de_la_oferta_original_pinta_con_textcontent():
    js = leer("comun.js")
    bloque = js[js.index("function ventanaOriginal"):js.index("// Dibuja el Markdown del CV")]
    assert "innerHTML" not in bloque and "insertAdjacentHTML" not in bloque
    assert "textoBonito(o.texto)" in bloque and "showModal()" in bloque
    assert "Abrir en la web de origen" in bloque and "if (urlSegura(o.url))" in bloque
    assert 'a.rel = "noopener noreferrer"' in bloque and 'a.target = "_blank"' in bloque
    assert "disparador.focus()" in bloque  # el foco vuelve al botón al cerrar (Esc cierra el diálogo nativo)
    assert "No consta fecha de publicación" in bloque and "TEXTOS.anadidaPorTi" in bloque
    assert "innerHTML" not in js[js.index("function textoBonito"):js.index("async function verOriginal")]
    assert re.search(r"\.apartado-original\{[^}]*font-weight: 600", leer("estilo.css"))


def test_ver_oferta_original_esta_en_ofertas_candidatura_y_catalogo():
    for archivo in ("ofertas.js", "candidatura.js", "catalogo.js"):
        assert "verOriginal(" in leer(archivo), archivo
        assert "Ver oferta original" in leer(archivo), archivo


# --- T19 · pantallas con avance -------------------------------------------------------------------------
def test_ofertas_ya_no_tiene_boton_recomendar_ni_limite_de_sondeos():
    html, js = leer("ofertas.html"), leer("ofertas.js")
    assert 'id="recomendar"' not in html and ">Recomendar<" not in html
    assert "MAX_PUNTUANDO" not in js and "sondeos" not in js
    assert 'id="avance"' in html and "barraAvance($(\"avance\"), \"Calculando la compatibilidad de las ofertas\")" in js  # noqa: E501
    textos = leer("textos.js")   # RF-10.2e: los textos, en un solo archivo
    assert TEXTO_TOPE in textos
    assert "TEXTOS.presupuesto" in js and "sueltas" not in js


TEXTO_TOPE = "Hoy ya hemos trabajado todo lo posible para ti. Mañana seguimos."


def test_al_cargar_con_una_tarea_activa_la_barra_retoma_su_valor_y_al_terminar_desaparece():
    js = leer("ofertas.js")
    assert '"/api/tareas/activas?tipo=recomendar"' in js and "seguirPuntuacion(r.datos.tareas[0].id)" in js
    assert 'lanzarPuntuacion("abrir")' in js
    assert "barra.quitar()" in js and "barra.poner(p)" in js
    comun = leer("comun.js")
    assert "SONDEO_TAREA_MS = 3000" in comun and "function seguirTarea" in comun
    assert "t.estado === \"pendiente\" || t.estado === \"en_curso\"" in comun  # sin límite de sondeos
    assert "frasePorError" in js and "Lo ya calculado se conserva." in leer("textos.js")  # RF-8.7d


def test_anadir_oferta_y_candidatura_llevan_su_barra():
    assert "Analizando la oferta" in leer("ofertas.js") and 'id="lectura-url"' in leer("ofertas.html")
    cand = leer("candidatura.js")
    assert "Preparando tu CV y tu carta" in cand and "/api/tareas/activas?tipo=candidatura" in cand


def test_ningun_texto_nuevo_dice_match_ats_ni_trazabilidad():
    for archivo in ("ofertas.html", "ofertas.js", "catalogo.html", "catalogo.js", "index.html"):
        textos = re.findall(r'"([^"\n]{4,})"|>([^<>\n]{4,})<', leer(archivo))
        for a, b in textos:
            t = a or b
            if t.startswith(("/", "http")) or "${" in t and "/api/" in t:
                continue
            assert not PROHIBIDAS.search(t), (archivo, t)
