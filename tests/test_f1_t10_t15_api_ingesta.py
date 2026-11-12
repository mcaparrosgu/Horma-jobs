"""Fase 1 · T10-T15: claves de API, POST /ofertas, worker, administración, ingestor, dashboard y
consola `fuente calificar`."""
import hashlib
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from typer.testing import CliRunner

from horma import config
from horma.ingesta import ClienteApi, atender_una, ingestar_fuente, leer_fuente
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.fuente import Fuente
from horma.web.db import sesion_sistema
from horma.web.main import crear_app
from horma.web.queue import worker

pytestmark = pytest.mark.bd

ADMIN = "google-admin"
AUDITOR = {"generica": False, "fraude": False}
TAX = {"sector": "tecnologia", "familia": "desarrollo_software", "nivel": "sin_especificar"}


class IdentidadFalsa:
    async def redirigir(self, request, redirect_uri):
        from starlette.responses import RedirectResponse

        return RedirectResponse("https://accounts.google.test/auth")

    async def sub_desde_callback(self, request) -> str:
        return request.query_params["code"]


@pytest.fixture
def ajustes_prueba(monkeypatch):
    monkeypatch.setenv("HORMA_ADMINS", f"otra-admin, {ADMIN}")
    monkeypatch.setenv("LIMITE_OFERTAS_POR_MINUTO", "1000")
    monkeypatch.setenv("HORMA_FLUJO_EN_LINEA", "false")
    config.ajustes.cache_clear()
    yield monkeypatch
    config.ajustes.cache_clear()


@pytest.fixture
def app(motor_app, bd_limpia, ajustes_prueba):
    return crear_app(engine=motor_app, identidad=IdentidadFalsa())


@pytest.fixture
def cliente(app):
    with TestClient(app, follow_redirects=False) as c:
        yield c


def entrar(c, sub=ADMIN) -> dict:
    assert c.get(f"/auth/google/callback?code={sub}").status_code == 302
    return {"X-CSRF-Token": c.get("/api/yo").json()["csrf"]}


def crear_clave(c, alcance="ingesta") -> str:
    h = entrar(c)
    r = c.post("/api/claves", json={"nombre": f"prueba-{alcance}", "alcance": alcance}, headers=h)
    assert r.status_code == 201, r.text
    c.post("/auth/logout", headers=h)
    return r.json()["clave"]


def activar(motor, nombre="arbeitnow"):
    with sesion_sistema(motor) as s:
        s.execute(text("update fuentes set activa=true where nombre=:n"), {"n": nombre})
        return s.execute(text("select id from fuentes where nombre=:n"), {"n": nombre}).scalar_one()


def bearer(clave: str) -> dict:
    return {"Authorization": f"Bearer {clave}"}


# --- T10: claves y POST /ofertas ---------------------------------------------------------------
def test_la_clave_se_guarda_como_hash_y_solo_se_enseña_una_vez(cliente, motor_app):
    clave = crear_clave(cliente, "ofertas")
    assert clave.startswith("hk_")
    with sesion_sistema(motor_app) as s:
        guardado = s.execute(text("select hash, prefijo from claves_api")).one()
    assert guardado.hash == hashlib.sha256(clave.encode()).hexdigest() and clave not in guardado
    h = entrar(cliente)
    listado = cliente.get("/api/claves", headers=h).json()
    assert listado[0]["prefijo"] == guardado.prefijo and "clave" not in listado[0]
    assert "hash" not in listado[0]


def test_post_ofertas_con_clave_valida_falsa_y_revocada(cliente):
    clave = crear_clave(cliente, "ofertas")
    assert cliente.post("/ofertas", json={"texto": "Camarera"}, headers=bearer(clave)).status_code == 201
    assert cliente.post("/ofertas", json={"texto": "x"}, headers=bearer("hk_falsa")).status_code == 401
    h = entrar(cliente)
    clave_id = cliente.get("/api/claves", headers=h).json()[0]["id"]
    assert cliente.delete(f"/api/claves/{clave_id}", headers=h).status_code == 204
    assert cliente.post("/ofertas", json={"texto": "y"}, headers=bearer(clave)).status_code == 401


def test_una_clave_de_empresa_no_puede_hacerse_pasar_por_una_fuente(cliente):
    clave = crear_clave(cliente, "ofertas")
    r = cliente.post("/ofertas", json={"texto": "x", "fuente": "arbeitnow"}, headers=bearer(clave))
    assert r.status_code == 403


