"""Fase 9a · bloque E (pantallas): guía, «Qué buscas», Perfil y «Tu CV maestro» (T14-T17, spec 009).
Los estáticos leen los archivos; la parte de la API usa la base de pruebas."""
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
PROHIBIDAS = re.compile(r"\b(match|ATS|trazabilidad)\b", re.IGNORECASE)


def leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


# --- T14 · guía -----------------------------------------------------------------------------------------
def test_la_guia_recoge_los_dos_avisos_nuevos():
    spec = (RAIZ / "specs" / "006-rediseno-2c" / "spec.md").read_text(encoding="utf-8")
    assert "| **Aviso con dos acciones**" in spec and "| **Aviso con elección de longitud**" in spec


def test_los_avisos_existen_con_tokens_y_sin_colores_sueltos():
    css = leer("estilo.css")
    bloque = css[css.index("/* ── Fase 9a"):]
    for clase in (".aviso-accion", ".acciones-aviso", ".aviso-longitud", ".terminos",
                  ".con-editar"):
        assert clase in bloque, clase
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", bloque)
    assert "var(--tap)" in bloque and "var(--line)" in bloque


# --- T15 · «Qué buscas» ---------------------------------------------------------------------------------
def test_que_buscas_separa_puestos_y_terminos_excluidos_sin_area():
    html, js, comun = leer("ofertas.html"), leer("ofertas.js"), leer("comun.js")
    assert '["familias", "Área"]' not in comun and '["sectores", "Sector"]' in comun
    assert "nuevas.familias = []" in js   # el área ya no se elige: se vacía al guardar
    for id_ in ("casillas-puestos", "nuevo-puesto", "anadir-puesto", "lista-excluidos", "nuevo-excluido",
                "anadir-excluido"):
        assert f'id="{id_}"' in html, id_
    assert "Seleccionar todo" in js and "Quitar selección" in js
    assert "nuevas.puestos" in js and "nuevas.excluidos" in js
    assert "innerHTML" not in js


def test_ofertas_sin_palabras_prohibidas():
    assert not PROHIBIDAS.search(re.sub(r"<[^>]+>", " ", leer("ofertas.html")))


# --- T16 · Perfil: orden y avisos -----------------------------------------------------------------------
def test_perfil_muestra_los_bloques_en_el_orden_de_rf_9_5():
    html = leer("perfil.html")
    orden = [html.index(x) for x in ('id="mi-perfil"', 'id="maestro"', 'id="pendientes"',
                                     'id="cvs-subidos"', 'id="estilo"')]
    assert orden == sorted(orden)
    assert "Por resolver" in html and "Tu CV completo" in html


def test_perfil_avisos_con_sus_acciones_y_otras_actividades():
    js = leer("perfil.js")
    for texto in ("Añadir", "Corregir", "Dar por visto", "Mantener la longitud",
                  "Que Horma lo sintetice", "Otras actividades", "/api/perfil/avisos",
                  "/api/perfil/avisos/visto", "/api/perfil/longitud"):
        assert texto in js, texto
    assert "total && !pendientesPrevias" in js  # abierto al aparecer alguno
    assert "preguntas.length + items.length" in js  # el número suma preguntas y avisos


# --- T17 · Tu CV maestro --------------------------------------------------------------------------------
def test_cv_maestro_con_frase_fecha_version_editar_y_sin_innerhtml():
    html, js = leer("perfil.html"), leer("perfil.js")
    assert "Es el texto del que Horma saca tus CV y cartas. Se cambia desde tu perfil." in html
    assert "cvBonito(maestroActual)" in js and "Editar" in js and "Actualizado el ${fecha(creadoEn)}" in js
    assert "innerHTML" not in js and "contenteditable" not in html


def test_perfil_sin_palabras_prohibidas():
    assert not PROHIBIDAS.search(re.sub(r"<[^>]+>", " ", leer("perfil.html")))


# --- API: el CV maestro viene de perfiles.cv_maestro y solo lo ve su dueña ----------------------------


class IdentidadFalsa:
    async def redirigir(self, request, redirect_uri):
        from starlette.responses import RedirectResponse
        return RedirectResponse("https://accounts.google.test/auth")

    async def sub_desde_callback(self, request) -> str:
        return request.query_params["code"]


@pytest.fixture
def app(motor_app, bd_limpia):
    config.ajustes.cache_clear()
    yield crear_app(engine=motor_app, identidad=IdentidadFalsa())
    config.ajustes.cache_clear()


def entrar(app, sub):
    c = TestClient(app, follow_redirects=False)
    assert c.get(f"/auth/google/callback?code={sub}").status_code == 302
    return c


@pytest.mark.bd
def test_el_cv_maestro_coincide_con_el_guardado_y_otra_usuaria_no_lo_ve(app, motor_app, motor_migrador):
    a, b = entrar(app, "google-A"), entrar(app, "google-B")
    with motor_migrador.connect() as c:
        u = c.execute(text("select id from usuarias where google_sub='google-A'")).scalar_one()
    with sesion_de(motor_app, u) as s:
        pid, version = perfiles.nueva_version(s, u)
        perfiles.guardar_perfil(s, u, pid, Perfil.model_validate({"version": version, "nombre": "Ana"}),
                                "# Ana\n## Experiencia\nCamarera · Bar Sol\n")
        guardado = s.execute(text("select cv_maestro from perfiles")).scalar_one()
    r = a.get("/api/perfil").json()
    assert r["cv_maestro"] == guardado and r["creado_en"]
    assert b.get("/api/perfil").json()["perfil"] is None
