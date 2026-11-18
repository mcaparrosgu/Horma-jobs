"""Fase 5 · T08: visibilidad de las experiencias en un CV base: completa, condensada u oculta (RF-5.1g)."""
# ruff: noqa: F401, F811  (fixtures importadas de otro módulo)
import pytest
from sqlalchemy import text
from test_f2_t13_t14_bd_worker import _encolar, _perfilar_hecho, _usuarias
from test_f2_t15_t19_api import (
    _perfil_hecho,
    _propietario,
    _tareas,
    _usuaria_id,
    admin,
    app,
    archivos,
    entrar,
)

from horma.flows import generar_cv_base
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.perfil import Perfil
from horma.tools.componer_cv_maestro import componer_cv_maestro
from horma.tools.visibilidad_cv import clave_experiencia, verificar_visibilidad
from horma.web.db import sesion_de
from horma.web.queue import worker
from horma.web.repositories import perfiles

pytestmark = pytest.mark.usefixtures("juez_automatico")


TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior", "stack": []}
ORIGEN = {"fuente": "usuaria", "fragmento": "x"}
BAR = {"puesto": "Camarera", "empresa": "Bar Sol", "inicio": "2020", "fin": "2023", "origen": ORIGEN}
OBRA = {"puesto": "Peón", "empresa": "Obras Norte", "inicio": "2018", "fin": "2019",
        "descripcion": "Montaje de andamios", "origen": ORIGEN}
PERFIL = Perfil.model_validate({"taxonomia": TAX, "experiencias": [BAR, OBRA]})
K_BAR, K_OBRA = (clave_experiencia(x) for x in PERFIL.experiencias)
CABECERA_BAR, CABECERA_OBRA = "Camarera · Bar Sol · 2020-2023", "Peón · Obras Norte · 2018-2019"
COMPLETO = f"## Experiencia\n{CABECERA_BAR}\n{CABECERA_OBRA}\nMontaje de andamios"
CONDENSADO = f"## Experiencia\n{CABECERA_BAR}\n{CABECERA_OBRA}"
SIN_OBRA = f"## Experiencia\n{CABECERA_BAR}"


def _respuesta(contenido):
    lineas = [x.lstrip("- ").strip() for x in contenido.splitlines() if not x.startswith("#")]
    return {"contenido": contenido, "traza": [{"frase": x, "fragmento": x} for x in lineas]}


# --- el comprobador (código puro) ---------------------------------------------------------------
def test_la_clave_no_depende_de_mayusculas_acentos_ni_espacios():
    otra = Perfil.model_validate({"experiencias": [{**OBRA, "puesto": " PEÓN ", "empresa": "obras  norte"}]})
    assert clave_experiencia(otra.experiencias[0]) == K_OBRA == "peon|obras norte|2018"


def test_una_oculta_no_puede_aparecer_y_una_completa_o_condensada_debe_aparecer():
    assert verificar_visibilidad(SIN_OBRA, PERFIL, {K_OBRA: "oculta"}) == []
    assert verificar_visibilidad(CONDENSADO, PERFIL, {K_OBRA: "oculta"})
    assert verificar_visibilidad(SIN_OBRA, PERFIL, {K_OBRA: "condensada"})
    assert verificar_visibilidad(SIN_OBRA, PERFIL, {K_OBRA: "completa"})


def test_una_condensada_ocupa_una_linea_y_una_completa_puede_llevar_su_descripcion():
    assert verificar_visibilidad(CONDENSADO, PERFIL, {K_OBRA: "condensada"}) == []
    assert verificar_visibilidad(COMPLETO, PERFIL, {K_OBRA: "condensada"})
    assert verificar_visibilidad(COMPLETO, PERFIL, {K_OBRA: "completa"}) == []


def test_sin_marcas_no_se_comprueba_nada():
    assert verificar_visibilidad(SIN_OBRA, PERFIL, {}) == []


# --- el flujo -----------------------------------------------------------------------------------
def _estado(visibilidad):
    return {"perfil": PERFIL.model_dump(mode="json"), "cv_maestro": componer_cv_maestro(PERFIL),
            "destinos": [{"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion"}],
            "visibilidad": visibilidad}


