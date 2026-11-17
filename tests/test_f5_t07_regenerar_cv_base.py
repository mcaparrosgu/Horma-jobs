"""Fase 5 · T07: regenerar un CV base a mano; la versión anterior queda en su historial (RF-5.1e)."""
# ruff: noqa: F401, F811  (fixtures importadas de otro módulo)
import pytest
from sqlalchemy import text
from test_f2_t13_t14_bd_worker import BUENO, MALO, TAX, _encolar, _perfilar_hecho, _usuarias
from test_f2_t15_t19_api import _perfil_hecho, _propietario, _tareas, _usuaria_id, app, archivos, entrar

from horma.flows import generar_cv_base
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.perfil import Perfil
from horma.web.db import sesion_de
from horma.web.queue import worker
from horma.web.repositories import perfiles

_BAR = "Camarera · Bar Sol · 2020-2023"
_LINEAS = ["## Idiomas", "Inglés B2", "## Experiencia", _BAR]  # mismo contenido que BUENO, otro orden
NUEVO = {"contenido": "\n".join(_LINEAS), "traza": BUENO["traza"]}


def test_el_flujo_con_destinos_dados_genera_solo_esos():
    perfil = Perfil.model_validate({"taxonomia": TAX})
    estado = {"perfil": perfil.model_dump(mode="json"), "cv_maestro": BUENO["contenido"],
              "preferencias": {"familias": ["ventas_comercial"]},
              "destinos": [{"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion"}]}
    prov = ProveedorSimulado([NUEVO])
    salida = generar_cv_base.crear(proveedor=prov).run(estado)
    assert [g["destino"]["familia"] for g in salida["cv_base"]["guardados"]] == ["hosteleria_restauracion"]
    assert len(prov.llamadas) == 1


def _cv_base_generado(motor, u):
    pid = _perfilar_hecho(motor, u)
    _encolar(motor, u, "generar_cv_base", pid)
    assert worker.procesar_una(motor, ProveedorSimulado([BUENO])) == "hecha"
    with sesion_de(motor, u) as s:
        return s.execute(text("select id from cv_base")).scalar_one()


@pytest.mark.bd
def test_regenerar_sustituye_el_contenido_y_deja_la_version_anterior_en_el_historial(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    cv_id = _cv_base_generado(motor_app, a)
    _encolar(motor_app, a, "regenerar_cv_base", cv_id)
    assert worker.procesar_una(motor_app, ProveedorSimulado([NUEVO])) == "hecha"
    with sesion_de(motor_app, a) as s:
        filas = s.execute(text("select id, contenido, estado, motivo_error from cv_base")).all()
        versiones = s.execute(text("select origen, contenido from cv_base_versiones")).all()
        historial = perfiles.versiones_cv_base(s, cv_id)  # lo que ve la pantalla
    assert [(f.id, f.estado) for f in filas] == [(cv_id, "hecho")]  # mismo CV, no uno nuevo
    assert filas[0].contenido == NUEVO["contenido"]
    assert [(v.origen, v.contenido) for v in versiones] == [("regeneracion", BUENO["contenido"])]
    assert [v["origen"] for v in historial] == ["regeneracion"]


@pytest.mark.bd
def test_si_la_regeneracion_no_pasa_la_verificacion_el_cv_se_queda_como_estaba(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    cv_id = _cv_base_generado(motor_app, a)
    _encolar(motor_app, a, "regenerar_cv_base", cv_id, tope_reintentos=1)
    assert worker.procesar_una(motor_app, ProveedorSimulado([MALO, MALO])) == "error"
    with sesion_de(motor_app, a) as s:
        fila = s.execute(text("select contenido, estado, motivo_error from cv_base")).one()
        assert perfiles.versiones_cv_base(s, cv_id) == []
    assert fila.contenido == BUENO["contenido"] and fila.estado == "hecho" and fila.motivo_error


@pytest.mark.bd
def test_regenerar_marca_el_cv_con_la_version_vigente_y_deja_de_estar_desfasado(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    cv_id = _cv_base_generado(motor_app, a)
    with sesion_de(motor_app, a) as s:  # el perfil avanza (v2) y el CV cita un dato que ya no está
        s.execute(text("update cv_base set traza = cast(:t as jsonb)"),
                  {"t": '[{"frase": "x", "fragmento": "Dato que ya no existe"}]'})
        s.execute(text("insert into perfiles (usuaria_id, version, estado, datos, cv_maestro) "
                       "select usuaria_id, 2, 'hecha', datos, :m from perfiles where version = 1"),
                  {"m": BUENO["contenido"]})
        assert perfiles.listar_cv_base(s)[0]["desfasado"] is True
    _encolar(motor_app, a, "regenerar_cv_base", cv_id)
    assert worker.procesar_una(motor_app, ProveedorSimulado([NUEVO])) == "hecha"
    with sesion_de(motor_app, a) as s:
        cv = perfiles.listar_cv_base(s)[0]
    assert cv["perfil_version"] == 2 and cv["desfasado"] is False


# --- API: solo al pulsar el botón ---------------------------------------------------------------
@pytest.mark.bd
def test_la_api_encola_la_regeneracion_solo_al_pedirla(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    with sesion_de(motor_app, u) as s:
        perfiles.guardar_cv_base(s, u, 1, {"guardados": [{
            "destino": {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion"},
            "contenido": "x", "traza": [], "intentos": 1}], "rechazados": []})
        cv_id = s.execute(text("select id from cv_base")).scalar_one()
    c.patch("/api/perfil/datos", headers=h, json={
        "campo": "experiencias", "indice": 0,
        "dato": {"puesto": "Jefa de sala", "empresa": "Bar Sol", "inicio": "2020", "fin": "2023"}})
    assert _tareas(motor_app, "regenerar_cv_base") == []  # cambiar el perfil no regenera nada
    assert c.post("/api/cv-base/9999/regenerar", headers=h).status_code == 404
    r = c.post(f"/api/cv-base/{cv_id}/regenerar", headers=h)
    assert r.status_code == 202 and len(_tareas(motor_app, "regenerar_cv_base")) == 1
    assert c.get("/api/cv-base").json()["regenerando"] == [cv_id]
    assert c.post(f"/api/cv-base/{cv_id}/regenerar", headers=h).status_code == 409  # ya en curso


def test_la_pantalla_tiene_el_boton_regenerar_y_dice_que_ha_cambiado():
    from pathlib import Path
    js = (Path(__file__).parent.parent / "horma" / "web" / "static" / "cv-base.js").read_text("utf-8")
    assert "/regenerar" in js and '"Regenerar"' in js and "Qué ha cambiado" in js and "regeneracion" in js