def test_limite_de_tamano_y_de_ritmo(cliente, ajustes_prueba):
    clave = crear_clave(cliente, "ofertas")
    grande = json.dumps({"texto": "a" * 70000})
    r = cliente.post("/ofertas", content=grande, headers={**bearer(clave),
                                                          "Content-Type": "application/json"})
    assert r.status_code == 413
    assert cliente.post("/ofertas", json={"texto": "a" * 20001},
                        headers=bearer(clave)).status_code == 422
    ajustes_prueba.setenv("LIMITE_OFERTAS_POR_MINUTO", "2")
    config.ajustes.cache_clear()
    codigos = [cliente.post("/ofertas", json={"texto": f"oferta {i}"},
                            headers=bearer(clave)).status_code for i in range(3)]
    assert codigos == [201, 201, 429]


def test_misma_oferta_de_la_misma_fuente_no_se_duplica(cliente, motor_app):
    activar(motor_app)
    clave = crear_clave(cliente)
    cuerpo = {"texto": "Dev en Acme", "fuente": "arbeitnow", "id_externo": "dev-1"}
    r1 = cliente.post("/ofertas", json=cuerpo, headers=bearer(clave))
    r2 = cliente.post("/ofertas", json=cuerpo, headers=bearer(clave))
    assert r1.status_code == 201 and r1.json()["nueva"] is True
    assert r2.status_code == 200 and r2.json() == {**r1.json(), "nueva": False}
    with sesion_sistema(motor_app) as s:
        assert s.execute(text("select count(*) from tareas")).scalar_one() == 1


# --- T11: worker -------------------------------------------------------------------------------
def test_el_mismo_texto_desde_otro_origen_queda_marcado_como_repetido(cliente, motor_app):
    clave = crear_clave(cliente, "ofertas")
    texto = "Dev Python en Acme. Publicada: 2026-11-01"
    for i in (1, 2):
        cliente.post("/ofertas", json={"texto": texto, "id_externo": str(i)}, headers=bearer(clave))
    respuestas = [{"titulo": "Dev Python", "empresa": "Acme", "fecha_publicacion": "2026-11-01"},
                  AUDITOR, TAX] * 2
    prov = ProveedorSimulado(respuestas)
    assert worker.procesar_una(motor_app, prov, resolver=None) == "hecha"
    assert worker.procesar_una(motor_app, prov, resolver=None) == "hecha"
    with sesion_sistema(motor_app) as s:
        filas = s.execute(text("select motivos_fantasma, recomendable from ofertas order by id")).all()
    assert filas[0] == ([], True) and filas[1] == (["repetida"], False)


def test_calificar_por_la_api_y_el_worker(cliente, motor_app):
    h = entrar(cliente)
    r = cliente.post("/api/fuentes/calificaciones", json={"url": "https://www.linkedin.com/jobs"},
                     headers=h)
    assert r.status_code == 202 and r.json()["estado"] == "pendiente"
    assert worker.procesar_una(motor_app, ProveedorSimulado([])) == "hecha"
    c = cliente.get(f"/api/fuentes/calificaciones/{r.json()['id']}", headers=h).json()
    assert c["estado"] == "hecha" and c["apta"] is False and c["excluida_por_regla"] is True

    paginas = {"https://www.arbeitnow.com/": '<a href="/terms">Terms</a>',
               "https://www.arbeitnow.com/terms": "<p>You may use our public job API.</p>",
               "https://www.arbeitnow.com/robots.txt": "User-agent: *\nDisallow: /admin"}
    r = cliente.post("/api/fuentes/calificaciones", json={"url": "https://www.arbeitnow.com/"},
                     headers=h)
    prov = ProveedorSimulado([{"permite_uso_automatizado": True, "requiere_clave": False,
                               "motivos": ["API pública."]}])
    assert worker.procesar_una(motor_app, prov, descargador=paginas.__getitem__) == "hecha"
    c = cliente.get(f"/api/fuentes/calificaciones/{r.json()['id']}", headers=h).json()
    assert c["apta"] is True and c["dominio"] == "arbeitnow.com"


# --- T12: administración -----------------------------------------------------------------------
def test_sin_sesion_401_y_sin_ser_admin_403(cliente):
    assert cliente.get("/api/ingesta/resumen").status_code == 401
    assert cliente.get("/ingesta").status_code == 401
    entrar(cliente, "google-normal")
    assert cliente.get("/api/ingesta/resumen").status_code == 403
    assert cliente.get("/ingesta").status_code == 403
    assert cliente.get("/api/claves").status_code == 403
    assert cliente.get("/api/yo").json()["admin"] is False


