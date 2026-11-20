"""Fase 8 · bloque B: datos y API (T03-T06, spec 008)."""
import importlib
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from horma import config
from horma.web.db import sesion_de
from horma.web.main import crear_app
from horma.web.repositories import tareas

pytestmark = pytest.mark.bd

ADMIN = "google-admin"


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
    return c, {"X-CSRF-Token": c.get("/api/yo").json()["csrf"]}


def usuaria(motor_migrador, sub):
    with motor_migrador.connect() as c:
        return c.execute(text("select id from usuarias where google_sub=:s"), {"s": sub}).scalar_one()


def oferta(motor_migrador, titulo="Camarera", duena=None, url=None, texto="Texto completo de la oferta"):
    with motor_migrador.begin() as c:
        return c.execute(text(
            "insert into ofertas (texto_crudo, huella, titulo, empresa, estado, usuaria_id, url, fantasma, fraude) "  # noqa: E501
            "values (:t, md5(:t || :ti || random()::text), :ti, 'Hotel Mar', 'procesada', :d, :u, false, false) "  # noqa: E501
            "returning id"), {"t": texto, "ti": titulo, "d": duena, "u": url}).scalar_one()


def tarea(motor_migrador, u, tipo="recomendar", entidad=1, coste=0, creada=None, estado="pendiente"):
    with motor_migrador.begin() as c:
        return c.execute(text(
            "insert into tareas (usuaria_id, tipo, entidad_id, tope_coste, coste_acumulado, estado, creada_en) "  # noqa: E501
            "values (:u, :t, :e, 1, :c, :s, coalesce(cast(:f as timestamptz), now())) returning id"),
            {"u": u, "t": tipo, "e": entidad, "c": coste, "f": creada, "s": estado}).scalar_one()


# --- T03 · migración 0020 -----------------------------------------------------------------------------
def test_la_migracion_0020_encadena_con_la_0019():
    m = importlib.import_module("horma.web.migrations.versions.0020_fase8_descartes_progreso")
    assert (m.revision, m.down_revision) == ("0020", "0019")


def test_progreso_tiene_su_check_y_actualizada_en(app, motor_migrador):
    entrar(app)
    u = usuaria(motor_migrador, "google-A")
    t = tarea(motor_migrador, u)
    with motor_migrador.begin() as c:
        fila = c.execute(text("select progreso, actualizada_en is not null from tareas where id=:i"),
                         {"i": t}).one()
        assert tuple(fila) == (0, True)
        with pytest.raises(Exception, match="progreso"):
            with c.begin_nested():
                c.execute(text("update tareas set progreso = 101 where id=:i"), {"i": t})
        with pytest.raises(Exception, match="progreso"):
            with c.begin_nested():
                c.execute(text("update tareas set progreso = -1 where id=:i"), {"i": t})


def test_existe_el_indice_de_tareas(motor_migrador, app):
    with motor_migrador.connect() as c:
        defn = c.execute(text("select indexdef from pg_indexes where tablename='tareas' "
                              "and indexname='tareas_usuaria_tipo_idx'")).scalar_one()
    assert "usuaria_id, tipo, creada_en" in defn


def test_una_usuaria_no_lee_ni_borra_los_descartes_de_otra(app, motor_app, motor_migrador):
    entrar(app, "google-A")
    entrar(app, "google-B")
    a, b = usuaria(motor_migrador, "google-A"), usuaria(motor_migrador, "google-B")
    o = oferta(motor_migrador)
    with sesion_de(motor_app, a) as s:
        s.execute(text("insert into descartes (usuaria_id, oferta_id) values (:u, :o)"), {"u": a, "o": o})
    with sesion_de(motor_app, b) as s:
        assert s.execute(text("select count(*) from descartes")).scalar_one() == 0
        assert s.execute(text("delete from descartes where oferta_id=:o"), {"o": o}).rowcount == 0
    with pytest.raises(Exception):  # no se puede descartar a nombre de otra  # noqa: B017
        with sesion_de(motor_app, b) as s:
            s.execute(text("insert into descartes (usuaria_id, oferta_id) values (:u, :o)"), {"u": a, "o": o})
    with sesion_de(motor_app, a) as s:
        assert s.execute(text("select count(*) from descartes")).scalar_one() == 1


# --- T04 · repositorio y API de tareas ----------------------------------------------------------------
def test_el_progreso_nunca_baja(app, motor_app, motor_migrador):
    entrar(app)
    u = usuaria(motor_migrador, "google-A")
    t = tarea(motor_migrador, u)
    with sesion_de(motor_app, u) as s:
        tareas.avanzar(s, t, 40)
        tareas.avanzar(s, t, 10)
        assert tareas.una(s, t)["progreso"] == 40
        tareas.avanzar(s, t, 250)
        assert tareas.una(s, t)["progreso"] == 100


