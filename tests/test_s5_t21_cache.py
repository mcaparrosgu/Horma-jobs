"""Simplificación S5 · T21: caché de la compatibilidad por huella del perfil y `clasificar_perfil` solo si
hace falta (RF-10.10c, RF-10.10d, migración 0022). Ninguna prueba llama al modelo real."""
import importlib

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from horma import config
from horma.schemas.perfil import Perfil
from horma.tools.huella_perfil import huella_clasificacion, huella_compatibilidad
from horma.web.db import sesion_de
from horma.web.main import crear_app
from horma.web.repositories import matches, perfiles
from tests.conftest import RAIZ

TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior", "stack": []}
ORIGEN = {"fuente": "cv", "cv_id": 1, "fragmento": "Camarera en Bar Sol, 2020-2023"}


def _perfil(**cambios) -> Perfil:
    base = {"taxonomia": TAX, "titular": {"valor": "Camarera", "origen": ORIGEN},
            "resumen": {"valor": "Camarera con experiencia.", "origen": ORIGEN},
            "experiencias": [{"puesto": "Camarera", "empresa": "Bar Sol", "origen": ORIGEN}],
            "idiomas": [{"idioma": "es", "nivel": "nativo", "origen": ORIGEN}]}
    return Perfil.model_validate({**base, **cambios})


# --- huellas (código puro) ------------------------------------------------------------------------
def test_editar_el_resumen_no_cambia_ninguna_huella():
    a = _perfil()
    b = _perfil(resumen={"valor": "Camarera con 3 años de experiencia.", "origen": ORIGEN})
    assert huella_compatibilidad(a) == huella_compatibilidad(b)
    assert huella_clasificacion(a) == huella_clasificacion(b)


def test_editar_una_experiencia_cambia_las_dos_huellas():
    a = _perfil()
    b = _perfil(experiencias=[{"puesto": "Camarera", "empresa": "Bar Luna", "origen": ORIGEN}])
    assert huella_compatibilidad(a) != huella_compatibilidad(b)
    assert huella_clasificacion(a) != huella_clasificacion(b)


def test_un_idioma_cambia_la_compatibilidad_pero_no_la_clasificacion():
    a = _perfil()
    b = _perfil(idiomas=[{"idioma": "es", "nivel": "nativo", "origen": ORIGEN},
                         {"idioma": "en", "nivel": "B2", "origen": ORIGEN}])
    assert huella_compatibilidad(a) != huella_compatibilidad(b)
    assert huella_clasificacion(a) == huella_clasificacion(b)


def test_el_origen_no_cuenta():
    otro = {"fuente": "usuaria", "fragmento": "Camarera en Bar Sol"}
    a = _perfil()
    b = _perfil(experiencias=[{"puesto": "Camarera", "empresa": "Bar Sol", "origen": otro}])
    assert huella_compatibilidad(a) == huella_compatibilidad(b)


# --- migración ------------------------------------------------------------------------------------
def test_la_migracion_0022_encadena_con_la_0021():
    m = importlib.import_module("horma.web.migrations.versions.0022_simplificacion")
    assert (m.revision, m.down_revision) == ("0022", "0021")


class IdentidadFalsa:
    async def redirigir(self, request, redirect_uri):
        from starlette.responses import RedirectResponse
        return RedirectResponse("https://accounts.google.test/auth")

    async def sub_desde_callback(self, request) -> str:
        return request.query_params["code"]


@pytest.fixture
def app(motor_app, bd_limpia, monkeypatch):
    config.ajustes.cache_clear()
    yield crear_app(engine=motor_app, identidad=IdentidadFalsa())
    config.ajustes.cache_clear()


def entrar(app, sub="google-A"):
    c = TestClient(app, follow_redirects=False)
    assert c.get(f"/auth/google/callback?code={sub}").status_code == 302
    return c, {"X-CSRF-Token": c.get("/api/yo").json()["csrf"]}


def usuaria(motor_migrador, sub="google-A"):
    with motor_migrador.connect() as s:
        return s.execute(text("select id from usuarias where google_sub=:s"), {"s": sub}).scalar_one()


def perfil_hecho(motor, u, perfil: Perfil | None = None):
    perfil = perfil or _perfil()
    with sesion_de(motor, u) as s:
        pid, version = perfiles.nueva_version(s, u)
        perfiles.guardar_perfil(s, u, pid, perfil.model_copy(update={"version": version}), "# Ana")
    return pid, version