def test_resumen_muestra_fuentes_sembradas_ofertas_por_estado_y_errores(cliente):
    h = entrar(cliente)
    cliente.post("/ofertas", json={"texto": "Oferta pegada"}, headers=h)
    r = cliente.get("/api/ingesta/resumen").json()
    nombres = {f["nombre"]: f for f in r["fuentes"]}
    assert {"arbeitnow", "adzuna"} <= set(nombres) and nombres["arbeitnow"]["activa"] is False
    assert r["ofertas_por_estado"] == {"pendiente": 1}
    assert r["errores"] == []


def test_activar_una_fuente_exige_calificacion_apta(cliente, motor_app):
    h = entrar(cliente)
    fuente = next(f for f in cliente.get("/api/ingesta/resumen").json()["fuentes"]
                  if f["nombre"] == "arbeitnow")
    datos = {k: fuente[k] for k in Fuente.model_fields} | {"activa": True}
    assert cliente.put(f"/api/fuentes/{fuente['id']}", json=datos, headers=h).status_code == 409
    with sesion_sistema(motor_app) as s:
        s.execute(text("insert into calificaciones_fuente (url, dominio, estado, apta) "
                       "values ('https://www.arbeitnow.com', 'arbeitnow.com', 'hecha', true)"))
    assert cliente.put(f"/api/fuentes/{fuente['id']}", json=datos, headers=h).status_code == 200


def test_no_se_registran_linkedin_ni_indeed_y_sin_csrf_no_se_edita(cliente):
    h = entrar(cliente)
    mala = {"nombre": "linkedin", "web": "https://www.linkedin.com", "url": "https://api.linkedin.com/x",
            "mapeo": {}}
    assert cliente.post("/api/fuentes", json=mala, headers=h).status_code == 422
    buena = dict(mala, nombre="nueva", web="https://nueva.test", url="https://nueva.test/api")
    assert cliente.post("/api/fuentes", json=buena).status_code == 403
    assert cliente.post("/api/fuentes", json=buena, headers=h).status_code == 201


def test_el_boton_deja_una_ejecucion_pendiente_y_no_ingesta(cliente, motor_app):
    h = entrar(cliente)
    fid = activar(motor_app, "adzuna")
    r = cliente.post("/api/ingesta/ejecuciones", json={"fuente_id": fid, "limite": 5}, headers=h)
    assert r.status_code == 201 and r.json()["estado"] == "pendiente"
    inactiva = next(f["id"] for f in cliente.get("/api/ingesta/resumen").json()["fuentes"]
                    if f["nombre"] == "arbeitnow")
    assert cliente.post("/api/ingesta/ejecuciones", json={"fuente_id": inactiva},
                        headers=h).status_code == 409
    fuentes = {f["nombre"]: f for f in cliente.get("/api/ingesta/resumen").json()["fuentes"]}
    assert fuentes["adzuna"]["ultima_ejecucion"]["estado"] == "pendiente"
    with sesion_sistema(motor_app) as s:
        assert s.execute(text("select count(*) from ofertas")).scalar_one() == 0


# --- T13: ingestor sin BD ----------------------------------------------------------------------
RESPUESTA = {"data": [
    {"slug": f"dev-{i}", "title": f"Backend Developer {i}", "company_name": "Acme",
     "location": "Berlin", "remote": True, "url": f"https://x.test/dev-{i}",
     "created_at": 1767225600, "description": "<p>Python</p>"} for i in range(3)]}


def _fuentes_http(peticiones: list):
    def responder(request: httpx.Request):
        peticiones.append(request)
        return httpx.Response(200, json=RESPUESTA)
    return httpx.Client(transport=httpx.MockTransport(responder))


def test_el_ingestor_entrega_por_la_api_y_cierra_la_ejecucion(cliente, motor_app):
    activar(motor_app)
    api = ClienteApi("", crear_clave(cliente), http=cliente)
    peticiones = []
    res = ingestar_fuente(api, "arbeitnow", limite=2, http_fuentes=_fuentes_http(peticiones))
    assert res["estado"] == "hecha" and (res["recibidas"], res["nuevas"]) == (2, 2)
    assert str(peticiones[0].url).startswith("https://www.arbeitnow.com/api/job-board-api")
    res = ingestar_fuente(api, "arbeitnow", limite=3, http_fuentes=_fuentes_http([]))
    assert (res["nuevas"], res["repetidas"]) == (1, 2)
    with sesion_sistema(motor_app) as s:
        filas = s.execute(text("select o.id_externo, f.nombre, o.texto_crudo from ofertas o "
                               "join fuentes f on f.id = o.fuente_id order by o.id")).all()
        ejecuciones = s.execute(text("select estado from ejecuciones_ingesta")).scalars().all()
    assert [f.id_externo for f in filas] == ["dev-0", "dev-1", "dev-2"]
    assert filas[0].texto_crudo.startswith("Backend Developer 0\nEmpresa: Acme")
    assert ejecuciones == ["hecha", "hecha"]


