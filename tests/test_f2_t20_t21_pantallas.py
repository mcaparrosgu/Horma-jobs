"""Fase 2 · T20-T21: pantallas de perfil, preferencias, CV base y ofertas recomendadas."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from horma import config
from horma.web.main import crear_app

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
PAGINAS = {"/perfil": "perfil", "/preferencias": "preferencias", "/cv-base": "cv-base",
           "/recomendadas": "recomendadas", "/anadir-oferta": "anadir-oferta"}
PROHIBIDO = ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function")


class IdentidadFalsa:
    async def redirigir(self, request, redirect_uri):
        from starlette.responses import RedirectResponse
        return RedirectResponse("https://accounts.google.test/auth")

    async def sub_desde_callback(self, request) -> str:
        return request.query_params["code"]


@pytest.fixture
def app(motor_app, bd_limpia, tmp_path, monkeypatch):
    monkeypatch.setenv("RUTA_ARCHIVOS", str(tmp_path / "archivos"))
    config.ajustes.cache_clear()
    yield crear_app(engine=motor_app, identidad=IdentidadFalsa())
    config.ajustes.cache_clear()


def entrar(app, sub="google-A"):
    c = TestClient(app, follow_redirects=False)
    assert c.get(f"/auth/google/callback?code={sub}").status_code == 302
    return c, {"X-CSRF-Token": c.get("/api/yo").json()["csrf"]}


def leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


@pytest.mark.bd
@pytest.mark.parametrize("ruta", PAGINAS)
def test_las_paginas_solo_se_sirven_con_sesion(app, ruta):
    anonima = TestClient(app, follow_redirects=False)
    r = anonima.get(ruta)
    assert r.status_code == 302 and r.headers["location"] == "/"
    c, _ = entrar(app)
    r = c.get(ruta)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "default-src 'self'" in r.headers["content-security-policy"]


@pytest.mark.parametrize("ruta,nombre", PAGINAS.items())
def test_cada_pagina_lleva_tokens_pestanas_y_sus_propios_scripts(ruta, nombre):
    html = leer(f"{nombre}.html")
    assert "/static/tokens.css" in html                                     # fase 6: tokens 2c en vez del marco
    assert 'id="pestanas"' in html                                          # pestañas comunes
    assert "/static/comun.js" in html and f"/static/{nombre}.js" in html
    assert not re.search(r"<script(?![^>]*\bsrc=)", html)                  # CSP: sin scripts inline
    assert " style=" not in html and "onclick=" not in html


def test_las_pestanas_son_las_cuatro_de_la_maqueta():
    js = leer("comun.js")
    for etiqueta, ruta in (("Perfil", "/perfil"), ("Preferencias", "/preferencias"),
                           ("CV base", "/cv-base"), ("Añadir oferta", "/anadir-oferta"),
                           ("Recomendadas", "/recomendadas")):
        assert f'"{etiqueta}"' in js and f'"{ruta}"' in js


def test_el_js_de_las_pantallas_pinta_solo_con_textcontent():
    for nombre in ("comun", "perfil", "preferencias", "cv-base", "recomendadas", "anadir-oferta"):
        js = leer(f"{nombre}.js")
        for malo in PROHIBIDO:
            assert malo not in js, f"{nombre}.js usa {malo}"


def test_preferencias_son_casillas_con_contador_y_un_campo_numerico_de_sueldo():
    js, html = leer("preferencias.js"), leer("preferencias.html")
    assert '"checkbox"' in leer("comun.js") and "grupoCasillas" in js
    assert "/api/preferencias/opciones" in js
    assert 'type="number"' in html and 'id="sueldo-minimo"' in html and "sueldo_minimo" in js
    assert "solo_remoto" in js and "solo_salario" in js
    assert "PUT" in js


def test_perfil_enseña_origen_pendientes_y_la_gestion_de_cv():
    js = leer("perfil.js")
    assert "origen" in js and "preguntas_pendientes" in js
    assert "/api/perfil/respuestas" in js and "/api/perfil/datos" in js
    assert "/api/cv" in js and "PATCH" in js and "/archivo" in js        # renombrar y descargar
    assert "FormData" in js                                               # subir un CV
    assert "/ver" in js and "iframe" in js and '"Ver"' in js              # ver el CV sin descargarlo
    assert 'id="visor"' in leer("perfil.html")


def test_cv_base_se_genera_a_peticion_y_se_renombra():
    js = leer("cv-base.js")
    assert "/api/cv-base" in js and "POST" in js and "PATCH" in js
    assert "desfasado" in js and "avisos" in js


def test_recomendadas_sigue_la_maqueta():
    html, js = leer("recomendadas.html"), leer("recomendadas.js")
    assert "Cómo leer las recomendaciones" in html and "<details" in html   # bloque plegable
    assert 'id="contador"' in html and 'id="filtros"' in html               # contador y barra
    for columna in ("Oferta", "Puesto", "Compatibilidad", "Salario", "Lugar", "Publicado"):
        assert f'"{columna}"' in js
    assert js.count('"?"') >= 1 and "AYUDA" in js                            # «?» que explica cada columna
    assert "/api/recomendaciones" in js and "/api/recomendar" in js
    assert "Modificar" in js and "/correccion" in js and "explicacion" in js
    assert "sin_puntuar" in js and "o.salario" in js                          # salario: texto de la oferta
    assert 'value="recientes"' in html and 'value="compatibles"' in html     # ordenación
    assert "rango" in js
    assert '"Condiciones"' not in js and "cond-" not in js                    # fase 5, RF-5.2: sin columna
    assert "Añadida por ti · analizada el" in js and "aviso_auditor" in js    # fase 5, RF-5.3e


def test_en_movil_las_filas_pasan_a_tarjetas():
    css = leer("estilo.css")
    assert re.search(r"@media \(max-width: \d+px\)\s*\{[^@]*\.tabla-ofertas", css, re.S)
    assert "data-etiqueta" in css or "attr(data-" in css                     # cada celda lleva su rótulo
