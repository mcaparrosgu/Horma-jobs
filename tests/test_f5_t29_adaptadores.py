"""Fase 5 · T29: adaptadores de ingesta (RF-5.5, RF-5.5b, RF-5.5d). Respuestas grabadas inventadas."""
import base64

import httpx
import pytest
from sqlalchemy import text

from horma.ingesta import leer_fuente
from horma.schemas.fuente import Fuente
from horma.tools import normalizar
from horma.web.db import sesion_sistema
from horma.web.services import ingesta as servicio

BASE = {"web": "https://www.ejemplo.test", "url": "https://api.ejemplo.test/ofertas"}


def _cliente(respuestas: dict, peticiones: list):
    def responder(request: httpx.Request):
        peticiones.append(request)
        return httpx.Response(200, json=respuestas[request.url.path])
    return httpx.Client(transport=httpx.MockTransport(responder))


def test_lista_dolar_es_un_array_en_la_raiz():
    datos = [{"id": 1, "title": "Dev"}, {"id": 2, "title": "QA"}]
    assert len(normalizar.items(datos, {"lista": "$"})) == 2
    f = Fuente(nombre="remotiva", **BASE, mapeo={"lista": "$", "id": "id", "titulo": "title"})
    ofertas = leer_fuente(f, _cliente({"/ofertas": datos}, []), limite=5)
    assert [o.id_externo for o in ofertas] == ["1", "2"]


def test_basic_auth_desde_variables():
    f = Fuente(nombre="conclave", **BASE, mapeo={"lista": "$", "id": "id"},
               auth_basica={"usuario": "${EJ_USUARIO}", "clave": "${EJ_CLAVE}"},
               variable_clave="EJ_USUARIO,EJ_CLAVE")
    peticiones = []
    leer_fuente(f, _cliente({"/ofertas": []}, peticiones), limite=1,
                entorno={"EJ_USUARIO": "ana", "EJ_CLAVE": "s3creta"})
    esperado = "Basic " + base64.b64encode(b"ana:s3creta").decode()
    assert peticiones[0].headers["Authorization"] == esperado
    with pytest.raises(ValueError):
        leer_fuente(f, _cliente({"/ofertas": []}, []), limite=1, entorno={})


def test_la_variable_de_auth_debe_estar_declarada():
    f = Fuente(nombre="conclave", **BASE, mapeo={"lista": "$", "id": "id"},
               auth_basica={"usuario": "${OTRA}", "clave": "x"}, variable_clave="EJ_USUARIO")
    with pytest.raises(ValueError):
        leer_fuente(f, _cliente({"/ofertas": []}, []), limite=1, entorno={"OTRA": "1"})


def test_detalle_trae_la_descripcion_con_una_segunda_llamada_por_oferta():
    f = Fuente(nombre="detallista", **BASE,
               mapeo={"lista": "resultados", "id": "id", "titulo": "titulo", "descripcion": "descripcion"},
               detalle={"url": "https://api.ejemplo.test/oferta/{id}", "raiz": "oferta"})
    respuestas = {
        "/ofertas": {"resultados": [{"id": "a1", "titulo": "Camarera"}, {"id": "b2", "titulo": "Cocinero"}]},
        "/oferta/a1": {"oferta": {"descripcion": "<p>Sala y barra</p>"}},
        "/oferta/b2": {"oferta": {"descripcion": "<p>Cocina fría</p>"}},
    }
    peticiones = []
    ofertas = leer_fuente(f, _cliente(respuestas, peticiones), limite=1)
    assert len(ofertas) == 1 and "Sala y barra" in ofertas[0].texto
    assert [r.url.path for r in peticiones] == ["/ofertas", "/oferta/a1"]  # solo detalle de las pedidas


def test_detalle_que_falla_no_tumba_la_oferta():
    f = Fuente(nombre="detallista", **BASE, mapeo={"lista": "$", "id": "id", "titulo": "titulo"},
               detalle={"url": "https://api.ejemplo.test/oferta/{id}"})

    def responder(request):
        if request.url.path == "/ofertas":
            return httpx.Response(200, json=[{"id": "a1", "titulo": "Camarera"}])
        return httpx.Response(500)
    ofertas = leer_fuente(f, httpx.Client(transport=httpx.MockTransport(responder)), limite=1)
    assert ofertas[0].texto.startswith("Camarera")


def test_el_detalle_exige_https_y_marcador_id():
    with pytest.raises(ValueError):
        Fuente(nombre="x1", **BASE, mapeo={"lista": "$"}, detalle={"url": "https://a.test/fijo"})
    with pytest.raises(ValueError):
        Fuente(nombre="x1", **BASE, mapeo={"lista": "$"}, detalle={"url": "http://a.test/{id}"})


# --- cada_horas y atribución (BD) --------------------------------------------------------------
@pytest.mark.bd
def test_cada_horas_no_se_pide_antes_de_tiempo(motor_app, bd_limpia):
    f = Fuente(nombre="remotiva", **BASE, mapeo={"lista": "$", "id": "id"}, cada_horas=6,
               atribucion="Remotiva (remotiva.test)")
    with sesion_sistema(motor_app) as s:
        fid = servicio.repo.crear_fuente(s, f)
        s.execute(text("update fuentes set activa=true where id=:i"), {"i": fid})
    servicio.pedir_ejecucion(motor_app, fid, 5)  # la primera, sin historial
    with pytest.raises(servicio.Conflicto):
        servicio.pedir_ejecucion(motor_app, fid, 5)
    with pytest.raises(servicio.Conflicto):
        servicio.empezar_ejecucion(motor_app, "remotiva", 5)
    with sesion_sistema(motor_app) as s:  # pasadas las 6 horas, ya se puede
        s.execute(text("update ejecuciones_ingesta set creada_en = now() - interval '7 hours'"))
    assert servicio.pedir_ejecucion(motor_app, fid, 5)["estado"] == "pendiente"
    with sesion_sistema(motor_app) as s:
        guardada = servicio.repo.fuente(s, fuente_id=fid)
    assert guardada["cada_horas"] == 6 and guardada["atribucion"] == "Remotiva (remotiva.test)"


@pytest.mark.bd
def test_una_ejecucion_con_error_no_bloquea_el_reintento(motor_app, bd_limpia):
    f = Fuente(nombre="remotiva", **BASE, mapeo={"lista": "$", "id": "id"}, cada_horas=6)
    with sesion_sistema(motor_app) as s:
        fid = servicio.repo.crear_fuente(s, f)
        s.execute(text("update fuentes set activa=true where id=:i"), {"i": fid})
    e = servicio.empezar_ejecucion(motor_app, "remotiva", 5)["ejecucion"]
    servicio.cerrar_ejecucion(motor_app, e["id"], recibidas=0, nuevas=0, repetidas=0, errores=0,
                              motivo="HTTPStatusError: 500")
    assert servicio.empezar_ejecucion(motor_app, "remotiva", 5)["ejecucion"]["estado"] == "en_curso"
