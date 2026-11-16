"""Fase 3 · T14-T17: API de candidaturas, historial del CV base, descargas en PDF y respuesta de la
empresa (sin llamar al modelo salvo `clasificar_respuesta`, con la puerta simulada)."""
import io
import json

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import text

from horma import config
from horma.llm.simulado import ProveedorSimulado
from horma.web.db import sesion_de, sesion_sistema
from horma.web.main import crear_app
from horma.web.queue import worker

pytestmark = pytest.mark.bd

MAESTRO = "# Ana Pérez\n\n## Experiencia\nCamarera en Bar Sol, 2020-2023\nManejo de TPV\n"
BASE = "## Experiencia\nCamarera en Bar Sol, 2020-2023\nManejo de TPV"
CV = "## Experiencia\nCamarera en Bar Sol, 2020-2023\nManejo de TPV"
CARTA = "Hola equipo,\nTrabajé en Bar Sol desde 2020.\nUn saludo"
TRAZA_CV = [{"frase": "Camarera en Bar Sol, 2020-2023", "fragmento": "Camarera en Bar Sol, 2020-2023"},
            {"frase": "Manejo de TPV", "fragmento": "Manejo de TPV"}]
TRAZA_CARTA = [{"frase": "Trabajé en Bar Sol desde 2020.", "fragmento": "Camarera en Bar Sol, 2020-2023"}]


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


def entrar(app, sub="google-A"):
    """Un cliente con su sesión. Devuelve (cliente, cabeceras CSRF, id de usuaria)."""
    c = TestClient(app, follow_redirects=False)
    assert c.get(f"/auth/google/callback?code={sub}").status_code == 302
    yo = c.get("/api/yo").json()
    return c, {"X-CSRF-Token": yo["csrf"]}, yo["usuaria_id"]


def _oferta(motor, titulo="Camarera"):
    with sesion_sistema(motor) as s:
        return s.execute(text(
            "insert into ofertas (texto_crudo, estado, titulo, empresa, requisitos, sector, familia, nivel) "
            "values ('texto', 'procesada', :t, 'Bar Luna', cast('[\"inglés\"]' as jsonb), "
            "'hosteleria_turismo', 'hosteleria_restauracion', 'junior') returning id"),
            {"t": titulo}).scalar_one()


def _perfil(motor, u, version=1):
    with sesion_de(motor, u) as s:
        s.execute(text("insert into perfiles (usuaria_id, version, estado, cv_maestro) "
                       "values (:u, :v, 'hecha', :m)"), {"u": u, "v": version, "m": MAESTRO})


def _cv_base(motor, u, nombre="CV hostelería", perfil_version=1, contenido=BASE):
    with sesion_de(motor, u) as s:
        return s.execute(text(
            "insert into cv_base (usuaria_id, perfil_version, nombre, sector, familia, contenido) "
            "values (:u, :v, :n, 'hosteleria_turismo', 'hosteleria_restauracion', :c) returning id"),
            {"u": u, "v": perfil_version, "n": nombre, "c": contenido}).scalar_one()


def _candidatura(motor, u, oferta_id, cv_base_id=None, **extra):
    """Una candidatura ya preparada (como la deja el worker)."""
    campos = {"usuaria_id": u, "oferta_id": oferta_id, "cv_base_id": cv_base_id, "perfil_version": 1,
              "cv_base_motivo": "Es tu único CV base válido.", "preparacion": "lista",
              "cv_contenido": CV, "carta_contenido": CARTA, "cv_traza": TRAZA_CV,
              "carta_traza": TRAZA_CARTA, **extra}
    jsonb = {"cv_traza", "carta_traza", "avisos", "huecos"}
    columnas = ", ".join(campos)
    marcas = ", ".join(f"cast(:{k} as jsonb)" if k in jsonb else f":{k}" for k in campos)
    valores = {k: json.dumps(v) if k in jsonb else v for k, v in campos.items()}
    with sesion_de(motor, u) as s:
        return s.execute(text(f"insert into candidaturas ({columnas}) values ({marcas}) returning id"),
                         valores).scalar_one()


def _escenario(app, motor, sub="google-A", **extra):
    c, h, u = entrar(app, sub)
    _perfil(motor, u)
    cb = _cv_base(motor, u)
    oferta = _oferta(motor)
    cid = _candidatura(motor, u, oferta, cb, **extra)
    return c, h, u, cb, oferta, cid