def test_el_dia_se_corta_a_medianoche_de_madrid(app, motor_app, motor_migrador):
    entrar(app)
    u = usuaria(motor_migrador, "google-A")
    with motor_migrador.connect() as c:
        inicio = c.execute(text("select (date_trunc('day', now() at time zone 'Europe/Madrid')) "
                                "at time zone 'Europe/Madrid'")).scalar_one()
    tarea(motor_migrador, u, entidad=1, coste=0.10, creada=inicio)  # justo a medianoche: hoy
    tarea(motor_migrador, u, entidad=2, coste=0.30, creada=inicio - timedelta(seconds=1))  # ayer
    tarea(motor_migrador, u, tipo="perfilar", coste=9)  # otro tipo: no cuenta
    tarea(motor_migrador, u, tipo="puntuar_una", entidad=5, coste=0.02)
    with sesion_de(motor_app, u) as s:
        assert tareas.gasto_hoy(s, u) == pytest.approx(0.12)
        assert tareas.sueltas_hoy(s, u) == 1
        assert tareas.ultima(s, u, "perfilar")["estado"] == "pendiente"
        assert tareas.ultima(s, u, "inexistente") is None


def test_activas_y_tarea_por_id_solo_las_propias(app, motor_migrador):
    ana, _ = entrar(app, "google-A")
    berta, _ = entrar(app, "google-B")
    a, b = usuaria(motor_migrador, "google-A"), usuaria(motor_migrador, "google-B")
    t_ana = tarea(motor_migrador, a, estado="en_curso")
    tarea(motor_migrador, a, tipo="perfilar", estado="hecha")
    t_berta = tarea(motor_migrador, b)
    with motor_migrador.begin() as c:
        c.execute(text("update tareas set progreso = 55 where id=:i"), {"i": t_ana})
    r = ana.get("/api/tareas/activas").json()["tareas"]
    assert [x["id"] for x in r] == [t_ana] and r[0]["progreso"] == 55 and r[0]["estado"] == "en_curso"
    assert ana.get("/api/tareas/activas?tipo=perfilar").json() == {"tareas": []}
    assert [x["id"] for x in ana.get("/api/tareas/activas?tipo=recomendar").json()["tareas"]] == [t_ana]
    assert ana.get(f"/api/tareas/{t_ana}").json()["progreso"] == 55
    assert ana.get(f"/api/tareas/{t_berta}").status_code == 404  # RLS
    assert [x["id"] for x in berta.get("/api/tareas/activas").json()["tareas"]] == [t_berta]
    assert TestClient(app).get("/api/tareas/activas").status_code == 401


# --- T05 · ofertas: catálogo solo Admin, propias aparte y original -------------------------------------
def test_el_catalogo_solo_lo_ve_una_administradora(app, motor_migrador):
    ana, _ = entrar(app, "google-A")
    admin, _ = entrar(app, ADMIN)
    oferta(motor_migrador)
    assert ana.get("/ofertas").status_code == 403
    assert ana.get("/ofertas/total").status_code == 403
    assert len(admin.get("/ofertas").json()) == 1
    assert admin.get("/ofertas/total").json()["total"] == 1


def test_propias_solo_las_suyas_y_con_avance(app, motor_migrador):
    ana, _ = entrar(app, "google-A")
    berta, _ = entrar(app, "google-B")
    a, b = usuaria(motor_migrador, "google-A"), usuaria(motor_migrador, "google-B")
    mia = oferta(motor_migrador, "Mía", duena=a)
    oferta(motor_migrador, "De Berta", duena=b)
    oferta(motor_migrador, "Del catálogo")
    with motor_migrador.begin() as c:
        c.execute(text("insert into tareas (usuaria_id, tipo, entidad_id, tope_coste, progreso, estado) "
                       "values (null, 'procesar_oferta', :o, 1, 60, 'en_curso')"), {"o": mia})
    r = ana.get("/api/ofertas/propias").json()
    assert [o["titulo"] for o in r] == ["Mía"] and r[0]["progreso"] == 60
    assert [o["titulo"] for o in berta.get("/api/ofertas/propias").json()] == ["De Berta"]