def test_el_generador_recibe_las_reglas_y_una_oculta_no_aparece():
    prov = ProveedorSimulado([_respuesta(SIN_OBRA)])
    salida = generar_cv_base.crear(proveedor=prov).run(_estado({K_OBRA: "oculta"}))
    assert [g["contenido"] for g in salida["cv_base"]["guardados"]] == [SIN_OBRA]
    assert "oculta" in prov.llamadas[0]["usuario"] and "Obras Norte" in prov.llamadas[0]["usuario"]


def test_si_el_modelo_ignora_la_visibilidad_el_cv_se_rechaza_tras_el_reintento():
    prov = ProveedorSimulado([_respuesta(COMPLETO), _respuesta(COMPLETO)])
    salida = generar_cv_base.crear(proveedor=prov).run(_estado({K_OBRA: "oculta"}))
    assert salida["cv_base"]["guardados"] == [] and "oculta" in salida["cv_base"]["rechazados"][0]["motivo"]


def test_el_segundo_intento_recibe_el_error_de_visibilidad_y_puede_corregir():
    prov = ProveedorSimulado([_respuesta(COMPLETO), _respuesta(CONDENSADO)])
    salida = generar_cv_base.crear(proveedor=prov).run(_estado({K_OBRA: "condensada"}))
    assert [g["intentos"] for g in salida["cv_base"]["guardados"]] == [2]


# --- la API y el worker -------------------------------------------------------------------------
def _dos_experiencias(c, h):
    c.patch("/api/perfil/datos", headers=h, json={
        "campo": "experiencias", "indice": 0,
        "dato": {"puesto": "Camarera", "empresa": "Bar Sol", "inicio": "2020", "fin": "2023"}})
    r = c.patch("/api/perfil/datos", headers=h, json={
        "campo": "experiencias",
        "dato": {"puesto": "Peón", "empresa": "Obras Norte", "inicio": "2018", "fin": "2019",
                 "descripcion": "Montaje de andamios"}})
    assert r.status_code == 201


def _sin_otras_tareas():
    """Editar el perfil encola trabajos de clasificación: aquí solo interesa la regeneración."""
    with admin() as s:
        s.execute(text("delete from tareas"))
        s.commit()