def test_el_ingestor_atiende_las_ejecuciones_del_boton(cliente, motor_app):
    fid = activar(motor_app)
    clave = crear_clave(cliente)
    h = entrar(cliente)
    cliente.post("/api/ingesta/ejecuciones", json={"fuente_id": fid, "limite": 1}, headers=h)
    api = ClienteApi("", clave, http=cliente)
    assert atender_una(api, _fuentes_http([]))["nuevas"] == 1
    assert atender_una(api, _fuentes_http([])) is None  # no queda ninguna


def test_un_endpoint_que_falla_deja_la_ejecucion_en_error(cliente, motor_app):
    activar(motor_app)
    api = ClienteApi("", crear_clave(cliente), http=cliente)
    roto = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    res = ingestar_fuente(api, "arbeitnow", limite=2, http_fuentes=roto)
    assert res["estado"] == "error" and "500" in res["motivo_error"]


def test_leer_fuente_sustituye_solo_sus_variables():
    f = Fuente(nombre="adzuna", web="https://www.adzuna.es", url="https://api.adzuna.test/search",
               parametros={"app_id": "${ADZUNA_APP_ID}", "app_key": "${ADZUNA_APP_KEY}", "n": 5},
               variable_clave="ADZUNA_APP_ID,ADZUNA_APP_KEY", mapeo={"lista": "data", "id": "slug",
                                                                       "titulo": "title"})
    peticiones = []
    ofertas = leer_fuente(f, _fuentes_http(peticiones), limite=1,
                          entorno={"ADZUNA_APP_ID": "id1", "ADZUNA_APP_KEY": "k1"})
    assert len(ofertas) == 1 and ofertas[0].id_externo == "dev-0"
    q = dict(peticiones[0].url.params)
    assert q == {"app_id": "id1", "app_key": "k1", "n": "5"}
    with pytest.raises(ValueError):
        leer_fuente(f, _fuentes_http([]), limite=1, entorno={})


# --- T14: web ----------------------------------------------------------------------------------
def test_dashboard_solo_para_admin_y_yo_dice_si_es_admin(cliente):
    entrar(cliente)
    yo = cliente.get("/api/yo").json()
    assert yo["admin"] is True and yo["sub"] == ADMIN
    r = cliente.get("/ingesta")
    assert r.status_code == 200 and '<script src="/static/ingesta.js"' in r.text


def test_el_js_del_dashboard_pinta_con_textcontent():
    from pathlib import Path

    static = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
    for archivo in ("ingesta.js", "app.js"):
        js = (static / archivo).read_text(encoding="utf-8")
        assert "innerHTML" not in js and "insertAdjacentHTML" not in js and "eval(" not in js


def test_el_catalogo_muestra_auditoria_y_taxonomia(cliente, motor_app):
    h = entrar(cliente, "google-normal")
    cliente.post("/ofertas", json={"texto": "Dev en Acme. Paga 30 euros de alta."}, headers=h)
    worker.procesar_una(motor_app, ProveedorSimulado([
        {"titulo": "Dev", "empresa": "Acme"},
        {"generica": False, "fraude": True, "senales_fraude": ["Paga 30 euros de alta."]}, TAX]),
        resolver=None)
    o = cliente.get("/ofertas").json()[0]
    assert o["fraude"] is True and o["recomendable"] is False and o["familia"] == "desarrollo_software"
    assert o["motivos_fantasma"] == ["sin_fecha"] and o["frase_pedir_salario"]


# --- T15: consola `fuente calificar` -----------------------------------------------------------
def test_consola_fuente_calificar_por_la_api(cliente, app, monkeypatch):
    from horma import cli

    clave = crear_clave(cliente)
    monkeypatch.setattr(cli, "_cliente_api", lambda: ClienteApi("", clave, http=cliente))
    monkeypatch.setattr(cli, "_esperar", lambda segundos: worker.procesar_una(
        app.state.engine, ProveedorSimulado([])))
    r = CliRunner().invoke(cli.app, ["fuente", "calificar", "https://es.indeed.com"])
    assert r.exit_code == 0, r.output
    assert "NO APTA" in r.output and "Indeed" in r.output


def test_consola_fuente_calificar_local_no_guarda(motor_app, bd_limpia):
    from horma import cli

    r = CliRunner().invoke(cli.app, ["fuente", "calificar", "https://www.linkedin.com", "--local"])
    assert r.exit_code == 0 and "NO APTA" in r.output
    with sesion_sistema(motor_app) as s:
        assert s.execute(text("select count(*) from calificaciones_fuente")).scalar_one() == 0
