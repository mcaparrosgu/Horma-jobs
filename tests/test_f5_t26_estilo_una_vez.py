"""Fase 5 · T26: la guía se calcula una sola vez y solo se repite con el botón (RF-5.6d)."""
from pathlib import Path

import pytest
from sqlalchemy import text
from test_f2_t15_t19_api import _propietario, _tareas, admin, app, archivos, entrar, subir  # noqa: F401
from test_f5_t24_cartas import _carta

from horma.flows.registry import FLUJOS, RESULTADO
from horma.llm.simulado import ProveedorSimulado
from horma.web.queue import worker

pytestmark = [pytest.mark.bd, pytest.mark.usefixtures("estilo_real")]

GUIA = {"registro": "cercano", "persona": "primera", "longitud_frase": "corta", "vinetas": "con verbo",
        "expresiones": [{"rasgo": "dice «he llevado»", "cita": "he llevado una sala"}], "evita": []}
TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior", "stack": []}


def _extraccion(cv_id):
    origen = {"fuente": "cv", "cv_id": cv_id, "fragmento": "Camarera en Bar Sol, 2020-2023"}
    return {"perfil": {"experiencias": [{"puesto": "Camarera", "empresa": "Bar Sol", "inicio": "2020",
                                         "fin": "2023", "origen": origen}]}}


def _guia_en_bd():
    with admin() as s:
        return s.execute(text("select guia, origen from estilo")).mappings().first()


def _procesar_estilo(motor_app, guia=GUIA):
    return worker.procesar_una(motor_app, ProveedorSimulado([{"guia": guia}]))


def test_el_flujo_esta_registrado():
    assert "analizar_estilo" in FLUJOS and RESULTADO["analizar_estilo"] == "guia"


def test_la_primera_carta_encola_el_analisis_y_el_worker_guarda_la_guia(app, motor_app):  # noqa: F811
    c, h, _ = entrar(app)
    assert _carta(c, h, nombre="Carta").status_code == 201
    (t,) = _tareas(motor_app, "analizar_estilo")
    assert t.estado == "pendiente"
    assert _procesar_estilo(motor_app) == "hecha"
    fila = _guia_en_bd()
    assert fila["origen"] == "modelo" and fila["guia"]["registro"] == "cercano"
    assert [e["cita"] for e in fila["guia"]["expresiones"]] == ["he llevado una sala"]


def test_subir_un_segundo_documento_con_guia_hecha_no_llama_al_modelo(app, motor_app):  # noqa: F811
    c, h, _ = entrar(app)
    _carta(c, h, nombre="Carta")
    _procesar_estilo(motor_app)
    assert _carta(c, h, nombre="Otra carta").status_code == 201
    assert len(_tareas(motor_app, "analizar_estilo")) == 1  # solo la primera
    assert _tareas(motor_app, "perfilar") == []


def test_un_cv_perfilado_sin_guia_encola_el_analisis_una_vez(app, motor_app):  # noqa: F811
    c, h, _ = entrar(app)
    assert subir(c, h, nombre="CV").status_code == 201
    assert _tareas(motor_app, "analizar_estilo") == []  # aún no: la guía espera a que se perfile
    assert worker.procesar_una(motor_app, ProveedorSimulado([_extraccion(1), TAX])) == "hecha"
    (t,) = _tareas(motor_app, "analizar_estilo")
    assert t.estado == "pendiente"
    # el análisis usa el CV como documento de tipo «cv»
    prov = ProveedorSimulado([{"guia": {**GUIA, "expresiones": []}}])
    assert worker.procesar_una(motor_app, prov) == "hecha"
    assert '"tipo":"cv"' in prov.llamadas[0]["usuario"].replace('": "', '":"')
    # con la guía hecha, un segundo CV perfilado ya no encola nada
    assert subir(c, h, nombre="CV 2", contenido=b"Ana\nCamarera en Bar Sol, 2020-2023\n").status_code == 201
    assert worker.procesar_una(motor_app, ProveedorSimulado([_extraccion(1), TAX])) == "hecha"
    assert len(_tareas(motor_app, "analizar_estilo")) == 1


def test_el_boton_pide_un_nuevo_analisis_aunque_haya_guia(app, motor_app):  # noqa: F811
    c, h, _ = entrar(app)
    _carta(c, h, nombre="Carta")
    _procesar_estilo(motor_app)
    r = c.post("/api/estilo/analizar", headers=h)
    assert r.status_code == 202
    assert len(_tareas(motor_app, "analizar_estilo")) == 2
    assert c.post("/api/estilo/analizar", headers=h).status_code == 409  # ya hay uno en marcha
    nueva = {**GUIA, "registro": "formal"}
    assert _procesar_estilo(motor_app, nueva) == "hecha"
    assert _guia_en_bd()["guia"]["registro"] == "formal"


def test_el_boton_sin_documentos_da_409(app):  # noqa: F811
    c, h, _ = entrar(app)
    assert c.post("/api/estilo/analizar", headers=h).status_code == 409


def test_lo_que_edita_ella_se_marca_usuaria_y_se_respeta(app, motor_app):  # noqa: F811
    c, h, _ = entrar(app)
    _carta(c, h, nombre="Carta")
    _procesar_estilo(motor_app)
    editada = {**GUIA, "registro": "formal", "vinetas": "sin punto final"}
    r = c.put("/api/estilo", headers=h, json=editada)
    assert r.status_code == 200 and r.json()["origen"] == "usuaria"
    fila = _guia_en_bd()
    assert fila["origen"] == "usuaria" and fila["guia"]["vinetas"] == "sin punto final"
    # subir otra carta no la pisa ni llama al modelo
    _carta(c, h, nombre="Otra")
    assert len(_tareas(motor_app, "analizar_estilo")) == 1
    ver = c.get("/api/estilo").json()
    assert ver["origen"] == "usuaria" and ver["guia"]["registro"] == "formal" and ver["hay_documentos"]


def test_una_guia_editada_que_describe_a_la_persona_se_rechaza(app):  # noqa: F811
    c, h, _ = entrar(app)
    r = c.put("/api/estilo", headers=h, json={**GUIA, "vinetas": "es una persona tranquila"})
    assert r.status_code == 422 and "describe a la persona" in r.json()["detail"]
    assert c.get("/api/estilo").json()["guia"] is None


def test_sin_sesion_o_sin_csrf_no_pasa(app):  # noqa: F811
    c, h, _ = entrar(app)
    assert c.put("/api/estilo", json=GUIA).status_code == 403
    assert c.post("/api/estilo/analizar").status_code == 403


def test_la_guia_es_solo_de_su_duena(app, motor_app):  # noqa: F811
    c, h, _ = entrar(app)
    c.put("/api/estilo", headers=h, json=GUIA)
    otra, h2, _ = entrar(app, "google-B")
    assert otra.get("/api/estilo").json()["guia"] is None


def test_la_pantalla_muestra_la_guia_y_el_boton():
    html = Path("horma/web/static/perfil.html").read_text(encoding="utf-8")
    js = Path("horma/web/static/perfil.js").read_text(encoding="utf-8")
    assert 'id="estilo"' in html and "Volver a analizar mi estilo" in html
    assert "/api/estilo" in js and "textContent" in js

