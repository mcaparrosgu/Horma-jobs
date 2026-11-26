"""Fase 9a · bloque D: avisos, longitud, otras actividades y preferencias con puestos (T11-T13)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from horma import config
from horma.schemas.perfil import Perfil
from horma.web.db import sesion_de
from horma.web.main import crear_app
from horma.web.repositories import perfiles

pytestmark = pytest.mark.bd


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


def entrar(app, sub="google-A"):
    c = TestClient(app, follow_redirects=False)
    assert c.get(f"/auth/google/callback?code={sub}").status_code == 302
    return c, {"X-CSRF-Token": c.get("/api/yo").json()["csrf"]}


def uid(motor_migrador, sub="google-A"):
    with motor_migrador.connect() as c:
        return c.execute(text("select id from usuarias where google_sub=:s"), {"s": sub}).scalar_one()


ORIG = {"fuente": "usuaria", "fragmento": "x"}


def perfil_de(motor_app, u, descripcion="Atendía a 40 clientes", cv="ana@x.es"):
    base = {"resumen": {"valor": "Resumen", "origen": ORIG},
            "experiencias": [{"puesto": "Camarera", "empresa": "Hotel Mar", "inicio": "2018-01",
                              "fin": "2019-02", "descripcion": descripcion, "origen": ORIG},
                             {"puesto": "Cajera", "empresa": "Super Sur", "inicio": "2019-11",
                              "fin": "actual", "descripcion": "Caja 12 horas", "origen": ORIG}]}
    with sesion_de(motor_app, u) as s:
        pid, version = perfiles.nueva_version(s, u)
        perfiles.guardar_perfil(s, u, pid, Perfil.model_validate({**base, "version": version}),
                                "# Ana\n" + "palabra " * 10)
        s.execute(text("delete from cv_archivos"))
        s.execute(text("insert into cv_archivos (usuaria_id, nombre, nombre_original, ruta, tipo, clase, "
                       "tamano, texto) values (:u, 'cv', 'cv.md', :r, 'md', 'fuente', 10, :t)"),
                  {"u": u, "r": f"r{u}{pid}", "t": f"Ana {cv}"})


def claves(r):
    return [a["clave"] for a in r["huecos"] + r["avisos"]]


# --- T11 ------------------------------------------------------------------------------------------------
def test_avisos_con_huecos_y_sin_los_vistos(app, motor_app, motor_migrador):
    c, h = entrar(app)
    perfil_de(motor_app, uid(motor_migrador))
    r = c.get("/api/perfil/avisos").json()
    assert claves(r) == ["hueco:2019-03:2019-10"]
    assert r["huecos"][0]["texto"].startswith("Entre marzo de 2019 y octubre de 2019")
    hueco = r["huecos"][0]
    assert c.put("/api/perfil/avisos/visto", json={"clave": hueco["clave"], "huella": hueco["huella"]},
                 headers=h).status_code == 200
    assert c.get("/api/perfil/avisos").json()["total"] == 0


def test_un_aviso_visto_vuelve_si_cambia_la_causa(app, motor_app, motor_migrador):
    c, h = entrar(app)
    u = uid(motor_migrador)

    def sin_cifras():
        avisos = c.get("/api/perfil/avisos").json()["avisos"]
        return [x for x in avisos if x["clave"].startswith("sin_cifras")]

    perfil_de(motor_app, u, descripcion="Atendía a los clientes")
    (a,) = sin_cifras()
    c.put("/api/perfil/avisos/visto", json={"clave": a["clave"], "huella": a["huella"]}, headers=h)
    perfil_de(motor_app, u, descripcion="Atendía a los clientes")  # mismo CV: no vuelve
    assert not sin_cifras()
    perfil_de(motor_app, u, descripcion="Atendía a todos los clientes del hotel")  # otra causa
    assert sin_cifras()


def test_sin_correo_ni_telefono_avisa_por_cv(app, motor_app, motor_migrador):
    c, _ = entrar(app)
    perfil_de(motor_app, uid(motor_migrador), cv="sin datos")
    assert any(k.startswith("sin_contacto:") for k in claves(c.get("/api/perfil/avisos").json()))


def test_elegir_longitud_oculta_el_aviso_de_cv_largo(app, motor_app, motor_migrador):
    c, h = entrar(app)
    u = uid(motor_migrador)
    perfil_de(motor_app, u)
    with sesion_de(motor_app, u) as s:
        s.execute(text("update perfiles set cv_maestro = :m"), {"m": "palabra " * 1200})
    assert "largo" in claves(c.get("/api/perfil/avisos").json())
    assert c.put("/api/perfil/longitud", json={"longitud": "otra"}, headers=h).status_code == 422
    assert c.put("/api/perfil/longitud", json={"longitud": "mantener"}, headers=h).status_code == 200
    r = c.get("/api/perfil/avisos").json()
    assert "largo" not in claves(r) and r["longitud"] == "mantener"


def test_otra_usuaria_no_ve_lo_ajeno(app, motor_app, motor_migrador):
    a, ha = entrar(app, "google-A")
    b, _ = entrar(app, "google-B")
    perfil_de(motor_app, uid(motor_migrador, "google-A"))
    hueco = a.get("/api/perfil/avisos").json()["huecos"][0]
    a.put("/api/perfil/avisos/visto", json={"clave": hueco["clave"], "huella": hueco["huella"]}, headers=ha)
    a.put("/api/perfil/longitud", json={"longitud": "mantener"}, headers=ha)
    assert b.get("/api/perfil/avisos").json() == {"huecos": [], "avisos": [], "grupos": [], "total": 0,
                                                  "longitud": None}


# --- T12 ------------------------------------------------------------------------------------------------
def test_actividades_se_anaden_corrigen_y_borran_con_version(app, motor_app, motor_migrador):
    c, h = entrar(app)
    perfil_de(motor_app, uid(motor_migrador))
    r = c.patch("/api/perfil/datos", headers=h, json={"campo": "actividades", "dato": {
        "descripcion": "Voluntariado", "inicio": "2019-03", "fin": "2019-10"}})
    assert r.status_code == 201 and r.json()["version"] == 2
    p = c.get("/api/perfil").json()["perfil"]
    assert p["actividades"][0]["descripcion"] == "Voluntariado"
    assert p["actividades"][0]["origen"]["fuente"] == "usuaria"
    assert c.get("/api/perfil/avisos").json()["huecos"] == []  # el voluntariado tapa el hueco
    r = c.patch("/api/perfil/datos", headers=h, json={"campo": "actividades", "indice": 0, "dato": {
        "descripcion": "Voluntariado en Cruz Roja", "inicio": "2019-03", "fin": "2019-10"}})
    assert r.json()["version"] == 3
    actividades = c.get("/api/perfil").json()["perfil"]["actividades"]
    assert actividades[0]["descripcion"] == "Voluntariado en Cruz Roja"
    assert c.patch("/api/perfil/datos", headers=h,
                   json={"campo": "actividades", "indice": 0}).json()["version"] == 4
    assert c.get("/api/perfil").json()["perfil"]["actividades"] == []


def test_una_actividad_con_rasgo_personal_se_guarda_como_periodo_cubierto(app, motor_app, motor_migrador):
    c, h = entrar(app)
    perfil_de(motor_app, uid(motor_migrador))
    r = c.patch("/api/perfil/datos", headers=h, json={"campo": "actividades", "dato": {
        "descripcion": "Baja por enfermedad", "inicio": "2019-03", "fin": "2019-10"}})
    assert r.status_code == 201
    assert r.json()["aviso"] == "Hemos quitado un dato personal que Horma no guarda."
    p = c.get("/api/perfil").json()["perfil"]
    assert p["actividades"] == [] and p["periodos_cubiertos"] == [{"inicio": "2019-03", "fin": "2019-10"}]
    assert "enfermedad" not in str(p).lower()
    assert c.get("/api/perfil/avisos").json()["huecos"] == []


# --- T13 ------------------------------------------------------------------------------------------------
def test_marcar_o_escribir_un_puesto_pone_origen_usuaria(app, motor_app, motor_migrador):
    c, h = entrar(app)
    u = uid(motor_migrador)
    with sesion_de(motor_app, u) as s:
        perfiles.aplicar_puestos_del_cv(s, u, [
            {"titulo": "Data Analyst", "dato": "Analista de datos", "marcado": True},
                                               {"titulo": "BI Analyst", "dato": "Excel", "marcado": True}])
    p = c.get("/api/preferencias").json()
    assert p["puestos"] == ["Data Analyst", "BI Analyst"] and p["origen"]["puestos"] == "cv"
    assert p["puestos_sugeridos"][0]["dato"] == "Analista de datos"
    p = c.put("/api/preferencias", headers=h, json={
        "puestos": ["Data Analyst", "  Business   Analyst "], "excluidos": ["prácticas", "prácticas"],
        "puestos_sugeridos": []}).json()
    assert p["puestos"] == ["Data Analyst", "Business Analyst"] and p["excluidos"] == ["prácticas"]
    assert p["origen"]["puestos"] == "usuaria"
    assert len(p["puestos_sugeridos"]) == 2  # los sugeridos no los reescribe ella
    assert c.put("/api/preferencias", headers=h, json={"excluidos": ["x" * 200]}).status_code == 422


def test_opciones_trae_los_sugeridos_con_su_dato_y_cuantas_ofertas_casan(app, motor_app, motor_migrador):
    c, _ = entrar(app)
    u = uid(motor_migrador)
    with motor_migrador.begin() as cx:
        cx.execute(text("insert into ofertas (texto_crudo, huella, titulo, titulo_norm, estado, fantasma, "
                        "fraude) values ('t', 'h', 'Senior Data Analyst', 'senior data analyst', "
                        "'procesada', false, false)"))
    with sesion_de(motor_app, u) as s:
        perfiles.aplicar_puestos_del_cv(s, u, [
            {"titulo": "Data Analyst", "dato": "Analista de datos", "marcado": True}])
    puestos = c.get("/api/preferencias/opciones").json()["puestos"]
    assert puestos[0]["valor"] == "Data Analyst" and puestos[0]["dato"] == "Analista de datos"
    assert puestos[0]["n"] == 1 and puestos[0]["marcado"] is True


def test_autocompletar_puestos_con_titulos_reales_de_las_ofertas(app, motor_migrador):
    c, _ = entrar(app)
    with motor_migrador.begin() as cx:
        for i, t in enumerate(["Senior Data Analyst", "Data Analyst", "Data Analyst", "Camarero"]):
            cx.execute(text("insert into ofertas (texto_crudo, huella, titulo, titulo_norm, estado, "
                            "fantasma, fraude) values ('t', :h, :t, lower(:t), 'procesada', false, false)"),
                       {"h": f"h{i}", "t": t})
    assert c.get("/api/preferencias/titulos", params={"q": "data"}).json()["titulos"] == [
        "Data Analyst", "Senior Data Analyst"]
    assert c.get("/api/preferencias/titulos", params={"q": "x"}).json()["titulos"] == []


def test_editar_una_experiencia_con_rasgo_personal_no_lo_guarda_y_avisa(app, motor_app, motor_migrador):
    """RF-11.25 / RT-09: el dato personal escrito a mano en una experiencia tampoco se guarda."""
    c, h = entrar(app)
    perfil_de(motor_app, uid(motor_migrador))
    antes = c.get("/api/perfil").json()["perfil"]["experiencias"][0]
    r = c.patch("/api/perfil/datos", headers=h, json={"campo": "experiencias", "indice": 0, "dato": {
        **{k: v for k, v in antes.items() if k != "origen"}, "descripcion": "Casada, con hijos"}})
    assert r.status_code in (200, 201)
    assert r.json()["aviso"] == "Hemos quitado un dato personal que Horma no guarda."
    p = c.get("/api/perfil").json()["perfil"]
    assert antes["puesto"] in [x["puesto"] for x in p["experiencias"]]
    assert "casada" not in str(p).lower() and "hijos" not in str(p).lower()


def test_una_experiencia_nueva_sin_rasgo_personal_no_avisa(app, motor_app, motor_migrador):
    c, h = entrar(app)
    perfil_de(motor_app, uid(motor_migrador))
    r = c.patch("/api/perfil/datos", headers=h, json={"campo": "experiencias", "dato": {
        "puesto": "Camarera", "empresa": "Bar Sol", "descripcion": "Sala y barra"}})
    assert r.status_code in (200, 201) and "aviso" not in r.json()
