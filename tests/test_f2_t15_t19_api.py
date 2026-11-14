"""Fase 2 · T15-T19: API de CV, perfil, preferencias, CV base y recomendaciones (sin llamar al modelo)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from horma import config
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.perfil import Perfil
from horma.web.db import sesion_de, sesion_sistema
from horma.web.main import crear_app
from horma.web.queue import worker
from horma.web.repositories import perfiles

pytestmark = pytest.mark.bd

MD = b"Ana Perez\nCamarera en Bar Sol, 2020-2023\nIngles B2\n"
TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior",
       "stack": []}


class IdentidadFalsa:
    async def redirigir(self, request, redirect_uri):
        from starlette.responses import RedirectResponse
        return RedirectResponse("https://accounts.google.test/auth")

    async def sub_desde_callback(self, request) -> str:
        return request.query_params["code"]


@pytest.fixture
def archivos(tmp_path, monkeypatch):
    monkeypatch.setenv("RUTA_ARCHIVOS", str(tmp_path / "archivos"))
    config.ajustes.cache_clear()
    yield tmp_path / "archivos"
    config.ajustes.cache_clear()


@pytest.fixture
def app(motor_app, bd_limpia, archivos):
    return crear_app(engine=motor_app, identidad=IdentidadFalsa())


@pytest.fixture
def cliente(app):
    with TestClient(app, follow_redirects=False) as c:
        yield c


def entrar(app, sub="google-A"):
    """Un cliente nuevo con su sesión. Devuelve (cliente, cabeceras CSRF, id de usuaria)."""
    c = TestClient(app, follow_redirects=False)
    assert c.get(f"/auth/google/callback?code={sub}").status_code == 302
    yo = c.get("/api/yo").json()
    return c, {"X-CSRF-Token": yo["csrf"]}, yo["usuaria_id"] if "usuaria_id" in yo else None


_ADMIN = {}


@pytest.fixture(autouse=True)
def _propietario(motor_migrador):
    """Conexión del propietario (salta la RLS) para mirar tablas de usuarias desde los tests."""
    _ADMIN["e"] = motor_migrador


def admin():
    return _ADMIN["e"].connect()


def _usuaria_id(motor, sub):
    with admin() as s:
        return s.execute(text("select id from usuarias where google_sub=:s"), {"s": sub}).scalar_one()


def subir(c, h, contenido=MD, nombre_archivo="cv.md", **datos):
    return c.post("/api/cv", headers=h, files={"archivo": (nombre_archivo, contenido)},
                  data={"clase": "fuente", **datos})


def _tareas(motor, tipo=None):
    with admin() as s:
        filas = s.execute(text("select tipo, usuaria_id, estado from tareas order by id")).all()
    return [f for f in filas if tipo is None or f.tipo == tipo]


def _perfil_hecho(motor, usuaria, **datos):
    """Una versión del perfil ya construida (como la deja el worker)."""
    base = {"taxonomia": TAX, "experiencias": [
        {"puesto": "Camarera", "empresa": "Bar Sol",
         "origen": {"fuente": "cv", "cv_id": 1, "fragmento": "Camarera en Bar Sol, 2020-2023"}}],
        "preguntas_pendientes": [{"campo": "idiomas", "motivo": "ambiguo",
                                  "pregunta": "¿Qué nivel de inglés tienes?"}], **datos}
    with sesion_de(motor, usuaria) as s:
        pid, version = perfiles.nueva_version(s, usuaria)
        perfiles.guardar_perfil(s, usuaria, pid, Perfil.model_validate({**base, "version": version}),
                                "# Ana\nCamarera en Bar Sol, 2020-2023")
    return pid, version


# --- T15: CV -----------------------------------------------------------------------------------
def test_sin_sesion_o_sin_csrf_no_se_sube_nada(app):
    anonimo = TestClient(app)
    assert subir(anonimo, {}).status_code == 401
    c, _, _ = entrar(app)
    assert subir(c, {}).status_code == 403


def test_subir_un_cv_lo_guarda_con_nombre_aleatorio_y_encola_perfilar(app, motor_app, archivos):
    c, h, _ = entrar(app)
    r = subir(c, h, nombre="CV hostelería")
    assert r.status_code == 201, r.text
    cv = r.json()
    assert cv["nombre"] == "CV hostelería" and cv["clase"] == "fuente" and cv["perfil_id"]
    guardados = list(archivos.iterdir())
    assert len(guardados) == 1 and guardados[0].name != "cv.md" and guardados[0].suffix == ".md"
    assert guardados[0].read_bytes() == MD
    t = _tareas(motor_app, "perfilar")
    assert len(t) == 1 and t[0].usuaria_id == _usuaria_id(motor_app, "google-A")
    with admin() as s:
        fila = s.execute(text("select texto, ruta from cv_archivos")).one()
        perfil = s.execute(text("select estado, version from perfiles")).one()
    assert "Camarera" in fila.texto and fila.ruta == guardados[0].name
    assert tuple(perfil) == ("pendiente", 1)


def test_sin_nombre_se_propone_el_del_archivo(app):
    c, h, _ = entrar(app)
    assert subir(c, h, nombre_archivo="mi-cv.md").json()["nombre"] == "mi-cv"


def test_tipo_no_admitido_se_rechaza_sin_guardar(app, motor_app, archivos):
    c, h, _ = entrar(app)
    assert subir(c, h, b"MZ\x90", "virus.exe").status_code == 415
    assert not archivos.exists() or not list(archivos.iterdir())
    assert _tareas(motor_app) == []


def test_un_pdf_que_no_lo_es_se_rechaza_por_sus_bytes(app, motor_app, archivos):
    c, h, _ = entrar(app)
    r = subir(c, h, b"esto no es un pdf", "cv.pdf")
    assert r.status_code == 422
    assert not archivos.exists() or not list(archivos.iterdir())
    with admin() as s:
        assert s.execute(text("select count(*) from cv_archivos")).scalar_one() == 0


def test_un_archivo_demasiado_grande_se_rechaza(app, monkeypatch, archivos):
    monkeypatch.setenv("MAX_CV_BYTES", "50")
    config.ajustes.cache_clear()
    c, h, _ = entrar(app)
    assert subir(c, h, b"x" * 200, "cv.md").status_code == 413
    assert not archivos.exists() or not list(archivos.iterdir())


def test_un_nombre_repetido_da_409_y_no_deja_archivo(app, archivos):
    c, h, _ = entrar(app)
    assert subir(c, h, nombre="Mi CV").status_code == 201
    assert subir(c, h, MD + b"otra linea\n", nombre="mi cv").status_code == 409
    assert len(list(archivos.iterdir())) == 1


def test_el_mismo_nombre_vale_para_otra_cuenta(app):
    a, ha, _ = entrar(app, "google-A")
    b, hb, _ = entrar(app, "google-B")
    assert subir(a, ha, nombre="Mi CV").status_code == 201
    assert subir(b, hb, nombre="Mi CV").status_code == 201


def test_la_descarga_es_solo_de_su_duena(app):
    a, ha, _ = entrar(app, "google-A")
    b, _, _ = entrar(app, "google-B")
    cv_id = subir(a, ha).json()["id"]
    r = a.get(f"/api/cv/{cv_id}/archivo")
    assert r.status_code == 200 and r.content == MD
    assert b.get(f"/api/cv/{cv_id}/archivo").status_code == 404
    assert TestClient(app).get(f"/api/cv/{cv_id}/archivo").status_code == 401


def test_el_cv_estetico_no_se_procesa(app, motor_app):
    c, h, _ = entrar(app)
    r = subir(c, h, b"%PDF-1.4 maquetado", "bonito.pdf", clase="estetico")
    assert r.status_code == 201 and r.json()["perfil_id"] is None
    assert _tareas(motor_app) == []
    with admin() as s:
        assert s.execute(text("select texto from cv_archivos")).scalar_one() is None
        assert s.execute(text("select count(*) from perfiles")).scalar_one() == 0


def test_listar_y_renombrar_un_cv(app):
    c, h, _ = entrar(app)
    a = subir(c, h, nombre="Uno").json()["id"]
    subir(c, h, MD + b"x\n", nombre="Dos")
    assert [x["nombre"] for x in c.get("/api/cv").json()] == ["Uno", "Dos"]
    assert c.patch(f"/api/cv/{a}", json={"nombre": "Tres"}, headers=h).status_code == 200
    assert c.patch(f"/api/cv/{a}", json={"nombre": "dos"}, headers=h).status_code == 409
    assert c.patch("/api/cv/999", json={"nombre": "x"}, headers=h).status_code == 404


# --- T16: perfil -------------------------------------------------------------------------------
def test_ver_el_perfil_con_origenes_y_pendientes(app, motor_app):
    c, h, _ = entrar(app)
    assert c.get("/api/perfil").json()["perfil"] is None
    _perfil_hecho(motor_app, _usuaria_id(motor_app, "google-A"))
    r = c.get("/api/perfil").json()
    assert r["perfil"]["version"] == 1 and r["perfil"]["experiencias"][0]["puesto"] == "Camarera"
    assert r["origenes"] == [{"campo": "experiencias.0", "fragmento": "Camarera en Bar Sol, 2020-2023"}]
    assert r["perfil"]["preguntas_pendientes"][0]["campo"] == "idiomas"


def test_responder_crea_version_nueva_conserva_la_anterior_y_marca_origen_usuaria(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    r = c.post("/api/perfil/respuestas", headers=h,
               json={"indice": 0, "dato": {"idioma": "en", "nivel": "B2"}})
    assert r.status_code == 201 and r.json()["version"] == 2
    nuevo = c.get("/api/perfil").json()
    assert nuevo["perfil"]["version"] == 2 and nuevo["perfil"]["preguntas_pendientes"] == []
    assert nuevo["perfil"]["idiomas"][0]["origen"]["fuente"] == "usuaria"
    with sesion_de(motor_app, u) as s:
        v1 = perfiles.perfil_modelo(perfiles.por_version(s, 1))
    assert len(v1.preguntas_pendientes) == 1 and v1.idiomas == []  # la anterior, intacta
    assert [t.tipo for t in _tareas(motor_app)] == ["clasificar_perfil"]


def test_corregir_un_dato_y_quitarlo(app, motor_app):
    c, h, _ = entrar(app)
    _perfil_hecho(motor_app, _usuaria_id(motor_app, "google-A"))
    r = c.patch("/api/perfil/datos", headers=h, json={
        "campo": "experiencias", "indice": 0, "dato": {"puesto": "Camarera de sala", "empresa": "Bar Sol"}})
    assert r.status_code == 201
    exp = c.get("/api/perfil").json()["perfil"]["experiencias"][0]
    assert exp["puesto"] == "Camarera de sala" and exp["origen"]["fuente"] == "usuaria"
    r = c.patch("/api/perfil/datos", headers=h, json={"campo": "experiencias", "indice": 0, "dato": None})
    assert r.json()["version"] == 3 and c.get("/api/perfil").json()["perfil"]["experiencias"] == []


def test_un_dato_que_no_cumple_el_esquema_o_sin_perfil_se_rechaza(app, motor_app):
    c, h, _ = entrar(app)
    cuerpo = {"campo": "idiomas", "indice": None, "dato": {"idioma": "klingon"}}
    assert c.patch("/api/perfil/datos", headers=h, json=cuerpo).status_code == 409  # sin perfil
    _perfil_hecho(motor_app, _usuaria_id(motor_app, "google-A"))
    assert c.post("/api/perfil/respuestas", headers=h,
                  json={"indice": 0, "dato": {"idioma": "klingon"}}).status_code == 422
    assert c.post("/api/perfil/respuestas", headers=h, json={"indice": 7}).status_code == 422
    assert c.get("/api/perfil").json()["perfil"]["version"] == 1  # nada se guardó


def test_el_perfil_de_otra_usuaria_no_se_ve_ni_se_toca(app, motor_app):
    a, ha, _ = entrar(app, "google-A")
    b, hb, _ = entrar(app, "google-B")
    _perfil_hecho(motor_app, _usuaria_id(motor_app, "google-A"))
    assert b.get("/api/perfil").json()["perfil"] is None
    assert b.post("/api/perfil/respuestas", headers=hb, json={"indice": 0}).status_code == 409
    assert a.get("/api/perfil").json()["perfil"]["version"] == 1


# --- T17: preferencias -------------------------------------------------------------------------
def _oferta(motor, **campos):
    base = {"titulo": "Camarera", "sector": "hosteleria_turismo", "familia": "hosteleria_restauracion",
            "nivel": "junior", "fantasma": False, "fraude": False, "salario_publicado": False,
            "pais": "ES", "tipo_contrato": "indefinido", "idiomas_norm": ["es"]}
    base.update(campos)
    columnas, marcas = ", ".join(base), ", ".join(
        f"cast(:{k} as text[])" if k == "idiomas_norm" else f":{k}" for k in base)
    with sesion_sistema(motor) as s:
        return s.execute(text(f"insert into ofertas (texto_crudo, estado, {columnas}) "
                              f"values ('t', 'procesada', {marcas}) returning id"), base).scalar_one()


def test_preferencias_vacias_por_defecto_y_se_guardan(app):
    c, h, _ = entrar(app)
    p = c.get("/api/preferencias").json()
    assert p["familias"] == [] and p["rango_min"] == 40 and p["rango_max"] == 100
    r = c.put("/api/preferencias", headers=h, json={**p, "contratos": ["indefinido"],
                                                    "sueldo_minimo": 18000, "solo_remoto": True})
    assert r.status_code == 200
    g = c.get("/api/preferencias").json()
    assert g["contratos"] == ["indefinido"] and g["sueldo_minimo"] == 18000 and g["solo_remoto"] is True
    assert g["origen"] == {"contratos": "usuaria", "sueldo_minimo": "usuaria", "solo_remoto": "usuaria"}


def test_las_preferencias_del_cv_llegan_marcadas_y_las_de_ella_no_se_pisan(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    with sesion_de(motor_app, u) as s:
        perfiles.aplicar_preferencias_del_cv(s, u, perfiles.Preferencias(
            familias=["hosteleria_restauracion"], origen={"familias": "cv"}))
    p = c.get("/api/preferencias").json()
    assert p["familias"] == ["hosteleria_restauracion"] and p["origen"]["familias"] == "cv"
    c.put("/api/preferencias", headers=h, json={**p, "familias": ["ventas_comercial"]})
    assert c.get("/api/preferencias").json()["origen"]["familias"] == "usuaria"


def test_preferencias_invalidas_se_rechazan(app):
    c, h, _ = entrar(app)
    p = c.get("/api/preferencias").json()
    assert c.put("/api/preferencias", headers=h, json={**p, "paises": ["XX"]}).status_code == 422
    invertido = {**p, "rango_min": 90, "rango_max": 10}
    assert c.put("/api/preferencias", headers=h, json=invertido).status_code == 422
    assert c.put("/api/preferencias", json=p).status_code == 403


def test_los_contadores_de_las_casillas_coinciden_con_el_catalogo(app, motor_app):
    c, _, _ = entrar(app)
    _oferta(motor_app)
    _oferta(motor_app, pais="DE", tipo_contrato="temporal", idiomas_norm=["en", "de"], familia="legal")
    _oferta(motor_app, fantasma=True)  # no recomendable: no cuenta
    _oferta(motor_app, pais=None, tipo_contrato=None, idiomas_norm=[])
    o = c.get("/api/preferencias/opciones").json()
    cuenta = {g: {x["valor"]: x["n"] for x in v} for g, v in o["grupos"].items()}
    assert o["total"] == 3
    assert cuenta["paises"]["ES"] == 1 and cuenta["paises"]["DE"] == 1 and cuenta["paises"]["FR"] == 0
    assert cuenta["contratos"]["indefinido"] == 1 and cuenta["contratos"]["temporal"] == 1
    assert cuenta["familias"]["hosteleria_restauracion"] == 2 and cuenta["familias"]["legal"] == 1
    assert cuenta["idiomas"]["es"] == 1 and cuenta["idiomas"]["de"] == 1 and cuenta["idiomas"]["en"] == 1


# --- T18: CV base ------------------------------------------------------------------------------
def test_los_cv_base_se_generan_a_peticion_y_no_por_si_solos(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    assert c.post("/api/cv-base", headers=h).status_code == 409  # sin perfil
    _perfil_hecho(motor_app, u)
    assert _tareas(motor_app) == []  # tener perfil no genera nada
    r = c.post("/api/cv-base", headers=h)
    assert r.status_code == 202 and r.json()["perfil_version"] == 1
    assert [t.tipo for t in _tareas(motor_app)] == ["generar_cv_base"]
    assert c.post("/api/cv-base", headers=h).status_code == 409  # ya en curso
    assert c.get("/api/cv-base").json()["generando"] is True


def test_cv_base_listado_renombrado_y_rechazados_ocultos(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    pid, _ = _perfil_hecho(motor_app, u)
    with sesion_de(motor_app, u) as s:
        perfiles.guardar_cv_base(s, u, 1, {
            "guardados": [{"destino": {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion"},
                           "contenido": "## Experiencia\nCamarera", "traza": [], "intentos": 1}],
            "rechazados": [{"destino": {"sector": "tecnologia", "familia": "desarrollo_software"},
                            "motivo": "Dato sin origen", "errores": ["Dato sin origen"]}]})
    r = c.get("/api/cv-base").json()
    assert [x["familia"] for x in r["cv_base"]] == ["hosteleria_restauracion"]  # el rechazado no aparece
    assert r["cv_base"][0]["desfasado"] is False
    assert r["avisos"] == [{"nombre": "CV base · desarrollo_software · tecnologia · v1",
                            "estado": "rechazado", "motivo": "Dato sin origen", "perfil_version": 1}]
    cv_id = r["cv_base"][0]["id"]
    assert c.patch(f"/api/cv-base/{cv_id}", headers=h, json={"nombre": "CV hostelería"}).status_code == 200
    assert c.get("/api/cv-base").json()["cv_base"][0]["nombre"] == "CV hostelería"
    subir(c, h, nombre="Otro")
    assert c.patch(f"/api/cv-base/{cv_id}", headers=h, json={"nombre": "otro"}).status_code == 409
    assert pid  # el CV base ya generado de esta versión impide generarlo otra vez
    assert c.post("/api/cv-base", headers=h).status_code == 409


def test_al_cambiar_el_perfil_los_cv_base_salen_desfasados_sin_regenerarse(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    with sesion_de(motor_app, u) as s:
        perfiles.guardar_cv_base(s, u, 1, {"guardados": [{
            "destino": {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion"},
            "contenido": "x", "traza": [], "intentos": 1}], "rechazados": []})
    c.post("/api/perfil/respuestas", headers=h, json={"indice": 0})
    assert c.get("/api/cv-base").json()["cv_base"][0]["desfasado"] is True
    assert "generar_cv_base" not in [t.tipo for t in _tareas(motor_app)]


# --- T19: recomendaciones ----------------------------------------------------------------------
def _match(oferta, version, nota, condiciones="medio", explicacion="Una frase. Dos frases."):
    return {"oferta_id": oferta, "nota": nota, "condiciones": condiciones, "explicacion": explicacion,
            "cita_perfil": "Camarera en Bar Sol", "cita_oferta": "camarera", "retirada": False}


def _puntuar(motor, usuaria, version, *notas):
    from horma.web.repositories import matches
    with sesion_de(motor, usuaria) as s:
        matches.guardar(s, usuaria, version, [_match(o, version, n) for o, n in notas])


def test_recomendar_encola_y_solo_se_pide_a_mano(app, motor_app):
    c, h, _ = entrar(app)
    assert c.post("/api/recomendar", headers=h).status_code == 409
    _perfil_hecho(motor_app, _usuaria_id(motor_app, "google-A"))
    r = c.post("/api/recomendar", headers=h)
    assert r.status_code == 202 and [t.tipo for t in _tareas(motor_app)] == ["recomendar"]
    assert c.post("/api/recomendar", headers=h).status_code == 409


def test_filtrar_u_ordenar_no_llama_al_modelo_ni_encola(app, motor_app, monkeypatch):
    def prohibido(**_):
        raise AssertionError("no se debe llamar al modelo al filtrar")
    monkeypatch.setattr("horma.agents.base.completar", prohibido)
    c, _, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    a, b = _oferta(motor_app, titulo="A"), _oferta(motor_app, titulo="B", pais="DE")
    _puntuar(motor_app, u, 1, (a, 70), (b, 90))
    for consulta in ("", "?orden=recientes", "?paises=ES", "?rango=0-100&solo_remoto=true",
                     "?contratos=indefinido&sueldo_minimo=1000"):
        assert c.get("/api/recomendaciones" + consulta).status_code == 200
    assert _tareas(motor_app) == []


def test_lo_puntuado_se_ordena_por_nota_y_lo_nuevo_sale_sin_puntuar(app, motor_app):
    c, _, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    a, b, nueva = (_oferta(motor_app, titulo=t) for t in ("A", "B", "Nueva"))
    _puntuar(motor_app, u, 1, (a, 60), (b, 85))
    r = c.get("/api/recomendaciones").json()
    assert [(x["titulo"], x["nota"], x["sin_puntuar"]) for x in r["recomendaciones"]] == [
        ("B", 85, False), ("A", 60, False), ("Nueva", None, True)]
    assert r["rango"] == [40, 100] and r["sin_puntuar"] == 1 and r["total"] == 3


def test_el_rango_por_defecto_es_40_100_y_se_puede_cambiar(app, motor_app):
    c, _, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    baja, alta = _oferta(motor_app, titulo="Baja"), _oferta(motor_app, titulo="Alta")
    _puntuar(motor_app, u, 1, (baja, 20), (alta, 80))
    assert [x["titulo"] for x in c.get("/api/recomendaciones").json()["recomendaciones"]] == ["Alta"]
    todas = c.get("/api/recomendaciones?rango=0-100").json()["recomendaciones"]
    assert {x["titulo"] for x in todas} == {"Baja", "Alta"}
    assert c.get("/api/recomendaciones?rango=100-0").status_code == 422
    assert c.get("/api/recomendaciones?rango=abc").status_code == 422


def test_los_filtros_de_la_url_y_los_guardados_descartan_ofertas(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    es, de = _oferta(motor_app, titulo="ES"), _oferta(motor_app, titulo="DE", pais="DE")
    _oferta(motor_app, titulo="Fantasma", fantasma=True)
    _puntuar(motor_app, u, 1, (es, 70), (de, 70))
    nombres = lambda q: {x["titulo"] for x in c.get("/api/recomendaciones" + q).json()["recomendaciones"]}  # noqa: E731
    assert nombres("") == {"ES", "DE"} and nombres("?paises=ES") == {"ES"}
    p = c.get("/api/preferencias").json()
    c.put("/api/preferencias", headers=h, json={**p, "paises": ["DE"]})
    assert nombres("") == {"DE"}  # sin parámetros, mandan las preferencias guardadas
    assert c.get("/api/recomendaciones?paises=XX").status_code == 422


def test_el_salario_se_ve_como_en_la_oferta(app, motor_app):
    c, _, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    a = _oferta(motor_app, salario_rango="2.000 €/mes brutos")
    b = _oferta(motor_app, salario_minimo=18000, salario_maximo=22000, salario_moneda="EUR")
    _puntuar(motor_app, u, 1, (a, 70), (b, 60))
    sal = {x["id"]: x["salario"] for x in c.get("/api/recomendaciones").json()["recomendaciones"]}
    assert sal == {a: "2.000 €/mes brutos", b: "18000 - 22000 EUR"}


def test_una_nota_de_una_version_anterior_sale_desfasada(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    a = _oferta(motor_app)
    _puntuar(motor_app, u, 1, (a, 70))
    assert c.get("/api/recomendaciones").json()["recomendaciones"][0]["desfasado"] is False
    c.post("/api/perfil/respuestas", headers=h, json={"indice": 0})
    r = c.get("/api/recomendaciones").json()["recomendaciones"][0]
    assert r["desfasado"] is True and r["nota"] == 70  # se sigue viendo, pero avisa


def test_corregir_una_explicacion_la_guarda_y_se_exporta_sin_entrar_al_repo(app, motor_app, tmp_path):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    a = _oferta(motor_app, titulo="Camarera")
    assert c.post(f"/api/matches/{a}/correccion", headers=h,
                  json={"nota": 50, "comentario": "Pide inglés."}).status_code == 404  # sin nota aún
    _puntuar(motor_app, u, 1, (a, 90))
    assert c.get(f"/api/matches/{a}/exportar").status_code == 404  # sin corrección
    r = c.post(f"/api/matches/{a}/correccion", headers=h, json={"nota": 50, "comentario": "Pide inglés."})
    assert r.status_code == 200
    caso = c.get(f"/api/matches/{a}/exportar").json()
    assert caso["esperado"] == {"nota": 50, "condiciones": "medio", "motivo": "Pide inglés."}
    assert caso["modelo"]["nota"] == 90 and caso["entrada"]["oferta"]["titulo"] == "Camarera"
    assert caso["entrada"]["perfil"]["experiencias"][0]["puesto"] == "Camarera"
    assert c.post(f"/api/matches/{a}/correccion", headers=h, json={"comentario": ""}).status_code == 422
    from pathlib import Path
    assert not any("Pide inglés" in p.read_text("utf-8") for p in Path("evals/recomendacion").rglob("*.json"))


def test_una_usuaria_no_ve_ni_corrige_las_notas_de_otra(app, motor_app):
    a, ha, _ = entrar(app, "google-A")
    b, hb, _ = entrar(app, "google-B")
    ua = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, ua)
    oferta = _oferta(motor_app)
    _puntuar(motor_app, ua, 1, (oferta, 80))
    assert b.get("/api/recomendaciones").json()["recomendaciones"][0]["nota"] is None
    assert b.post(f"/api/matches/{oferta}/correccion", headers=hb,
                  json={"comentario": "x"}).status_code == 404
    assert a.get("/api/recomendaciones").json()["recomendaciones"][0]["nota"] == 80


def test_de_la_subida_al_perfil_y_la_recomendacion_con_el_worker(app, motor_app):
    """Recorrido completo con la puerta simulada: subir CV → perfilar → recomendar → ver."""
    c, h, _ = entrar(app)
    cv = subir(c, h).json()
    extraccion = {"perfil": {"experiencias": [{
        "puesto": "Camarera", "empresa": "Bar Sol",
        "origen": {"fuente": "cv", "cv_id": cv["id"], "fragmento": "Camarera en Bar Sol, 2020-2023"}}]},
        "cv_maestro": "# Ana\nCamarera en Bar Sol, 2020-2023"}
    assert worker.procesar_una(motor_app, ProveedorSimulado([extraccion, TAX])) == "hecha"
    assert c.get("/api/perfil").json()["perfil"]["experiencias"][0]["puesto"] == "Camarera"
    assert c.get("/api/preferencias").json()["familias"] == ["hosteleria_restauracion"]
    oferta = _oferta(motor_app, titulo="Camarera de sala")
    assert c.post("/api/recomendar", headers=h).status_code == 202
    match = {"oferta_id": oferta, "nota": 88, "condiciones": "alto", "cita_perfil": "Camarera en Bar Sol",
             "cita_oferta": "camarera", "explicacion": "Tiene experiencia en sala. La oferta pide camarera."}
    assert worker.procesar_una(motor_app, ProveedorSimulado([{"matches": [match]}])) == "hecha"
    r = c.get("/api/recomendaciones").json()["recomendaciones"]
    assert [(x["titulo"], x["nota"]) for x in r] == [("Camarera de sala", 88)]