def _fila(motor, u, cid):
    with sesion_de(motor, u) as s:
        return s.execute(text("select * from candidaturas where id = :i"), {"i": cid}).mappings().one()


def _eventos(motor, u, cid):
    with sesion_de(motor, u) as s:
        return [dict(f) for f in s.execute(text(
            "select de, a, motivo, canal, origen, tipo, etiqueta_respuesta from candidatura_eventos "
            "where candidatura_id = :i order by id"), {"i": cid}).mappings()]


# --- T14: crear, listar y detalle --------------------------------------------------------------
def test_sin_sesion_o_sin_csrf_no_se_crea_nada(app):
    assert TestClient(app).post("/api/candidaturas", json={"oferta_id": 1}).status_code == 401
    c, _, _ = entrar(app)
    assert c.post("/api/candidaturas", json={"oferta_id": 1}).status_code == 403


def test_crear_con_solo_la_oferta_encola_la_tarea(app, motor_app):
    c, h, u = entrar(app)
    _perfil(motor_app, u)
    _cv_base(motor_app, u)
    oferta = _oferta(motor_app)
    r = c.post("/api/candidaturas", headers=h, json={"oferta_id": oferta})
    assert r.status_code == 202, r.text
    cid, tarea = r.json()["id"], r.json()["tarea_id"]
    f = _fila(motor_app, u, cid)
    assert f["estado"] == "borrador" and f["preparacion"] == "en_curso" and f["oferta_id"] == oferta
    with sesion_de(motor_app, u) as s:
        t = s.execute(text("select tipo, entidad_id, tope_coste from tareas where id = :i"),
                      {"i": tarea}).one()
    assert t.tipo == "candidatura" and t.entidad_id == cid and float(t.tope_coste) == 1.0


def test_sin_cv_base_valido_pide_generarlo(app, motor_app):
    c, h, u = entrar(app)
    _perfil(motor_app, u)
    oferta = _oferta(motor_app)
    r = c.post("/api/candidaturas", headers=h, json={"oferta_id": oferta})
    assert r.status_code == 409 and "CV base" in r.json()["detail"]
    with sesion_de(motor_app, u) as s:
        s.execute(text("insert into cv_base (usuaria_id, perfil_version, nombre, estado, motivo_error) "
                       "values (:u, 1, 'malo', 'rechazado', 'x')"), {"u": u})
    assert c.post("/api/candidaturas", headers=h, json={"oferta_id": oferta}).status_code == 409


def test_sin_perfil_o_con_oferta_inexistente(app, motor_app):
    c, h, u = entrar(app)
    oferta = _oferta(motor_app)
    assert c.post("/api/candidaturas", headers=h, json={"oferta_id": oferta}).status_code == 409
    _perfil(motor_app, u)
    _cv_base(motor_app, u)
    assert c.post("/api/candidaturas", headers=h, json={"oferta_id": 9999}).status_code == 404


def test_una_segunda_candidatura_viva_para_la_misma_oferta_es_409(app, motor_app):
    c, h, u = entrar(app)
    _perfil(motor_app, u)
    _cv_base(motor_app, u)
    oferta = _oferta(motor_app)
    primera = c.post("/api/candidaturas", headers=h, json={"oferta_id": oferta}).json()["id"]
    assert c.post("/api/candidaturas", headers=h, json={"oferta_id": oferta}).status_code == 409
    assert c.post(f"/api/candidaturas/{primera}/cerrar", headers=h,
                  json={"motivo": "descartada"}).status_code == 200
    assert c.post("/api/candidaturas", headers=h, json={"oferta_id": oferta}).status_code == 409  # avisa
    otra = c.post("/api/candidaturas", headers=h, json={"oferta_id": oferta, "repetir": True})
    assert otra.status_code == 202


def test_el_detalle_muestra_cv_base_motivo_y_aviso_de_desfase(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app, avisos=["otro aviso"])
    d = c.get(f"/api/candidaturas/{cid}").json()
    assert d["cv_base"] == {"id": cb, "nombre": "CV hostelería", "desfasado": False}
    assert d["cv_base_motivo"] == "Es tu único CV base válido." and d["oferta"]["titulo"] == "Camarera"
    assert d["cv_contenido"] == CV and d["carta_contenido"] == CARTA and d["eventos"] == []
    assert "respuesta_pendiente" not in d
    _perfil(motor_app, u, version=2)  # el perfil avanza: el CV base queda desfasado
    assert c.get(f"/api/candidaturas/{cid}").json()["cv_base"]["desfasado"] is True