def _cv_base_hecho(motor, u):
    with sesion_de(motor, u) as s:
        v = perfiles.vigente(s)["version"]
        perfiles.guardar_cv_base(s, u, v, {"guardados": [{
            "destino": {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion"},
            "contenido": "x", "traza": [], "intentos": 1}], "rechazados": []})
        return s.execute(text("select id from cv_base")).scalar_one()


@pytest.mark.bd
def test_la_api_guarda_la_visibilidad_y_lista_las_experiencias_para_marcarla(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    _dos_experiencias(c, h)
    cv_id = _cv_base_hecho(motor_app, u)
    r = c.get("/api/cv-base").json()
    assert [e["clave"] for e in r["experiencias"]] == [K_BAR, K_OBRA]
    assert r["experiencias"][1]["nombre"] == "Peón · Obras Norte"
    assert r["cv_base"][0]["visibilidad"] == {}
    ok = c.put(f"/api/cv-base/{cv_id}/visibilidad", headers=h, json={"visibilidad": {K_OBRA: "oculta"}})
    assert ok.status_code == 200
    assert c.get("/api/cv-base").json()["cv_base"][0]["visibilidad"] == {K_OBRA: "oculta"}
    # marcar otra vez sustituye lo anterior; vacío = volver a lo automático
    c.put(f"/api/cv-base/{cv_id}/visibilidad", headers=h, json={"visibilidad": {}})
    assert c.get("/api/cv-base").json()["cv_base"][0]["visibilidad"] == {}


@pytest.mark.bd
def test_la_api_rechaza_valores_y_experiencias_que_no_existen(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    _dos_experiencias(c, h)
    cv_id = _cv_base_hecho(motor_app, u)
    url = f"/api/cv-base/{cv_id}/visibilidad"
    assert c.put(url, headers=h, json={"visibilidad": {K_OBRA: "borrosa"}}).status_code == 422
    assert c.put(url, headers=h, json={"visibilidad": {"inventada|x|1": "oculta"}}).status_code == 422
    assert c.put("/api/cv-base/9999/visibilidad", headers=h, json={"visibilidad": {}}).status_code == 404


@pytest.mark.bd
def test_al_regenerar_se_respeta_lo_marcado(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    _dos_experiencias(c, h)
    cv_id = _cv_base_hecho(motor_app, u)
    c.put(f"/api/cv-base/{cv_id}/visibilidad", headers=h, json={"visibilidad": {K_OBRA: "oculta"}})
    with sesion_de(motor_app, u) as s:
        maestro = perfiles.vigente(s)["cv_maestro"]
    cab = [x for x in maestro.splitlines() if "Camarera" in x][0]
    ok = {"contenido": f"## Experiencia\n{cab}", "traza": [{"frase": cab, "fragmento": cab}]}
    _sin_otras_tareas()
    _encolar(motor_app, u, "regenerar_cv_base", cv_id, tope_reintentos=1)
    # el perfil de prueba tiene idiomas: el CV de prueba los incluye para no fallar por otra causa
    assert worker.procesar_una(motor_app, ProveedorSimulado([_con_idiomas(ok, maestro)])) == "hecha"
    with sesion_de(motor_app, u) as s:
        contenido = s.execute(text("select contenido from cv_base")).scalar_one()
    assert "Obras Norte" not in contenido and "Camarera" in contenido


def _con_idiomas(resp, maestro):
    ids = [x for x in maestro.splitlines() if x.strip() and not x.startswith("#")
           and "·" not in x and x not in ("Montaje de andamios",)]
    lineas = [x for x in ids if x not in resp["contenido"]]
    extra = "\n".join(lineas)
    return {"contenido": resp["contenido"] + ("\n## Idiomas\n" + extra if extra else ""),
            "traza": resp["traza"] + [{"frase": x, "fragmento": x} for x in lineas]}


@pytest.mark.bd
def test_si_regenera_ignorando_lo_oculto_no_se_guarda(app, motor_app):
    c, h, _ = entrar(app)
    u = _usuaria_id(motor_app, "google-A")
    _perfil_hecho(motor_app, u)
    _dos_experiencias(c, h)
    cv_id = _cv_base_hecho(motor_app, u)
    c.put(f"/api/cv-base/{cv_id}/visibilidad", headers=h, json={"visibilidad": {K_OBRA: "oculta"}})
    with sesion_de(motor_app, u) as s:
        maestro = perfiles.vigente(s)["cv_maestro"]
    todo = _con_idiomas({"contenido": "## Experiencia\n" + "\n".join(
        x for x in maestro.splitlines() if "·" in x), "traza": [
        {"frase": x, "fragmento": x} for x in maestro.splitlines() if "·" in x]}, maestro)
    _sin_otras_tareas()
    _encolar(motor_app, u, "regenerar_cv_base", cv_id, tope_reintentos=1)
    assert worker.procesar_una(motor_app, ProveedorSimulado([todo, todo])) == "error"
    with sesion_de(motor_app, u) as s:
        assert s.execute(text("select contenido from cv_base")).scalar_one() == "x"


# --- los evals ---------------------------------------------------------------------------------
@pytest.mark.usefixtures("limites_reales")
def test_el_eval_cv_base_incluye_casos_de_visibilidad_y_pasa_en_simulado():
    from pathlib import Path

    from horma.evals import correr_set
    raiz = Path(__file__).resolve().parent.parent / "evals"
    r = correr_set("cv-base", raiz=raiz, simulado=True)
    assert r["aprobado"] and r["casos"] >= 7 and r["campos"] == {"verificacion": 1.0, "ats": 1.0}
    nombres = {c.name for c in (raiz / "cv-base" / "casos").iterdir()}
    assert {"06-visibilidad-oculta", "07-visibilidad-condensada"} <= nombres


def test_la_pantalla_deja_marcar_cada_experiencia_y_avisa_que_se_aplica_al_regenerar():
    from pathlib import Path
    ruta = Path(__file__).resolve().parent.parent / "horma" / "web" / "static" / "cv-base.js"
    js = ruta.read_text("utf-8")
    assert "/visibilidad" in js and "Oculta" in js and "Condensada en una línea" in js
    assert "Qué experiencias salen" in js and "Regenerar" in js