def oferta(motor_migrador, titulo="Camarera"):
    with motor_migrador.begin() as c:
        return c.execute(text(
            "insert into ofertas (texto_crudo, huella, titulo, empresa, estado, fantasma, fraude, sector, "
            "familia) values (:t, md5(:t || random()::text), :t, 'Hotel Mar', 'procesada', false, false, "
            "'hosteleria_turismo', 'hosteleria_restauracion') returning id"), {"t": titulo}).scalar_one()


def match(o, nota=80):
    return {"oferta_id": o, "nota": nota, "condiciones": "medio", "explicacion": "Una frase. Dos frases.",
            "cita_perfil": "Camarera en Bar Sol", "cita_oferta": "camarera", "retirada": False}


def tareas(motor_migrador, tipo):
    with motor_migrador.connect() as c:
        return c.execute(text("select count(*) from tareas where tipo = :t"), {"t": tipo}).scalar_one()


@pytest.mark.bd
def test_el_relleno_da_huella_a_las_notas_que_ya_habia(bd_migrada, motor_app, motor_migrador, bd_limpia):
    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", bd_migrada[1])
    with motor_migrador.begin() as c:
        u = c.execute(text("insert into usuarias (google_sub) values ('a') returning id")).scalar_one()
    perfil_hecho(motor_app, u)
    o = oferta(motor_migrador)
    command.downgrade(cfg, "0021")
    with motor_migrador.begin() as c:
        c.execute(text("insert into matches (usuaria_id, oferta_id, perfil_version, nota, condiciones) "
                       "values (:u, :o, 1, 80, 'medio')"), {"u": u, "o": o})
    command.upgrade(cfg, "head")
    with motor_migrador.connect() as c:
        h = c.execute(text("select huella_perfil from matches")).scalar_one()
    assert h == huella_compatibilidad(_perfil())


# --- servicios ------------------------------------------------------------------------------------
@pytest.mark.bd
def test_editar_el_resumen_no_clasifica_ni_vuelve_a_puntuar(app, motor_app, motor_migrador):
    c, h = entrar(app)
    u = usuaria(motor_migrador)
    perfil_hecho(motor_app, u)
    o = oferta(motor_migrador)
    with sesion_de(motor_app, u) as s:
        huella = huella_compatibilidad(_perfil())
        matches.guardar(s, u, 1, [match(o)], huella)
    r = c.patch("/api/perfil/datos", headers=h, json={
        "campo": "resumen", "dato": {"valor": "Camarera con 3 años de experiencia."}})
    assert r.status_code == 201 and r.json()["version"] == 2
    assert tareas(motor_migrador, "clasificar_perfil") == 0
    with sesion_de(motor_app, u) as s:
        v2 = perfiles.perfil_modelo(perfiles.vigente(s))
        assert huella_compatibilidad(v2) == huella
        assert matches.puntuadas(s, huella_compatibilidad(v2)) == [o]  # no hay nada que puntuar
        assert matches.listado(s, [o], huella)[0]["desfasado"] is False
    # y «Recomendar» no lanza nada: todo está puntuado con esta huella
    r = c.post("/api/recomendar", headers=h, json={"motivo": "buscar"})
    assert r.json()["motivo"] == "sin_pendientes"


@pytest.mark.bd
def test_editar_una_experiencia_clasifica_y_deja_la_nota_desfasada(app, motor_app, motor_migrador):
    c, h = entrar(app)
    u = usuaria(motor_migrador)
    perfil_hecho(motor_app, u)
    o = oferta(motor_migrador)
    with sesion_de(motor_app, u) as s:
        matches.guardar(s, u, 1, [match(o)], huella_compatibilidad(_perfil()))
    r = c.patch("/api/perfil/datos", headers=h, json={
        "campo": "experiencias", "indice": 0, "dato": {"puesto": "Camarera", "empresa": "Bar Luna"}})
    assert r.status_code == 201
    assert tareas(motor_migrador, "clasificar_perfil") == 1
    with sesion_de(motor_app, u) as s:
        nueva = huella_compatibilidad(perfiles.perfil_modelo(perfiles.vigente(s)))
        assert matches.puntuadas(s, nueva) == []
        assert matches.listado(s, [o], nueva)[0]["desfasado"] is True


def test_precios_oficiales_con_fecha_de_consulta():
    fuente = (RAIZ / "horma" / "config.py").read_text(encoding="utf-8")
    assert "ESTIMADOS" not in fuente and "consultada el" in fuente and "2026" in fuente
    a = config.Ajustes()
    assert a.precio_pequeno == (0.10, 0.50) and a.precio_mayor == (2.0, 10.0)
