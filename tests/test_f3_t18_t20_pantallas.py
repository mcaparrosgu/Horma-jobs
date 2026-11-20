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
def test_cada_pagina_lleva_tokens_pestanas_y_sus_scripts(nombre):
    html = leer(f"{nombre}.html")
    assert "/static/tokens.css" in html                                     # fase 6: tokens 2c en vez del marco
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


# --- T19 y T31 · candidatura simplificada ------------------------------------------------------
def test_revisa_esto_une_huecos_y_avisos_cada_aviso_junto_a_su_frase():
    js = leer("candidatura.js")
    assert "Revisa esto" in js and "c.huecos" in js and "c.avisos" in js
    assert "a.frase" in js and "a.mensaje" in js and "a.documento" in js   # el aviso va con su frase
    assert js.count('"Revisa esto"') == 1 and "Avisos:" not in js        # una sola lista
    assert "`CV: " not in js and "`Carta: " not in js and "Carta, rasgo" not in js  # sin prefijos técnicos


def test_detalles_va_plegado_con_cv_base_motivo_y_porcentaje_ats():
    js = leer("candidatura.js")
    assert '"details"' in js and '"Detalles"' in js
    corte = js[js.index("function detalles"):js.index("// --- botones")]
    for pieza in ("cv_base", "cv_base_motivo", "cobertura_ats"):
        assert pieza in corte, pieza
    cabecera = js[js.index("function cabecera"):js.index("// --- «Revisa esto»")]
    assert "cv_base" not in cabecera and "cobertura_ats" not in cabecera   # fuera de la vista principal


def test_candidatura_muestra_los_documentos_y_el_historial_y_los_edita_sin_guardar_como_base():
    js = leer("candidatura.js")
    for pieza in ("cv_contenido", "carta_contenido", "eventos", "cvBonito"):
        assert pieza in js, pieza
    assert 'metodo: "PATCH"' in js
    for ya_no in ("Guardar como mi CV base", "guardar-cv-base", "cvEditado"):
        assert ya_no not in js, ya_no


def test_aprobar_y_descargar_no_tiene_casilla_ni_eleccion_de_cv():
    js = leer("candidatura.js")
    assert "Aprobar y descargar" in js and "/aprobar" in js
    for ya_no in ("He revisado los avisos", "avisos_revisados", "cv_estetico_id", "estetico", "checkbox",
                  "radio", "/api/cv"):
        assert ya_no not in js, ya_no
    assert "cv.pdf" in js and "carta.pdf" in js


def test_marcar_como_enviada_con_canal_opcional_y_sin_fecha():
    js = leer("candidatura.js")
    assert "Marcar como enviada" in js and "/enviada" in js and "Sin indicar" in js
    for canal in ("correo", "web", "linkedin", "otro"):
        assert f'"{canal}"' in js
    assert 'type = "date"' not in js and "fecha:" not in js              # la fecha es la de hoy


def test_dos_botones_de_respuesta_segun_el_estado_y_nada_de_pegar_el_correo():
    js = leer("candidatura.js")
    assert "Me han llamado" in js and "Me han rechazado" in js
    assert "/entrevista" in js and '{ motivo: "rechazo" }' in js
    assert 'c.estado === "enviada"' in js                      # «Me han llamado» solo desde enviada
    for ya_no in ("/respuesta", "clasificando", "respuesta_propuesta", "Analizar respuesta"):
        assert ya_no not in js, ya_no


def test_reintentar_solo_cuando_la_preparacion_fallo():
    js = leer("candidatura.js")
    assert "Reintentar" in js and "/reintentar" in js
    assert 'c.preparacion === "error"' in js and "motivo_error" in js


def test_los_botones_cambian_con_el_estado():
    js = leer("candidatura.js")
    for estado in ("borrador", "aprobada", "enviada", "entrevista", "cerrada"):
        assert f'"{estado}"' in js, estado
    for motivo in ("descartada", "retirada"):
        assert f'"{motivo}"' in js


def test_la_pantalla_espera_solo_mientras_se_prepara():
    js = leer("candidatura.js")
    assert "en_curso" in js and "setTimeout" in js


# --- T20 · recomendadas y CV base ---------------------------------------------------------------
def test_los_textos_de_recomendadas_y_cv_base_no_hablan_de_elegir_cv_ni_de_cv_estetico():
    for nombre in ("recomendadas", "cv-base"):
        js = leer(f"{nombre}.js")
        assert "estético" not in js and "guardas una candidatura" not in js
        assert "desde una candidatura" not in js
    assert "Horma elige tu CV base" in leer("recomendadas.js")


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
