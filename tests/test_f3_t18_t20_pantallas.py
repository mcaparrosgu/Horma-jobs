"""Fase 3 · T18-T20: tablero, pantalla de candidatura, botón «Preparar candidatura» e historial del CV base.

Las pantallas son HTML y JS estáticos; aquí se comprueba lo que se puede sin navegador: que solo se sirven
con sesión, que llevan el marco y las pestañas, que no pintan HTML y que cada función pedida está."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from horma import config
from horma.web.main import crear_app

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
PAGINAS = {"/candidaturas": "candidaturas", "/candidaturas/7": "candidatura"}
JS = ("comun", "candidaturas", "candidatura", "recomendadas", "cv-base")
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


def leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


@pytest.mark.bd
@pytest.mark.parametrize("ruta", PAGINAS)
def test_las_paginas_solo_se_sirven_con_sesion(app, ruta):
    anonima = TestClient(app, follow_redirects=False)
    r = anonima.get(ruta)
    assert r.status_code == 302 and r.headers["location"] == "/"
    c = TestClient(app, follow_redirects=False)
    assert c.get("/auth/google/callback?code=google-A").status_code == 302
    r = c.get(ruta)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "default-src 'self'" in r.headers["content-security-policy"]


@pytest.mark.parametrize("nombre", PAGINAS.values())
def test_cada_pagina_lleva_marco_pestanas_y_sus_scripts(nombre):
    html = leer(f"{nombre}.html")
    assert 'class="pp"' in html and 'aria-hidden="true"' in html
    assert 'id="pestanas"' in html
    assert "/static/comun.js" in html and f"/static/{nombre}.js" in html
    assert not re.search(r"<script(?![^>]*\bsrc=)", html)                  # CSP: sin scripts inline
    assert " style=" not in html and "onclick=" not in html


def test_el_js_pinta_solo_con_textcontent():
    for nombre in JS:
        js = leer(f"{nombre}.js")
        for malo in PROHIBIDO:
            assert malo not in js, f"{nombre}.js usa {malo}"


def test_hay_una_pestana_candidaturas():
    js = leer("comun.js")
    assert '"Candidaturas"' in js and '"/candidaturas"' in js


# --- T18 · tablero ------------------------------------------------------------------------------
def test_tablero_pide_la_api_y_pinta_las_columnas_con_cerradas_plegada():
    js = leer("candidaturas.js")
    assert "/api/candidaturas" in js
    assert "te_toca_revisar" in js and "Te toca revisar" in js
    assert "Cerradas" in js and '"details"' in js                           # «Cerradas» plegada
    assert "/candidaturas/" in js                                           # cada tarjeta lleva a su pantalla
    assert "preparando" in js.lower() or "en_curso" in js                   # la que aún se prepara se ve


def test_tablero_apila_las_columnas_en_movil():
    css = leer("estilo.css")
    assert ".tablero" in css
    movil = css[css.index("@media (max-width: 760px)"):]
    assert ".tablero" in movil


# --- T19 · candidatura --------------------------------------------------------------------------
def test_candidatura_muestra_cv_base_elegido_documentos_huecos_y_avisos():
    js = leer("candidatura.js")
    for pieza in ("cv_base_motivo", "cv_contenido", "carta_contenido", "huecos", "avisos", "eventos",
                  "cvBonito", "propuesta", "cobertura_ats"):
        assert pieza in js, pieza


def test_candidatura_edita_y_ofrece_guardar_como_cv_base_con_aviso_de_historial():
    js = leer("candidatura.js")
    assert 'metodo: "PATCH"' in js and "cv_contenido" in js
    assert "Guardar como mi CV base" in js and "/guardar-cv-base" in js
    assert "La versión anterior queda en el historial" in js


def test_aprobar_exige_la_casilla_si_hay_avisos_y_elige_documento():
    js = leer("candidatura.js")
    assert "He revisado los avisos" in js and "avisos_revisados" in js
    assert "/aprobar" in js and "documento" in js and "cv_estetico_id" in js and "/api/cv" in js
    assert ".disabled" in js                                                # el botón espera a la casilla


def test_los_botones_cambian_con_el_estado():
    js = leer("candidatura.js")
    for ruta in ("/enviada", "/entrevista", "/cerrar", "/respuesta", "/respuesta/confirmar",
                 "/respuesta/descartar", "cv.pdf", "carta.pdf"):
        assert ruta in js, ruta
    for estado in ("borrador", "aprobada", "enviada", "entrevista", "cerrada"):
        assert f'"{estado}"' in js, estado
    for canal in ("correo", "web", "linkedin", "otro"):
        assert f'"{canal}"' in js
    for motivo in ("rechazo", "descartada", "retirada"):
        assert f'"{motivo}"' in js


def test_la_pantalla_espera_mientras_se_prepara_o_se_clasifica():
    js = leer("candidatura.js")
    assert "en_curso" in js and "clasificando" in js and "setTimeout" in js


# --- T20 · recomendadas y CV base ---------------------------------------------------------------
def test_recomendadas_tiene_preparar_candidatura_que_no_pide_cv_base():
    js = leer("recomendadas.js")
    assert "Preparar candidatura" in js and "/api/candidaturas" in js and "oferta_id" in js
    assert "/cv-base" in js                                                 # sin CV base, enlaza a generarlo
    assert "location" in js                                                 # y lleva a la candidatura


def test_cv_base_tiene_historial_plegado_con_lineas_marcadas_y_volver():
    js = leer("cv-base.js")
    assert "Historial" in js and "/versiones" in js and "/restaurar" in js
    assert "Volver a esta versión" in js
    assert "añadida" in js and "quitada" in js
    css = leer("estilo.css")
    assert ".linea-anadida" in css and ".linea-quitada" in css
    assert "line-through" in css                                            # no solo el color