def test_original_con_el_texto_completo_y_url_solo_http(app, motor_migrador):
    ana, _ = entrar(app, "google-A")
    berta, _ = entrar(app, "google-B")
    a = usuaria(motor_migrador, "google-A")
    larga = "Línea 1\nLínea 2 <b>no</b> " + "x" * 3000
    ok = oferta(motor_migrador, "Con web", url="https://empresa.test/oferta", texto=larga)
    mala = oferta(motor_migrador, "Mala", url="javascript:alert(1)")
    ajena = oferta(motor_migrador, "Ajena", duena=a)
    r = ana.get(f"/api/ofertas/{ok}/original").json()
    assert r["texto"] == larga and r["url"] == "https://empresa.test/oferta" and r["propia"] is False
    assert r["titulo"] == "Con web" and r["empresa"] == "Hotel Mar"
    assert ana.get(f"/api/ofertas/{mala}/original").json()["url"] is None
    assert ana.get(f"/api/ofertas/{ajena}/original").json()["propia"] is True
    assert berta.get(f"/api/ofertas/{ajena}/original").status_code == 404
    assert ana.get("/api/ofertas/9999/original").status_code == 404


# --- T06 · descartes y estado de candidatura en el listado ---------------------------------------------
def candidatura(motor_migrador, u, o, estado="borrador", motivo=None):
    with motor_migrador.begin() as c:
        return c.execute(text("insert into candidaturas (usuaria_id, oferta_id, estado, motivo_cierre) "
                              "values (:u, :o, :e, :m) returning id"),
                         {"u": u, "o": o, "e": estado, "m": motivo}).scalar_one()


def por_id(cliente):
    return {r["id"]: r for r in cliente.get("/api/recomendaciones").json()["recomendaciones"]}


def test_descartar_y_recuperar(app, motor_migrador):
    ana, h = entrar(app)
    o = oferta(motor_migrador)
    assert ana.put(f"/api/descartes/{o}", headers=h).status_code == 200
    assert ana.put(f"/api/descartes/{o}", headers=h).status_code == 200  # idempotente
    assert por_id(ana)[o]["descartada"] is True
    assert ana.delete(f"/api/descartes/{o}", headers=h).status_code == 200
    assert por_id(ana)[o]["descartada"] is False
    assert ana.put("/api/descartes/9999", headers=h).status_code == 404
    assert ana.put(f"/api/descartes/{o}").status_code == 403  # sin CSRF


def test_no_se_descarta_con_candidatura_abierta(app, motor_migrador):
    ana, h = entrar(app)
    u = usuaria(motor_migrador, "google-A")
    o = oferta(motor_migrador)
    candidatura(motor_migrador, u, o)
    assert ana.put(f"/api/descartes/{o}", headers=h).status_code == 409
    with motor_migrador.begin() as c:
        c.execute(text("update candidaturas set estado='cerrada', motivo_cierre='retirada'"))
    assert ana.put(f"/api/descartes/{o}", headers=h).status_code == 200


def test_el_listado_trae_la_candidatura_abierta_o_la_ultima_cerrada(app, motor_migrador):
    ana, _ = entrar(app)
    u = usuaria(motor_migrador, "google-A")
    sin, abierta, cerrada, ambas = (oferta(motor_migrador, t) for t in ("sin", "abierta", "cerrada", "ambas"))
    ca = candidatura(motor_migrador, u, abierta, "enviada")
    candidatura(motor_migrador, u, cerrada, "cerrada", "rechazo")
    candidatura(motor_migrador, u, ambas, "cerrada", "retirada")
    viva = candidatura(motor_migrador, u, ambas, "borrador")
    r = por_id(ana)
    assert r[sin]["candidatura"] is None
    assert r[abierta]["candidatura"] == {"id": ca, "estado": "enviada", "motivo_cierre": None}
    assert r[cerrada]["candidatura"]["estado"] == "cerrada"
    assert r[cerrada]["candidatura"]["motivo_cierre"] == "rechazo"
    assert r[ambas]["candidatura"]["id"] == viva  # la abierta gana a la cerrada


def test_recomendaciones_ya_no_aplica_rango_ni_orden(app, motor_migrador):
    ana, _ = entrar(app)
    u = usuaria(motor_migrador, "google-A")
    o1, o2 = oferta(motor_migrador, "baja"), oferta(motor_migrador, "alta")
    with motor_migrador.begin() as c:
        for o, n in ((o1, 10), (o2, 95)):
            c.execute(text("insert into matches (usuaria_id, oferta_id, perfil_version, nota, condiciones) "
                           "values (:u, :o, 1, :n, 'alto')"), {"u": u, "o": o, "n": n})
    r = ana.get("/api/recomendaciones?rango=50-100&orden=compatibles").json()
    assert {x["id"] for x in r["recomendaciones"]} == {o1, o2} and "rango" not in r
