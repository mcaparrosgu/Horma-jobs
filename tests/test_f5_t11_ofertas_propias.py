"""Fase 5 · T11: una oferta añadida por una usuaria es suya y solo suya (RF-5.3c), garantizado por RLS."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from horma import config
from horma.llm.simulado import ProveedorSimulado
from horma.web.db import sesion_de, sesion_sistema
from horma.web.main import crear_app
from horma.web.queue import worker
from horma.web.repositories import ofertas as repo

pytestmark = pytest.mark.bd

TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior",
       "stack": []}
AUDITOR = {"generica": False, "fraude": False}
TEXTO = "Camarera de sala en Hotel Mar, Valencia. Publicada: 2026-11-01"
EXTRACCION = {"titulo": "Camarera de sala", "empresa": "Hotel Mar", "fecha_publicacion": "2026-11-01"}


class IdentidadFalsa:
    async def redirigir(self, request, redirect_uri):
        from starlette.responses import RedirectResponse
        return RedirectResponse("https://accounts.google.test/auth")

    async def sub_desde_callback(self, request) -> str:
        return request.query_params["code"]


@pytest.fixture
def app(motor_app, bd_limpia, tmp_path, monkeypatch):
    monkeypatch.setenv("RUTA_ARCHIVOS", str(tmp_path / "archivos"))
    monkeypatch.setenv("HORMA_ADMINS", "google-A,google-B")  # el catálogo común es solo de Admin (RF-8.2c)
    config.ajustes.cache_clear()
    yield crear_app(engine=motor_app, identidad=IdentidadFalsa())
    config.ajustes.cache_clear()


def _entrar(app, sub):
    c = TestClient(app, follow_redirects=False)
    assert c.get(f"/auth/google/callback?code={sub}").status_code == 302
    yo = c.get("/api/yo").json()
    return c, {"X-CSRF-Token": yo["csrf"]}


def _pegar(c, h, motor, texto=TEXTO):
    oid = c.post("/ofertas", headers=h, json={"texto": texto}).json()["id"]
    prov = ProveedorSimulado([EXTRACCION, AUDITOR, TAX])
    while worker.procesar_una(motor, prov, resolver=None):  # también las tareas que deja encoladas
        pass
    return oid


def _del_catalogo(motor, texto=TEXTO):
    with sesion_sistema(motor) as s:
        oid, _, _ = repo.crear(s, texto)
    return oid


def _usuaria(motor_migrador, sub):
    with motor_migrador.connect() as s:
        return s.execute(text("select id from usuarias where google_sub=:s"), {"s": sub}).scalar_one()


def test_la_oferta_de_ana_no_la_ve_berta_en_ningun_sitio(app, motor_app, motor_migrador):
    ana, ha = _entrar(app, "google-A")
    berta, _ = _entrar(app, "google-B")
    propia = _pegar(ana, ha, motor_app)
    catalogo = _del_catalogo(motor_app, "Otra oferta del catálogo")
    assert propia in {o["id"] for o in ana.get("/ofertas").json()}
    ids_de_berta = {o["id"] for o in berta.get("/ofertas").json()}
    assert propia not in ids_de_berta and catalogo in ids_de_berta           # /ofertas
    assert propia not in {o["id"] for o in berta.get("/api/recomendaciones").json()["recomendaciones"]}
    with sesion_de(motor_app, _usuaria(motor_migrador, "google-B")) as s:     # por id, en la base
        assert s.execute(text("select count(*) from ofertas where id=:i"), {"i": propia}).scalar_one() == 0
        assert repo.completas(s, [propia]) == {}
        assert s.execute(text("select count(*) from ofertas where id=:i"), {"i": catalogo}).scalar_one() == 1
    with sesion_de(motor_app, _usuaria(motor_migrador, "google-A")) as s:
        assert s.execute(text("select count(*) from ofertas where id=:i"), {"i": propia}).scalar_one() == 1


def test_el_catalogo_comun_lo_ven_las_dos(app, motor_app):
    ana, _ = _entrar(app, "google-A")
    berta, _ = _entrar(app, "google-B")
    oid = _del_catalogo(motor_app)
    assert oid in {o["id"] for o in ana.get("/ofertas").json()}
    assert oid in {o["id"] for o in berta.get("/ofertas").json()}


def test_dos_usuarias_con_la_misma_oferta_tienen_cada_una_la_suya_y_ninguna_es_fantasma(
        app, motor_app):
    ana, ha = _entrar(app, "google-A")
    berta, hb = _entrar(app, "google-B")
    del_catalogo = _del_catalogo(motor_app)  # el mismo texto ya estaba en el catálogo
    de_ana = _pegar(ana, ha, motor_app)
    de_berta = _pegar(berta, hb, motor_app)
    assert len({del_catalogo, de_ana, de_berta}) == 3
    with sesion_sistema(motor_app) as s:
        filas = s.execute(text(
            "select id, usuaria_id, fantasma, recomendable from ofertas where id = any(:i)"),
            {"i": [de_ana, de_berta]}).all()
        assert all(not f.fantasma and f.recomendable and f.usuaria_id for f in filas)
        assert repo.para_procesar(s, de_berta)["repetida"] is False


def test_pegar_dos_veces_la_misma_no_la_duplica_ni_la_vuelve_a_procesar(app, motor_app):
    ana, ha = _entrar(app, "google-A")
    primera = _pegar(ana, ha, motor_app)
    segunda = _pegar(ana, ha, motor_app)
    assert segunda == primera
    with sesion_sistema(motor_app) as s:
        assert s.execute(text("select count(*) from ofertas where usuaria_id is not null")).scalar_one() == 1
