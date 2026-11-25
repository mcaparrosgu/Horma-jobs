"""Fase 5 · T30: Himalayas, Jobicy, Remotive y Adzuna por configuración (RF-5.5, RF-5.5d).
Respuestas grabadas inventadas con la forma de cada API."""
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import text

from horma.ingesta import leer_fuente
from horma.tools import dominio
from horma.tools.semilla import fuentes_semilla
from horma.web.db import sesion_de, sesion_sin_usuaria, sesion_sistema
from horma.web.repositories import ofertas as repo_ofertas
from horma.web.services import ofertas as servicio_ofertas

AYER = int((datetime.now(UTC) - timedelta(days=1)).timestamp())
MAÑANA = int((datetime.now(UTC) + timedelta(days=1)).timestamp())

RESPUESTAS = {
    "remotive": {"jobs": [{
        "id": 2069746, "url": "https://remotive.com/remote-jobs/software-dev/dev-2069746",
        "title": "Backend Engineer", "company_name": "Acme", "job_type": "full_time",
        "publication_date": "2026-11-14T20:33:53", "candidate_required_location": "Europa",
        "salary": "40k-50k €", "description": "<p>Python y SQL</p>"}]},
    "jobicy": {"jobs": [{
        "id": 155536, "url": "https://jobicy.com/jobs/155536-analista", "jobTitle": "Analista de datos",
        "companyName": "Datos SL", "jobType": ["Full-Time"], "jobGeo": "España",
        "pubDate": "2026-11-18T05:20:13+00:00", "jobDescription": "<p>Dashboards</p>"}]},
    "himalayas": {"jobs": [{
        "title": "Contable sénior", "companyName": "Cuentas SA", "employmentType": "Full Time",
        "locationRestrictions": ["Spain"], "pubDate": AYER, "expiryDate": MAÑANA,
        "applicationLink": "https://himalayas.app/companies/cuentas/jobs/contable",
        "guid": "https://himalayas.app/companies/cuentas/jobs/contable",
        "description": "<p>Cierre contable</p>"}]},
    "adzuna": {"results": [{
        "id": "4455", "title": "Camarera", "company": {"display_name": "Bar Sol"},
        "location": {"display_name": "Barcelona"}, "contract_time": "part_time",
        "created": "2026-11-15T10:00:00Z", "redirect_url": "https://www.adzuna.es/details/4455",
        "description": "Sala y barra"}]},
}
ENTORNO = {"ADZUNA_APP_ID": "i", "ADZUNA_APP_KEY": "k"}


def _semilla(nombre):
    return next(f for f in fuentes_semilla() if f.nombre == nombre)


def _http(nombre):
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=RESPUESTAS[nombre])))


@pytest.mark.parametrize("nombre", ["remotive", "jobicy", "himalayas", "adzuna"])
def test_cada_fuente_da_ofertas_normalizadas_con_enlace_y_atribucion(nombre):
    f = _semilla(nombre)
    assert f.activa is False  # solo se activa con una calificación apta
    assert f.atribucion and dominio.excluida_por_regla(f.web) is None
    ofertas = leer_fuente(f, _http(nombre), limite=5, entorno=ENTORNO)
    assert len(ofertas) == 1
    o = ofertas[0]
    assert o.url and o.url.startswith("https://") and o.id_externo
    assert "Empresa:" in o.texto and len(o.texto.splitlines()) > 3


def test_remotive_no_se_pide_mas_de_cuatro_veces_al_dia():
    assert _semilla("remotive").cada_horas >= 6
    assert _semilla("himalayas").cada_horas and _semilla("jobicy").cada_horas


def test_himalayas_trae_su_fecha_de_caducidad_y_se_salta_las_caducadas():
    f = _semilla("himalayas")
    [o] = leer_fuente(f, _http("himalayas"), limite=5)
    assert o.caduca is not None and o.caduca > datetime.now(UTC)
    caducada = {"jobs": [{**RESPUESTAS["himalayas"]["jobs"][0], "expiryDate": AYER}]}
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=caducada)))
    assert leer_fuente(f, http, limite=5) == []