def test_el_detalle_de_otra_usuaria_no_existe(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    otra, _, _ = entrar(app, "google-B")
    assert otra.get(f"/api/candidaturas/{cid}").status_code == 404
    assert otra.get("/api/candidaturas").json()["total"] == 0


def test_el_tablero_sale_agrupado_por_estado(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app, preparacion="pendiente_de_ti")
    _candidatura(motor_app, u, _oferta(motor_app, "Cocinera"), cb, estado="enviada")
    t = c.get("/api/candidaturas").json()
    assert t["total"] == 2
    assert [x["estado"] for x in t["columnas"]] == ["borrador", "aprobada", "enviada", "entrevista",
                                                    "cerrada"]
    por = {x["estado"]: x["candidaturas"] for x in t["columnas"]}
    assert len(por["borrador"]) == 1 and len(por["enviada"]) == 1 and por["aprobada"] == []
    tarjeta = por["borrador"][0]
    assert tarjeta["titulo"] == "Camarera" and tarjeta["empresa"] == "Bar Luna"
    assert tarjeta["te_toca_revisar"] is True and por["enviada"][0]["te_toca_revisar"] is False
    assert tarjeta["actualizado_en"]


# --- T15: editar, guardar encima del CV base, versiones, aprobar y transiciones ----------------
def test_editar_en_borrador_no_llama_al_modelo_y_recalcula_los_avisos(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    nuevo = CV + "\nDirigí un equipo de 30 personas"
    r = c.patch(f"/api/candidaturas/{cid}", headers=h, json={"cv_contenido": nuevo})
    assert r.status_code == 200, r.text
    assert any("Dirigí" in a for a in r.json()["avisos"]) and r.json()["preparacion"] == "pendiente_de_ti"
    assert _fila(motor_app, u, cid)["cv_contenido"] == nuevo
    r = c.patch(f"/api/candidaturas/{cid}", headers=h, json={"cv_contenido": CV})
    assert r.json()["avisos"] == [] and r.json()["preparacion"] == "lista"
    with sesion_de(motor_app, u) as s:
        assert s.execute(text("select count(*) from tareas")).scalar_one() == 0


def test_editar_pide_un_cambio_y_no_vale_fuera_de_borrador_ni_en_curso(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    assert c.patch(f"/api/candidaturas/{cid}", headers=h, json={}).status_code == 422
    en_curso = _candidatura(motor_app, u, _oferta(motor_app, "Otra"), cb, preparacion="en_curso")
    r = c.patch(f"/api/candidaturas/{en_curso}", headers=h, json={"carta_contenido": "x"})
    assert r.status_code == 409
    c.post(f"/api/candidaturas/{cid}/aprobar", headers=h,
           json={"documento": "adaptado", "avisos_revisados": True})
    assert c.patch(f"/api/candidaturas/{cid}", headers=h, json={"carta_contenido": "x"}).status_code == 409


def test_guardar_como_mi_cv_base_sobrescribe_y_guarda_la_version_anterior(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app, cv_contenido=CV + "\nIngles B2")
    r = c.post(f"/api/candidaturas/{cid}/guardar-cv-base", headers=h, json={"nombre": "Mi CV de sala"})
    assert r.status_code == 200, r.text
    with sesion_de(motor_app, u) as s:
        base = s.execute(text("select nombre, contenido from cv_base where id = :i"), {"i": cb}).one()
        v = s.execute(text("select nombre, contenido, origen, candidatura_id from cv_base_versiones "
                           "where cv_base_id = :i"), {"i": cb}).all()
    assert base.nombre == "Mi CV de sala" and base.contenido == CV + "\nIngles B2"
    assert len(v) == 1 and (v[0].nombre, v[0].contenido, v[0].origen, v[0].candidatura_id) == (
        "CV hostelería", BASE, "candidatura", cid)
    assert [e["tipo"] for e in _eventos(motor_app, u, cid)] == ["cv_base_guardado"]


def test_guardar_encima_rechaza_nombre_repetido_otro_estado_y_otra_usuaria(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    _cv_base(motor_app, u, nombre="Otro CV")
    assert c.post(f"/api/candidaturas/{cid}/guardar-cv-base", headers=h,
                  json={"nombre": "otro cv"}).status_code == 409
    otra, h2, _ = entrar(app, "google-B")
    assert otra.post(f"/api/candidaturas/{cid}/guardar-cv-base", headers=h2,
                     json={"nombre": "Mío"}).status_code == 404
    c.post(f"/api/candidaturas/{cid}/aprobar", headers=h, json={"documento": "adaptado",
                                                                "avisos_revisados": True})
    assert c.post(f"/api/candidaturas/{cid}/guardar-cv-base", headers=h,
                  json={"nombre": "Nuevo"}).status_code == 409


def test_una_candidatura_nueva_parte_del_cv_base_guardado(app, motor_app):
    from horma.web.repositories import candidaturas as repo
    c, h, u, cb, oferta, cid = _escenario(app, motor_app, cv_contenido=CV + "\nIngles B2")
    c.post(f"/api/candidaturas/{cid}/guardar-cv-base", headers=h, json={"nombre": "Mi CV de sala"})
    with sesion_de(motor_app, u) as s:
        assert repo.cv_base_para_flujo(s)[0]["contenido"] == CV + "\nIngles B2"


def test_el_historial_recoge_ediciones_manuales_y_se_puede_restaurar(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    assert c.patch(f"/api/cv-base/{cb}", headers=h,
                   json={"contenido": BASE + "\nIngles B2"}).status_code == 200
    assert c.patch(f"/api/cv-base/{cb}", headers=h,
                   json={"contenido": BASE + "\nIngles B2\nCarné B"}).status_code == 200
    v = c.get(f"/api/cv-base/{cb}/versiones").json()["versiones"]
    assert len(v) == 2 and v[0]["origen"] == "edicion" and v[0]["nombre"] == "CV hostelería"
    marcas = {(x["marca"], x["linea"]) for x in v[0]["lineas"]}  # la más reciente, frente a la actual
    assert ("añadida", "Carné B") in marcas
    assert ("añadida", "Ingles B2") in {(x["marca"], x["linea"]) for x in v[1]["lineas"]}
    r = c.post(f"/api/cv-base/{cb}/versiones/{v[1]['id']}/restaurar", headers=h)
    assert r.status_code == 200, r.text
    with sesion_de(motor_app, u) as s:
        assert s.execute(text("select contenido from cv_base where id = :i"), {"i": cb}).scalar_one() == BASE
        guardadas = s.execute(text("select contenido, origen from cv_base_versiones where cv_base_id = :i "
                                   "order by id"), {"i": cb}).all()
    assert len(guardadas) == 3 and guardadas[-1].contenido == BASE + "\nIngles B2\nCarné B"
    assert guardadas[-1].origen == "restauracion"


def test_cambiar_solo_el_nombre_o_nada_no_ensucia_el_historial(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    c.patch(f"/api/cv-base/{cb}", headers=h, json={"contenido": BASE})  # igual: nada cambia
    assert c.get(f"/api/cv-base/{cb}/versiones").json()["versiones"] == []


def test_otra_usuaria_no_ve_ni_restaura_versiones(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    c.patch(f"/api/cv-base/{cb}", headers=h, json={"contenido": "otro texto"})
    vid = c.get(f"/api/cv-base/{cb}/versiones").json()["versiones"][0]["id"]
    otra, h2, _ = entrar(app, "google-B")
    assert otra.get(f"/api/cv-base/{cb}/versiones").status_code == 404
    assert otra.post(f"/api/cv-base/{cb}/versiones/{vid}/restaurar", headers=h2).status_code == 404


def test_aprobar_con_avisos_sin_revisarlos_es_400(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app, avisos=["El CV base es de otra versión"])
    cuerpo = {"documento": "adaptado", "avisos_revisados": False}
    assert c.post(f"/api/candidaturas/{cid}/aprobar", headers=h, json=cuerpo).status_code == 400
    assert _fila(motor_app, u, cid)["estado"] == "borrador"
    assert c.post(f"/api/candidaturas/{cid}/aprobar", headers=h,
                  json={**cuerpo, "avisos_revisados": True}).status_code == 200
    f = _fila(motor_app, u, cid)
    assert f["estado"] == "aprobada" and f["documento"] == "adaptado"
    assert _eventos(motor_app, u, cid)[-1]["a"] == "aprobada"


def test_una_preparacion_pendiente_de_ti_tambien_pide_revisar(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app, preparacion="pendiente_de_ti")
    cuerpo = {"documento": "adaptado", "avisos_revisados": False}
    assert c.post(f"/api/candidaturas/{cid}/aprobar", headers=h, json=cuerpo).status_code == 400


def test_no_se_aprueba_lo_que_se_esta_preparando_ni_lo_de_otra(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    en_curso = _candidatura(motor_app, u, _oferta(motor_app, "Otra"), cb, preparacion="en_curso")
    cuerpo = {"documento": "adaptado", "avisos_revisados": True}
    assert c.post(f"/api/candidaturas/{en_curso}/aprobar", headers=h, json=cuerpo).status_code == 409
    otra, h2, _ = entrar(app, "google-B")
    assert otra.post(f"/api/candidaturas/{cid}/aprobar", headers=h2, json=cuerpo).status_code == 404
    assert _fila(motor_app, u, cid)["estado"] == "borrador"


def test_aprobar_con_el_estetico_pide_uno_propio(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    cuerpo = {"documento": "estetico", "avisos_revisados": True}
    assert c.post(f"/api/candidaturas/{cid}/aprobar", headers=h, json=cuerpo).status_code == 422
    fuente = c.post("/api/cv", headers=h, files={"archivo": ("a.md", b"# Ana\nCamarera")},
                    data={"clase": "fuente"}).json()["id"]
    assert c.post(f"/api/candidaturas/{cid}/aprobar", headers=h,
                  json={**cuerpo, "cv_estetico_id": fuente}).status_code == 422  # no es un estético
    est = c.post("/api/cv", headers=h, files={"archivo": ("b.md", b"# Ana")},
                 data={"clase": "estetico"}).json()["id"]
    assert c.post(f"/api/candidaturas/{cid}/aprobar", headers=h,
                  json={**cuerpo, "cv_estetico_id": est}).status_code == 200
    assert _fila(motor_app, u, cid)["cv_estetico_id"] == est


def test_las_transiciones_dejan_un_evento_cada_una(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    ruta = f"/api/candidaturas/{cid}"
    assert c.post(f"{ruta}/enviada", headers=h,
                  json={"fecha": "2026-11-20", "canal": "correo"}).status_code == 409  # sin aprobar
    assert c.post(f"{ruta}/aprobar", headers=h, json={"documento": "adaptado",
                                                      "avisos_revisados": True}).status_code == 200
    assert c.post(f"{ruta}/enviada", headers=h, json={"fecha": "2026-11-20", "canal": "otro",
                                                      "canal_otro": "en mano"}).status_code == 200
    f = _fila(motor_app, u, cid)
    assert f["estado"] == "enviada" and str(f["enviada_en"]) == "2026-11-20" and f["canal_otro"] == "en mano"
    assert c.post(f"{ruta}/entrevista", headers=h).status_code == 200
    assert c.post(f"{ruta}/cerrar", headers=h, json={"motivo": "retirada"}).status_code == 200
    assert c.post(f"{ruta}/entrevista", headers=h).status_code == 409  # cerrada: no admite más
    ev = _eventos(motor_app, u, cid)
    assert [(e["de"], e["a"]) for e in ev] == [("borrador", "aprobada"), ("aprobada", "enviada"),
                                               ("enviada", "entrevista"), ("entrevista", "cerrada")]
    assert ev[1]["canal"] == "otro" and ev[-1]["motivo"] == "retirada"
    assert [e["a"] for e in c.get(ruta).json()["eventos"]] == ["aprobada", "enviada", "entrevista", "cerrada"]


def test_los_datos_de_envio_y_de_cierre_se_validan(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    ruta = f"/api/candidaturas/{cid}"
    c.post(f"{ruta}/aprobar", headers=h, json={"documento": "adaptado", "avisos_revisados": True})
    assert c.post(f"{ruta}/enviada", headers=h, json={"canal": "correo"}).status_code == 422
    assert c.post(f"{ruta}/enviada", headers=h,
                  json={"fecha": "2026-11-20", "canal": "paloma"}).status_code == 422
    assert c.post(f"{ruta}/enviada", headers=h, json={"fecha": "2026-11-20", "canal": "correo",
                                                      "canal_otro": "x"}).status_code == 409
    assert c.post(f"{ruta}/cerrar", headers=h, json={"motivo": "porque sí"}).status_code == 422
    assert _fila(motor_app, u, cid)["estado"] == "aprobada"


# --- T16: descargas ----------------------------------------------------------------------------
def test_los_pdf_no_salen_en_borrador(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    assert c.get(f"/api/candidaturas/{cid}/cv.pdf").status_code == 403
    assert c.get(f"/api/candidaturas/{cid}/carta.pdf").status_code == 403


def test_desde_aprobada_salen_el_cv_y_la_carta_en_pdf(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    c.post(f"/api/candidaturas/{cid}/aprobar", headers=h, json={"documento": "adaptado",
                                                                "avisos_revisados": True})
    for nombre, texto in (("cv", "Camarera en Bar Sol"), ("carta", "Trabajé en Bar Sol")):
        r = c.get(f"/api/candidaturas/{cid}/{nombre}.pdf")
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
        assert "attachment" in r.headers["content-disposition"]
        assert texto in "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)


def test_con_el_estetico_elegido_se_sirve_su_archivo_original(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    est = c.post("/api/cv", headers=h, files={"archivo": ("b.md", b"# Mi CV bonito")},
                 data={"clase": "estetico"}).json()["id"]
    c.post(f"/api/candidaturas/{cid}/aprobar", headers=h,
           json={"documento": "estetico", "cv_estetico_id": est, "avisos_revisados": True})
    r = c.get(f"/api/candidaturas/{cid}/cv.pdf")
    assert r.status_code in (302, 303, 307) and r.headers["location"] == f"/api/cv/{est}/archivo"
    assert c.get(r.headers["location"]).content == b"# Mi CV bonito"
    assert c.get(f"/api/candidaturas/{cid}/carta.pdf").status_code == 200  # la carta sigue siendo la adaptada


def test_los_pdf_son_solo_de_su_duena(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    c.post(f"/api/candidaturas/{cid}/aprobar", headers=h, json={"documento": "adaptado",
                                                                "avisos_revisados": True})
    otra, _, _ = entrar(app, "google-B")
    assert otra.get(f"/api/candidaturas/{cid}/cv.pdf").status_code == 404
    assert TestClient(app).get(f"/api/candidaturas/{cid}/cv.pdf").status_code == 401


def test_una_cerrada_sin_haber_sido_aprobada_no_da_pdf(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    c.post(f"/api/candidaturas/{cid}/cerrar", headers=h, json={"motivo": "descartada"})
    assert c.get(f"/api/candidaturas/{cid}/cv.pdf").status_code == 403


# --- T17: la respuesta de la empresa -----------------------------------------------------------
CORREO = "Hola Ana, nos gustaría hacerte una entrevista el martes."


def _enviada(app, motor_app, sub="google-A"):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app, sub=sub)
    ruta = f"/api/candidaturas/{cid}"
    c.post(f"{ruta}/aprobar", headers=h, json={"documento": "adaptado", "avisos_revisados": True})
    c.post(f"{ruta}/enviada", headers=h, json={"fecha": "2026-11-20", "canal": "correo"})
    return c, h, u, cid, ruta


def _clasificar(motor_app, etiqueta):
    prov = ProveedorSimulado([{"etiqueta": etiqueta, "instrucciones_embebidas": []}])
    assert worker.procesar_una(motor_app, prov) == "hecha"


def test_pegar_la_respuesta_encola_y_el_texto_no_queda_en_ninguna_tabla(app, motor_app):
    c, h, u, cid, ruta = _enviada(app, motor_app)
    r = c.post(f"{ruta}/respuesta", headers=h, json={"texto": CORREO})
    assert r.status_code == 202 and r.json()["tarea_id"]
    assert c.get(ruta).json()["clasificando"] is True
    assert c.post(f"{ruta}/respuesta", headers=h, json={"texto": CORREO}).status_code == 409  # ya en cola
    _clasificar(motor_app, "entrevista")
    f = _fila(motor_app, u, cid)
    assert f["respuesta_pendiente"] is None and f["estado"] == "enviada"
    d = c.get(ruta).json()
    assert d["clasificando"] is False and d["respuesta_propuesta"]["destino"] == "entrevista"
    with sesion_de(motor_app, u) as s:
        for tabla in ("candidaturas", "candidatura_eventos", "tareas", "llm_llamadas"):
            volcado = s.execute(text(f"select cast(t as text) from {tabla} t")).scalars().all()
            assert not any("martes" in v for v in volcado), tabla


def test_confirmar_aplica_la_transicion_y_deja_el_evento_con_la_etiqueta(app, motor_app):
    c, h, u, cid, ruta = _enviada(app, motor_app)
    c.post(f"{ruta}/respuesta", headers=h, json={"texto": CORREO})
    _clasificar(motor_app, "entrevista")
    assert c.post(f"{ruta}/respuesta/confirmar", headers=h).status_code == 200
    f = _fila(motor_app, u, cid)
    assert f["estado"] == "entrevista" and f["respuesta_propuesta"] is None
    ev = _eventos(motor_app, u, cid)[-1]
    assert (ev["de"], ev["a"], ev["origen"], ev["etiqueta_respuesta"]) == (
        "enviada", "entrevista", "respuesta", "entrevista")
    assert c.post(f"{ruta}/respuesta/confirmar", headers=h).status_code == 409  # ya no hay propuesta


def test_un_rechazo_propone_cerrar_y_una_peticion_de_informacion_solo_una_nota(app, motor_app):
    c, h, u, cid, ruta = _enviada(app, motor_app)
    c.post(f"{ruta}/respuesta", headers=h, json={"texto": "Lo sentimos, hemos elegido a otra persona."})
    _clasificar(motor_app, "rechazo")
    assert c.post(f"{ruta}/respuesta/confirmar", headers=h).status_code == 200
    f = _fila(motor_app, u, cid)
    assert f["estado"] == "cerrada" and f["motivo_cierre"] == "rechazo"
    c2, h2, u2, cid2, ruta2 = _enviada(app, motor_app, "google-B")
    c2.post(f"{ruta2}/respuesta", headers=h2, json={"texto": "¿Puedes enviarnos tu carné?"})
    _clasificar(motor_app, "piden_informacion")
    assert c2.post(f"{ruta2}/respuesta/confirmar", headers=h2).status_code == 200
    assert _fila(motor_app, u2, cid2)["estado"] == "enviada"
    assert _eventos(motor_app, u2, cid2)[-1]["tipo"] == "nota"


def test_descartar_la_propuesta_no_cambia_nada(app, motor_app):
    c, h, u, cid, ruta = _enviada(app, motor_app)
    c.post(f"{ruta}/respuesta", headers=h, json={"texto": CORREO})
    _clasificar(motor_app, "entrevista")
    antes = len(_eventos(motor_app, u, cid))
    assert c.post(f"{ruta}/respuesta/descartar", headers=h).status_code == 200
    f = _fila(motor_app, u, cid)
    assert f["estado"] == "enviada" and f["respuesta_propuesta"] is None
    assert len(_eventos(motor_app, u, cid)) == antes


def test_la_respuesta_solo_la_pega_su_duena_y_en_una_candidatura_viva(app, motor_app):
    c, h, u, cid, ruta = _enviada(app, motor_app)
    otra, h2, _ = entrar(app, "google-B")
    assert otra.post(f"{ruta}/respuesta", headers=h2, json={"texto": CORREO}).status_code == 404
    assert c.post(f"{ruta}/respuesta", headers=h, json={"texto": ""}).status_code == 422
    c.post(f"{ruta}/cerrar", headers=h, json={"motivo": "retirada"})
    assert c.post(f"{ruta}/respuesta", headers=h, json={"texto": CORREO}).status_code == 409


def test_repetir_oferta_con_candidatura_cerrada_avisa_y_pide_confirmar(app, motor_app):
    c, h, u = entrar(app)
    _perfil(motor_app, u)
    _cv_base(motor_app, u)
    oferta = _oferta(motor_app)
    cid = c.post("/api/candidaturas", headers=h, json={"oferta_id": oferta}).json()["id"]
    with sesion_de(motor_app, u) as s:
        s.execute(text("update candidaturas set estado = 'cerrada', motivo_cierre = 'descartada' "
                       "where id = :i"), {"i": cid})
    r = c.post("/api/candidaturas", headers=h, json={"oferta_id": oferta})
    assert r.status_code == 409 and "Ya preparaste" in r.json()["detail"]
    r = c.post("/api/candidaturas", headers=h, json={"oferta_id": oferta, "repetir": True})
    assert r.status_code == 202
