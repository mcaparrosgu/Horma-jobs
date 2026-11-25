"""Spec 011 (T08k, RF-11.29, D-030) · una URL ya añadida no se vuelve a leer; «Leer de nuevo» actualiza la
misma oferta. Sin llamadas al modelo ni a Apify: `lector` falso y `ProveedorSimulado`."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from horma import config
from horma.llm.simulado import ProveedorSimulado
from horma.tools import validar_url as validar
from horma.web.main import crear_app
from horma.web.queue import worker

URL = "https://job-boards.greenhouse.io/hotelmar/jobs/1"
PAGINA = "# Camarera de sala\n\nHotel Mar busca camarera de sala para la temporada. " * 12
PAGINA_NUEVA = "# Camarera de sala\n\nHotel Mar busca camarera de sala y ofrece contrato indefinido. " * 12
TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior", "stack": []}
EXTRACCION = {"titulo": "Camarera de sala", "empresa": "Hotel Mar", "fecha_publicacion": "2026-11-01"}
AUDITOR = {"generica": False, "fraude": False}


# --- url_canonica (sin base de datos) ----------------------------------------------------------
@pytest.mark.parametrize("entrada, esperada", [
    ("https://jobtoday.com/es/trabajo/camarera-lZG5dm?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply"
     "&utm_medium=organic", "https://jobtoday.com/es/trabajo/camarera-lZG5dm"),
    ("HTTPS://Empresa.COM/Ofertas/Camarera-AB", "https://empresa.com/Ofertas/Camarera-AB"),
    ("https://empresa.com/oferta/1#solicitar", "https://empresa.com/oferta/1"),
    ("https://empresa.com/oferta/1/", "https://empresa.com/oferta/1"),
    ("https://empresa.com/", "https://empresa.com/"),
    ("https://empresa.com", "https://empresa.com/"),
    ("https://empresa.com/o?id=7&gclid=x&b=2&fbclid=y&msclkid=z", "https://empresa.com/o?id=7&b=2"),
    ("https://empresa.com/o?b=2&id=7", "https://empresa.com/o?b=2&id=7"),   # el resto, en su orden
    ("  https://empresa.com/o?utm_source=a  ", "https://empresa.com/o"),
])
def test_url_canonica(entrada, esperada):
    from horma.tools.validar_url import url_canonica
    assert url_canonica(entrada) == esperada


# --- API y worker (con base de datos) ----------------------------------------------------------
class IdentidadFalsa:
    async def redirigir(self, request, redirect_uri):
        from starlette.responses import RedirectResponse
        return RedirectResponse("https://accounts.google.test/auth")

    async def sub_desde_callback(self, request) -> str:
        return request.query_params["code"]


@pytest.fixture
def app(motor_app, bd_limpia, tmp_path, monkeypatch):
    monkeypatch.setenv("RUTA_ARCHIVOS", str(tmp_path / "archivos"))
    monkeypatch.setenv("LIMITE_URL_HORA", "50")
    monkeypatch.setattr(validar, "_resolver", lambda host: ["151.101.1.1"])
    config.ajustes.cache_clear()
    yield crear_app(engine=motor_app, identidad=IdentidadFalsa())
    config.ajustes.cache_clear()


def _entrar(app, sub="google-A"):
    c = TestClient(app, follow_redirects=False)
    assert c.get(f"/auth/google/callback?code={sub}").status_code == 302
    return c, {"X-CSRF-Token": c.get("/api/yo").json()["csrf"]}


def _cuenta(motor_migrador, tabla, donde=""):
    with motor_migrador.connect() as s:
        return s.execute(text(f"select count(*) from {tabla} {donde}")).scalar_one()


def _anadir_y_analizar(app, motor_app, c, h, url=URL, pagina=PAGINA):
    r = c.post("/ofertas/url", headers=h, json={"url": url})
    assert r.status_code == 202
    assert worker.procesar_una(motor_app, lector=lambda u: pagina) == "hecha"
    prov = ProveedorSimulado([EXTRACCION, AUDITOR, TAX])
    assert worker.procesar_una(motor_app, prov, resolver=None) == "hecha"
    assert worker.procesar_una(motor_app) == "hecha"   # «puntuar_propias», que encola el análisis
    assert worker.procesar_una(motor_app) is None
    return r.json()["id"]


@pytest.mark.bd
def test_la_misma_url_con_o_sin_utm_no_se_vuelve_a_leer_ni_a_encolar(app, motor_app, motor_migrador):
    c, h = _entrar(app)
    _anadir_y_analizar(app, motor_app, c, h)
    importaciones, tareas = _cuenta(motor_migrador, "importaciones"), _cuenta(motor_migrador, "tareas")
    with motor_migrador.connect() as s:
        oferta_id, creada = s.execute(text("select id, creada_en from ofertas")).one()
    for url in (URL, URL + "?utm_source=google_jobs_apply&gclid=abc#aplicar", "HTTPS://JOB-BOARDS.GREENHOUSE.IO/hotelmar/jobs/1/"):
        r = c.post("/ofertas/url", headers=h, json={"url": url})
        assert r.status_code == 200, url
        d = r.json()
        assert d["repetida"] is True and d["oferta_id"] == oferta_id and d["titulo"] == "Camarera de sala"
        assert d["anadida_en"].startswith(creada.isoformat()[:10])
    assert _cuenta(motor_migrador, "importaciones") == importaciones
    assert _cuenta(motor_migrador, "tareas") == tareas


@pytest.mark.bd
def test_la_oferta_de_otra_usuaria_no_cuenta_como_repetida(app, motor_app):
    ana, ha = _entrar(app)
    berta, hb = _entrar(app, "google-B")
    _anadir_y_analizar(app, motor_app, ana, ha)
    r = berta.post("/ofertas/url", headers=hb, json={"url": URL})
    assert r.status_code == 202 and "repetida" not in r.json()


@pytest.mark.bd
def test_una_url_pendiente_devuelve_la_misma_importacion(app, motor_migrador):
    c, h = _entrar(app)
    primera = c.post("/ofertas/url", headers=h, json={"url": URL})
    segunda = c.post("/ofertas/url", headers=h, json={"url": URL + "?utm_medium=organic"})
    assert primera.status_code == 202
    assert segunda.json() == {"id": primera.json()["id"], "estado": "pendiente"}
    assert _cuenta(motor_migrador, "importaciones") == 1
    assert _cuenta(motor_migrador, "tareas", "where tipo='leer_url'") == 1


@pytest.mark.bd
def test_releer_crea_una_importacion_con_la_oferta_y_encola_la_lectura(app, motor_app, motor_migrador):
    c, h = _entrar(app)
    _anadir_y_analizar(app, motor_app, c, h)
    with motor_migrador.connect() as s:
        oferta_id = s.execute(text("select id from ofertas")).scalar_one()
    r = c.post("/ofertas/url", headers=h, json={"url": URL + "?utm_source=x", "releer": True})
    assert r.status_code == 202 and r.json()["estado"] == "pendiente" and "repetida" not in r.json()
    with motor_migrador.connect() as s:
        fila = s.execute(text("select id, oferta_id, estado from importaciones "
                              "order by id desc limit 1")).one()
    assert fila.id == r.json()["id"] and fila.oferta_id == oferta_id and fila.estado == "pendiente"
    assert _cuenta(motor_migrador, "tareas", "where tipo='leer_url' and estado='pendiente'") == 1


@pytest.mark.bd
def test_releer_sin_oferta_previa_es_como_una_lectura_normal(app, motor_migrador):
    c, h = _entrar(app)
    r = c.post("/ofertas/url", headers=h, json={"url": URL, "releer": True})
    assert r.status_code == 202
    with motor_migrador.connect() as s:
        assert s.execute(text("select oferta_id from importaciones")).scalar_one() is None


def _con_match(motor_migrador, oferta_id):
    with motor_migrador.begin() as s:
        uid = s.execute(text("select usuaria_id from ofertas where id=:o"), {"o": oferta_id}).scalar_one()
        s.execute(text("insert into perfiles (usuaria_id, version) values (:u, 1) on conflict do nothing"),
                  {"u": uid})
        s.execute(text("insert into matches (usuaria_id, oferta_id, perfil_version, nota, condiciones) "
                       "values (:u, :o, 1, 80, 'alto')"), {"u": uid, "o": oferta_id})


@pytest.mark.bd
def test_releer_con_texto_distinto_actualiza_la_misma_oferta(app, motor_app, motor_migrador):
    c, h = _entrar(app)
    _anadir_y_analizar(app, motor_app, c, h)
    with motor_migrador.connect() as s:
        oferta_id = s.execute(text("select id from ofertas")).scalar_one()
    _con_match(motor_migrador, oferta_id)
    tareas_antes = _cuenta(motor_migrador, "tareas", "where tipo='procesar_oferta'")
    imp = c.post("/ofertas/url", headers=h, json={"url": URL, "releer": True}).json()["id"]
    assert worker.procesar_una(motor_app, lector=lambda u: PAGINA_NUEVA) == "hecha"
    with motor_migrador.connect() as s:
        ofertas = s.execute(text("select id, estado, texto_crudo, motivo_error from ofertas")).all()
        assert len(ofertas) == 1
        o = ofertas[0]
        assert o.id == oferta_id and o.estado == "pendiente" and "indefinido" in o.texto_crudo
        assert o.motivo_error is None
        assert s.execute(text("select count(*) from matches where oferta_id=:o"),
                         {"o": oferta_id}).scalar_one() == 0
        assert s.execute(text("select estado, oferta_id from importaciones where id=:i"), {"i": imp}).one() \
            == ("leida", oferta_id)
    assert _cuenta(motor_migrador, "tareas", "where tipo='procesar_oferta'") == tareas_antes + 1


@pytest.mark.bd
def test_releer_con_el_mismo_texto_no_cambia_nada_ni_encola(app, motor_app, motor_migrador):
    c, h = _entrar(app)
    _anadir_y_analizar(app, motor_app, c, h)
    with motor_migrador.connect() as s:
        oferta_id = s.execute(text("select id from ofertas")).scalar_one()
    _con_match(motor_migrador, oferta_id)
    tareas_antes = _cuenta(motor_migrador, "tareas")
    imp = c.post("/ofertas/url", headers=h, json={"url": URL, "releer": True}).json()["id"]
    tareas_antes += 1   # la propia lectura
    assert worker.procesar_una(motor_app, lector=lambda u: PAGINA) == "hecha"
    with motor_migrador.connect() as s:
        assert s.execute(text("select estado from ofertas where id=:o"),
                         {"o": oferta_id}).scalar_one() == "procesada"
        assert s.execute(text("select count(*) from matches")).scalar_one() == 1
        assert s.execute(text("select estado, oferta_id from importaciones where id=:i"), {"i": imp}).one() \
            == ("leida", oferta_id)
    assert _cuenta(motor_migrador, "tareas") == tareas_antes



@pytest.mark.bd
def test_releer_una_oferta_en_error_la_vuelve_a_analizar_con_el_mismo_texto(app, motor_app, motor_migrador):
    c, h = _entrar(app)
    _anadir_y_analizar(app, motor_app, c, h)
    with motor_migrador.begin() as s:
        oferta_id = s.execute(text("select id from ofertas")).scalar_one()
        s.execute(text("update ofertas set estado='error', motivo_error='tope de coste' where id=:o"),
                  {"o": oferta_id})
    tareas_antes = _cuenta(motor_migrador, "tareas", "where tipo='procesar_oferta'")
    c.post("/ofertas/url", headers=h, json={"url": URL, "releer": True})
    assert worker.procesar_una(motor_app, lector=lambda u: PAGINA) == "hecha"
    with motor_migrador.connect() as s:
        assert s.execute(text("select estado, motivo_error from ofertas where id=:o"),
                         {"o": oferta_id}).one() == ("pendiente", None)
    assert _cuenta(motor_migrador, "tareas", "where tipo='procesar_oferta'") == tareas_antes + 1