# --- BD: atribución guardada y borrado de caducadas ---------------------------------------------
@pytest.mark.bd
def test_la_oferta_guarda_la_atribucion_de_su_fuente(motor_app, bd_limpia):
    with sesion_sistema(motor_app) as s:
        s.execute(text("update fuentes set activa=true where nombre='remotive'"))
    r = servicio_ofertas.recibir(motor_app, "Backend Engineer\nEmpresa: Acme", fuente="remotive",
                                 id_externo="1", url="https://remotive.com/x")
    with sesion_sistema(motor_app) as s:
        atribucion = s.execute(
            text("select atribucion from ofertas where id=:i"), {"i": r["id"]}
        ).scalar_one()
    assert atribucion == _semilla("remotive").atribucion


@pytest.mark.bd
def test_las_caducadas_se_borran_y_las_vigentes_se_quedan(motor_app, bd_limpia):
    with sesion_sistema(motor_app) as s:
        s.execute(text("update fuentes set activa=true where nombre='himalayas'"))
    pasado = datetime.now(UTC) - timedelta(hours=1)
    futuro = datetime.now(UTC) + timedelta(days=2)
    ids = {}
    for clave, caduca in (("vencida", pasado), ("vigente", futuro), ("sin_fecha", None)):
        ids[clave] = servicio_ofertas.recibir(motor_app, f"Oferta {clave}", fuente="himalayas",
                                              id_externo=clave, caduca_en=caduca)["id"]
    with sesion_sistema(motor_app) as s:
        assert repo_ofertas.borrar_caducadas(s) == 1
        quedan = set(s.execute(text("select id_externo from ofertas")).scalars())
    assert quedan == {"vigente", "sin_fecha"}


def _oferta_con_nota(motor_app, usuaria, clave, caduca):
    """Oferta del catálogo con una nota de `usuaria`, creada con la sesión de ella como hace la app."""
    oid = servicio_ofertas.recibir(motor_app, f"Oferta {clave}", fuente="himalayas",
                                   id_externo=clave, caduca_en=caduca)["id"]
    with sesion_de(motor_app, usuaria) as s:
        s.execute(text("insert into matches (usuaria_id, oferta_id, perfil_version, nota, condiciones) "
                       "values (:u, :o, 1, 80, 'alto')"), {"u": usuaria, "o": oid})
    return oid


def _caducada_y_vigente(motor_app):
    with sesion_sin_usuaria(motor_app) as s:
        u = s.execute(text("select obtener_o_crear_usuaria('google-T08n')")).scalar_one()
    with sesion_sistema(motor_app) as s:
        s.execute(text("update fuentes set activa=true where nombre='himalayas'"))
    ayer = datetime.now(UTC) - timedelta(hours=1)
    manana = datetime.now(UTC) + timedelta(days=2)
    return (u, _oferta_con_nota(motor_app, u, "vencida", ayer),
            _oferta_con_nota(motor_app, u, "vigente", manana))


@pytest.mark.bd
def test_borrar_caducadas_con_notas_borra_la_oferta_y_su_nota(motor_app, bd_limpia):
    u, vencida, vigente = _caducada_y_vigente(motor_app)
    with sesion_sistema(motor_app) as s:
        assert repo_ofertas.borrar_caducadas(s) == 1
    with sesion_de(motor_app, u) as s:
        assert set(s.execute(text("select oferta_id from matches")).scalars()) == {vigente}
        assert set(s.execute(text("select id from ofertas")).scalars()) == {vigente}


@pytest.mark.bd
def test_el_sistema_solo_ve_las_notas_de_las_caducadas(motor_app, bd_limpia):
    u, vencida, vigente = _caducada_y_vigente(motor_app)
    with sesion_sistema(motor_app) as s:
        assert set(s.execute(text("select oferta_id from matches")).scalars()) == {vencida}
        assert s.execute(text("select count(*) from matches where oferta_id=:o"),
                         {"o": vigente}).scalar_one() == 0


@pytest.mark.bd
def test_la_caducada_con_candidatura_no_se_borra(motor_app, bd_limpia):
    u, vencida, vigente = _caducada_y_vigente(motor_app)
    with sesion_de(motor_app, u) as s:
        s.execute(text("insert into candidaturas (usuaria_id, oferta_id) values (:u, :o)"),
                  {"u": u, "o": vencida})
    with sesion_sistema(motor_app) as s:
        assert repo_ofertas.borrar_caducadas(s) == 0
    with sesion_de(motor_app, u) as s:
        assert {vencida, vigente} == set(s.execute(text("select id from ofertas")).scalars())
        assert s.execute(text("select count(*) from matches")).scalar_one() == 2
