"""Fase 3 · T14-T17 y T30: API de candidaturas simplificada (bloque H3), historial del CV base y
descargas en PDF. Nada llama al modelo: solo se encolan tareas."""
import io
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import text

from horma import config
from horma.web.db import sesion_de, sesion_sistema
from horma.web.main import crear_app

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
    jsonb = {"cv_traza", "carta_traza", "avisos", "huecos", "problemas_juez"}
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


def _aviso(documento="carta", frase="Trabajé en Bar Sol desde 2020.", mensaje="Revisa esto."):
    return {"documento": documento, "frase": frase, "mensaje": mensaje}


def _problema(documento, frase, tipo="inflado"):
    return {"documento": documento, "tipo": tipo, "frase": frase, "motivo": "x"}


def _eventos(motor, u, cid):
    with sesion_de(motor, u) as s:
        return [dict(f) for f in s.execute(text(
            "select de, a, motivo, canal, origen, tipo from candidatura_eventos "
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
    c, h, u, cb, oferta, cid = _escenario(app, motor_app, avisos=[_aviso()])
    d = c.get(f"/api/candidaturas/{cid}").json()
    assert d["cv_base"] == {"id": cb, "nombre": "CV hostelería", "desfasado": False}
    assert d["cv_base_motivo"] == "Es tu único CV base válido." and d["oferta"]["titulo"] == "Camarera"
    assert d["cv_contenido"] == CV and d["carta_contenido"] == CARTA and d["eventos"] == []
    assert d["avisos"] == [_aviso()] and "respuesta_pendiente" not in d and "clasificando" not in d
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
    assert any(a["documento"] == "cv" and a["frase"] == "Dirigí un equipo de 30 personas"
               for a in r.json()["avisos"]) and r.json()["preparacion"] == "pendiente_de_ti"
    assert all(set(a) == {"documento", "frase", "mensaje"} and ": " not in a["mensaje"][:12]
               for a in r.json()["avisos"])
    assert _fila(motor_app, u, cid)["cv_contenido"] == nuevo
    r = c.patch(f"/api/candidaturas/{cid}", headers=h, json={"cv_contenido": CV})
    assert r.json()["avisos"] == [] and r.json()["preparacion"] == "lista"
    with sesion_de(motor_app, u) as s:
        assert s.execute(text("select count(*) from tareas")).scalar_one() == 0


def test_editar_conserva_los_avisos_del_juez_cuya_frase_sigue(app, motor_app):
    carta_con_frase = CARTA + "\nSoy la mejor candidata posible"
    problemas = [_problema("cv", "Manejo de TPV"), _problema("carta", "Soy la mejor candidata posible")]
    c, h, u, cb, oferta, cid = _escenario(app, motor_app, carta_contenido=carta_con_frase,
                                          problemas_juez=problemas)
    ruta = f"/api/candidaturas/{cid}"
    # Edita solo el CV (la frase señalada sigue): el aviso del CV y el de la carta, que no tocó, se quedan.
    r = c.patch(ruta, headers=h, json={"cv_contenido": CV + "\nIngles B2"})
    frases = {(a["documento"], a["frase"]) for a in r.json()["avisos"]}
    assert ("cv", "Manejo de TPV") in frases and ("carta", "Soy la mejor candidata posible") in frases
    # Reescribe la frase del CV: su aviso desaparece y el de la carta sigue.
    r = c.patch(ruta, headers=h, json={"cv_contenido": CV.replace("Manejo de TPV", "Cobro en TPV")})
    frases = {(a["documento"], a["frase"]) for a in r.json()["avisos"]}
    assert ("cv", "Manejo de TPV") not in frases and ("carta", "Soy la mejor candidata posible") in frases
    # Y al revés: edita la carta y el aviso del CV (ya reescrito) no vuelve, el de la carta desaparece.
    r = c.patch(ruta, headers=h, json={"carta_contenido": CARTA})
    assert all(a["frase"] not in ("Manejo de TPV", "Soy la mejor candidata posible")
               for a in r.json()["avisos"])


def test_editar_pide_un_cambio_y_no_vale_fuera_de_borrador_ni_en_curso(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    assert c.patch(f"/api/candidaturas/{cid}", headers=h, json={}).status_code == 422
    en_curso = _candidatura(motor_app, u, _oferta(motor_app, "Otra"), cb, preparacion="en_curso")
    r = c.patch(f"/api/candidaturas/{en_curso}", headers=h, json={"carta_contenido": "x"})
    assert r.status_code == 409
    c.post(f"/api/candidaturas/{cid}/aprobar", headers=h)
    assert c.patch(f"/api/candidaturas/{cid}", headers=h, json={"carta_contenido": "x"}).status_code == 409


def test_ya_no_se_guarda_ni_se_responde_desde_la_candidatura(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    ruta = f"/api/candidaturas/{cid}"
    assert c.post(f"{ruta}/guardar-cv-base", headers=h, json={"nombre": "Mío"}).status_code == 404
    for sufijo in ("respuesta", "respuesta/confirmar", "respuesta/descartar"):
        assert c.post(f"{ruta}/{sufijo}", headers=h, json={"texto": "hola"}).status_code == 404, sufijo


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


def test_aprobar_no_pide_casilla_ni_documento_y_los_avisos_no_bloquean(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app, avisos=[_aviso()], preparacion="pendiente_de_ti")
    assert c.post(f"/api/candidaturas/{cid}/aprobar", headers=h).status_code == 200
    assert _fila(motor_app, u, cid)["estado"] == "aprobada"
    assert _eventos(motor_app, u, cid)[-1]["a"] == "aprobada"
    assert c.post(f"/api/candidaturas/{cid}/aprobar", headers=h).status_code == 409  # ya no es borrador


def test_no_se_aprueba_lo_que_se_esta_preparando_ni_lo_de_otra(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    en_curso = _candidatura(motor_app, u, _oferta(motor_app, "Otra"), cb, preparacion="en_curso")
    assert c.post(f"/api/candidaturas/{en_curso}/aprobar", headers=h).status_code == 409
    otra, h2, _ = entrar(app, "google-B")
    assert otra.post(f"/api/candidaturas/{cid}/aprobar", headers=h2).status_code == 404
    assert _fila(motor_app, u, cid)["estado"] == "borrador"


# --- reintentar ---------------------------------------------------------------------------------
def test_reintentar_solo_con_error_y_encola_la_misma_candidatura(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    assert c.post(f"/api/candidaturas/{cid}/reintentar", headers=h).status_code == 409  # está «lista»
    fallida = _candidatura(motor_app, u, _oferta(motor_app, "Otra"), cb, preparacion="error",
                           motivo_error="tope de coste superado")
    r = c.post(f"/api/candidaturas/{fallida}/reintentar", headers=h)
    assert r.status_code == 202 and r.json()["id"] == fallida and r.json()["tarea_id"]
    f = _fila(motor_app, u, fallida)
    assert f["preparacion"] == "en_curso" and f["motivo_error"] is None
    with sesion_de(motor_app, u) as s:
        t = s.execute(text("select tipo, entidad_id, tope_coste from tareas where id = :i"),
                      {"i": r.json()["tarea_id"]}).one()
    assert t.tipo == "candidatura" and t.entidad_id == fallida and float(t.tope_coste) == 1.0
    assert c.post(f"/api/candidaturas/{fallida}/reintentar", headers=h).status_code == 409  # ya en curso


def test_reintentar_es_solo_de_su_duena_y_pide_csrf(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app, preparacion="error")
    otra, h2, _ = entrar(app, "google-B")
    assert otra.post(f"/api/candidaturas/{cid}/reintentar", headers=h2).status_code == 404
    assert c.post(f"/api/candidaturas/{cid}/reintentar").status_code == 403


def test_las_transiciones_dejan_un_evento_cada_una(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    ruta = f"/api/candidaturas/{cid}"
    assert c.post(f"{ruta}/enviada", headers=h,
                  json={"fecha": "2026-11-20", "canal": "correo"}).status_code == 409  # sin aprobar
    assert c.post(f"{ruta}/aprobar", headers=h).status_code == 200
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


def test_enviada_sin_fecha_usa_hoy_y_el_canal_es_opcional(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    ruta = f"/api/candidaturas/{cid}"
    c.post(f"{ruta}/aprobar", headers=h)
    assert c.post(f"{ruta}/enviada", headers=h, json={}).status_code == 200
    f = _fila(motor_app, u, cid)
    assert f["estado"] == "enviada" and f["enviada_en"] == date.today() and f["canal"] is None
    d = c.get(ruta).json()
    assert d["canal"] is None and d["eventos"][-1]["canal"] is None


def test_me_han_llamado_y_me_han_rechazado_solo_cuando_son_legales(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    ruta = f"/api/candidaturas/{cid}"
    assert c.post(f"{ruta}/entrevista", headers=h).status_code == 409           # desde borrador no
    c.post(f"{ruta}/aprobar", headers=h)
    assert c.post(f"{ruta}/entrevista", headers=h).status_code == 409           # ni desde aprobada
    c.post(f"{ruta}/enviada", headers=h, json={})
    assert c.post(f"{ruta}/entrevista", headers=h).status_code == 200           # «Me han llamado»
    assert c.post(f"{ruta}/entrevista", headers=h).status_code == 409           # ya está en entrevista
    assert c.post(f"{ruta}/cerrar", headers=h, json={"motivo": "rechazo"}).status_code == 200
    f = _fila(motor_app, u, cid)
    assert f["estado"] == "cerrada" and f["motivo_cierre"] == "rechazo"
    assert c.post(f"{ruta}/cerrar", headers=h, json={"motivo": "rechazo"}).status_code == 409


def test_los_datos_de_envio_y_de_cierre_se_validan(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    ruta = f"/api/candidaturas/{cid}"
    c.post(f"{ruta}/aprobar", headers=h)
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
    c.post(f"/api/candidaturas/{cid}/aprobar", headers=h)
    for nombre, texto in (("cv", "Camarera en Bar Sol"), ("carta", "Trabajé en Bar Sol")):
        r = c.get(f"/api/candidaturas/{cid}/{nombre}.pdf")
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
        assert "attachment" in r.headers["content-disposition"]
        assert texto in "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)


def test_el_pdf_es_siempre_del_cv_adaptado_aunque_haya_un_estetico_subido(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    c.post("/api/cv", headers=h, files={"archivo": ("b.md", b"# Mi CV bonito")}, data={"clase": "estetico"})
    c.post(f"/api/candidaturas/{cid}/aprobar", headers=h)
    r = c.get(f"/api/candidaturas/{cid}/cv.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert "Camarera en Bar Sol" in "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)


def test_tras_enviarla_los_pdf_siguen_y_al_cerrarla_depende_de_si_se_aprobo(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    ruta = f"/api/candidaturas/{cid}"
    c.post(f"{ruta}/aprobar", headers=h)
    c.post(f"{ruta}/enviada", headers=h, json={})
    assert c.get(f"{ruta}/cv.pdf").status_code == 200
    c.post(f"{ruta}/cerrar", headers=h, json={"motivo": "rechazo"})
    assert c.get(f"{ruta}/carta.pdf").status_code == 200                       # se aprobó antes de cerrar


def test_los_pdf_son_solo_de_su_duena(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    c.post(f"/api/candidaturas/{cid}/aprobar", headers=h)
    otra, _, _ = entrar(app, "google-B")
    assert otra.get(f"/api/candidaturas/{cid}/cv.pdf").status_code == 404
    assert TestClient(app).get(f"/api/candidaturas/{cid}/cv.pdf").status_code == 401


def test_una_cerrada_sin_haber_sido_aprobada_no_da_pdf(app, motor_app):
    c, h, u, cb, oferta, cid = _escenario(app, motor_app)
    c.post(f"/api/candidaturas/{cid}/cerrar", headers=h, json={"motivo": "descartada"})
    assert c.get(f"/api/candidaturas/{cid}/cv.pdf").status_code == 403


# --- repetir una oferta ya cerrada ---------------------------------------------------------------
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
