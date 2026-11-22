"""S9 · T51-T53: «Corregir explicación» amplía la información (RF-10.15 a 10.15e). Sin modelo real."""
# ruff: noqa: F401, F811  (fixtures importadas de otro módulo)
from pathlib import Path

import pytest
from sqlalchemy import text
from test_f2_t15_t19_api import _perfil_hecho, _puntuar
from test_f3_t08_t09_flujos import APROBADO, CARTA, MAESTRO, OFERTA
from test_f3_t14_t17_api import _candidatura, _fila, _oferta, app, archivos, entrar

from horma.flows.candidatura import TITULO_INFORMACION, maestro_con_informacion
from horma.flows.perfilar import conservar_usuaria
from horma.flows.registry import IMPLEMENTACIONES, crear_flujo
from horma.llm.simulado import ProveedorSimulado
from horma.web.db import sesion_de
from horma.web.queue import worker

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
INFO = "Carné de carretillera desde 2019"
CV_CON_INFO = {
    "contenido": f"## Experiencia\nCamarera en Bar Sol, 2020-2023\nManejo de TPV\n\n## Formación\n{INFO}",
    "traza": [{"frase": "Camarera en Bar Sol, 2020-2023", "fragmento": "Camarera en Bar Sol, 2020-2023"},
              {"frase": "Manejo de TPV", "fragmento": "Manejo de TPV"},
              {"frase": INFO, "fragmento": INFO}],
    "huecos": []}


def _estado(**extra):
    return {"usuaria_id": 7, "perfil_version": 2, "oferta": OFERTA, "cv_maestro": MAESTRO, **extra}


# --- T52 (sin base de datos): la información es una fuente más del flujo ----------------------------
def test_la_informacion_va_al_final_del_maestro_con_su_titulo():
    texto = maestro_con_informacion(MAESTRO, f"  {INFO}  ")
    assert texto.startswith(MAESTRO.rstrip()) and texto.rstrip().endswith(INFO)
    assert f"## {TITULO_INFORMACION}" in texto and "Información que añadiste para esta oferta" in texto
    assert maestro_con_informacion(MAESTRO, None) == MAESTRO
    assert maestro_con_informacion(MAESTRO, "   ") == MAESTRO


@pytest.mark.parametrize("impl", IMPLEMENTACIONES)
def test_el_redactor_la_carta_y_el_juez_reciben_la_informacion(impl):
    prov = ProveedorSimulado([CV_CON_INFO, CARTA, APROBADO])
    e = crear_flujo("candidatura", impl, proveedor=prov).run(_estado(informacion_usuaria=INFO))
    assert len(prov.llamadas) == 3
    for llamada in prov.llamadas:   # redactor del CV, redactor de la carta y juez
        assert INFO in llamada["usuario"] and TITULO_INFORMACION in llamada["usuario"]
    assert e["preparacion"] == "lista" and e["avisos"] == []   # la trazabilidad la acepta como fuente


@pytest.mark.parametrize("impl", IMPLEMENTACIONES)
def test_sin_informacion_nadie_la_recibe_y_la_frase_no_tiene_origen(impl):
    prov = ProveedorSimulado([CV_CON_INFO, CARTA, APROBADO, CV_CON_INFO, CARTA])
    e = crear_flujo("candidatura", impl, proveedor=prov).run(_estado())
    assert all(TITULO_INFORMACION not in x["usuario"] for x in prov.llamadas)
    assert e["preparacion"] == "pendiente_de_ti"
    assert any(a["documento"] == "cv" and INFO in (a.get("frase") or "") for a in e["avisos"])


@pytest.mark.parametrize("impl", IMPLEMENTACIONES)
def test_un_dato_que_no_esta_ni_en_el_perfil_ni_en_la_informacion_da_error_de_trazabilidad(impl):
    """RF-10.15b: Horma no amplía la información ni deduce nada de ella."""
    flujo = crear_flujo("candidatura", impl, proveedor=ProveedorSimulado([]))
    e = flujo.run_step("elegir_cv_base", _estado(informacion_usuaria=INFO))
    textos = {"cv_contenido": CV_CON_INFO["contenido"], "cv_traza": CV_CON_INFO["traza"],
              "carta_contenido": CARTA["contenido"], "carta_traza": CARTA["traza"]}
    assert flujo.run_step("comprobar", {**e, **textos})["errores_cv"] == []
    ampliada = "Carné de carretillera desde 2019 y de grúa torre desde 2021"
    malo = {**e, **textos, "cv_contenido": CV_CON_INFO["contenido"].replace(INFO, ampliada),
            "cv_traza": [*CV_CON_INFO["traza"][:2], {"frase": ampliada, "fragmento": INFO}]}
    assert flujo.run_step("comprobar", malo)["errores_cv"]
    inventada = {**e, **textos, "cv_contenido": CV_CON_INFO["contenido"] + "\nCarné de camión C desde 2015",
                 "cv_traza": [*CV_CON_INFO["traza"], {"frase": "Carné de camión C desde 2015",
                                                      "fragmento": "Carné de camión C desde 2015"}]}
    assert flujo.run_step("comprobar", inventada)["errores_cv"]


def test_los_prompts_no_cambian_por_la_informacion():
    """Decisión del 22-nov: entra como una fuente más, sin tocar los prompts (por eso no hay eval)."""
    agentes = Path(__file__).resolve().parent.parent / "horma" / "agents"
    for agente in ("redactor_cv", "redactor_carta", "juez_candidatura"):
        prompt = (agentes / agente / "prompt.md").read_text(encoding="utf-8")
        assert "añadiste para esta oferta" not in prompt and "informacion_usuaria" not in prompt


def test_rehacer_el_perfil_conserva_las_propuestas_pendientes():
    propuesta = {"campo": "propuesta", "motivo": "falta", "pregunta": "¿La guardas?", "opciones": [INFO]}
    perfil = {"experiencias": [], "formacion": [], "idiomas": [], "habilidades": [], "proyectos": [],
              "certificaciones": [], "otros": [], "actividades": [], "titular": None, "resumen": None,
              "nombre": None, "genero_puestos": None,
              "preguntas_pendientes": [
                  {"campo": "idiomas", "motivo": "falta", "pregunta": "¿?", "opciones": []}]}
    conservar_usuaria(perfil, {"propuestas": [propuesta]})
    assert perfil["preguntas_pendientes"][-1] == propuesta and len(perfil["preguntas_pendientes"]) == 2


# --- Pantallas (estático) ------------------------------------------------------------------------
def test_el_formulario_de_corregir_tiene_el_campo_y_la_ayuda():
    js = (ESTATICOS / "ofertas.js").read_text(encoding="utf-8")
    textos = (ESTATICOS / "textos.js").read_text(encoding="utf-8")
    assert "Información nueva sobre ti" in textos
    assert "Algo que no consta en tu CV y que Horma puede usar en esta oferta" in textos
    for pieza in ("TEXTOS.informacionNueva", "TEXTOS.informacionAyuda", "TEXTOS.corregirAyuda",
                  "informacion:"):
        assert pieza in js, pieza
    ayuda = textos.split("corregirAyuda:")[1].split("\n")[0]
    for idea in ("no cambian la compatibilidad", "candidaturas nuevas de esta oferta", "confirmes"):
        assert idea in ayuda, idea


def test_tras_enviar_pregunta_si_guardarla_en_el_perfil():
    js = (ESTATICOS / "ofertas.js").read_text(encoding="utf-8")
    textos = (ESTATICOS / "textos.js").read_text(encoding="utf-8")
    for texto in ("¿Guardarla también en tu perfil para futuras candidaturas?", "Sí, revisarla",
                  "No, solo para esta oferta"):
        assert texto in textos, texto
    assert "/informacion/perfil" in js and "TEXTOS.guardarEnPerfil" in js


def test_perfil_ensena_la_propuesta_con_editar_colocar_y_descartar():
    js = (ESTATICOS / "perfil.js").read_text(encoding="utf-8")
    assert '"propuesta"' in js and "SECCIONES_PROPUESTA" in js and "Descartar" in js
    for seccion in ("experiencias", "habilidades", "formacion", "otros"):
        assert seccion in js.split("SECCIONES_PROPUESTA =")[1].split(";")[0], seccion


# --- Con base de datos -----------------------------------------------------------------------------
def _con_nota(app, motor, sub="google-A"):
    c, h, u = entrar(app, sub)
    _perfil_hecho(motor, u)
    oferta = _oferta(motor)
    _puntuar(motor, u, 1, (oferta, 60))
    return c, h, u, oferta


def _corregir(c, h, oferta, **extra):
    return c.post(f"/api/matches/{oferta}/correccion", headers=h,
                  json={"comentario": "Falta un dato.", **extra})


def _perfil_api(c):
    return c.get("/api/perfil").json()["perfil"]


@pytest.mark.bd
def test_la_correccion_guarda_la_informacion_y_sin_ella_sigue_valiendo(app, motor_app):
    c, h, u, oferta = _con_nota(app, motor_app)
    r = _corregir(c, h, oferta)
    assert r.status_code == 200 and r.json()["informacion"] is None
    r = _corregir(c, h, oferta, nota=70, informacion=f"  {INFO} ")
    assert r.status_code == 200 and r.json()["informacion"] == INFO
    with sesion_de(motor_app, u) as s:
        guardada = s.execute(text("select correccion from matches where oferta_id = :o"),
                             {"o": oferta}).scalar_one()
    assert guardada["informacion"] == INFO and guardada["nota"] == 70
    assert _corregir(c, h, oferta, informacion="   ").json()["informacion"] is None
    assert _corregir(c, h, oferta, informacion="x" * 1001).status_code == 422
    assert "informacion" not in str(c.get(f"/api/matches/{oferta}/exportar").json()["esperado"])


@pytest.mark.bd
def test_otra_usuaria_no_puede_anadir_informacion_a_esa_correccion(app, motor_app):
    c, h, u, oferta = _con_nota(app, motor_app)
    b, hb, _ = entrar(app, "google-B")
    assert _corregir(b, hb, oferta, informacion=INFO).status_code == 404
    assert b.post(f"/api/matches/{oferta}/informacion/perfil", headers=hb).status_code == 404


@pytest.mark.bd
def test_la_candidatura_nueva_lleva_la_informacion_y_la_ya_preparada_no(app, motor_app):
    c, h, u, oferta = _con_nota(app, motor_app)
    otra = _oferta(motor_app, titulo="Cocinera")
    _puntuar(motor_app, u, 1, (otra, 55))
    previa = _candidatura(motor_app, u, oferta)   # preparada antes de corregir
    _corregir(c, h, oferta, informacion=INFO)
    assert _fila(motor_app, u, previa)["informacion"] is None
    cierre = c.post(f"/api/candidaturas/{previa}/cerrar", headers=h, json={"motivo": "retirada"})
    assert cierre.status_code == 200, cierre.text
    r = c.post("/api/candidaturas", headers=h, json={"oferta_id": oferta, "repetir": True})
    assert r.status_code == 202, r.text
    nueva = r.json()["id"]
    assert _fila(motor_app, u, nueva)["informacion"] == INFO
    sin = c.post("/api/candidaturas", headers=h, json={"oferta_id": otra}).json()["id"]
    assert _fila(motor_app, u, sin)["informacion"] is None   # la información es solo de su oferta
    with sesion_de(motor_app, u) as s:
        carga = worker._Candidatura()
        assert carga.cargar(s, {"entidad_id": nueva, "usuaria_id": u})["informacion_usuaria"] == INFO
        assert carga.cargar(s, {"entidad_id": previa, "usuaria_id": u})["informacion_usuaria"] is None
        assert carga.cargar(s, {"entidad_id": sin, "usuaria_id": u})["informacion_usuaria"] is None


@pytest.mark.bd
def test_al_editar_la_candidatura_se_comprueba_con_la_informacion_que_llevaba(app, motor_app):
    c, h, u, oferta = _con_nota(app, motor_app)
    otra = _oferta(motor_app, titulo="Cocinera")
    preparada = {"cv_contenido": CV_CON_INFO["contenido"], "cv_traza": CV_CON_INFO["traza"]}
    con = _candidatura(motor_app, u, oferta, informacion=INFO, **preparada)
    sin = _candidatura(motor_app, u, otra, **preparada)
    carta = "Hola, equipo:\nTrabajé en Bar Sol desde 2020.\nUn saludo"

    def avisos_del_cv(cid):
        r = c.patch(f"/api/candidaturas/{cid}", headers=h, json={"carta_contenido": carta})
        assert r.status_code == 200, r.text
        return [a for a in r.json()["avisos"] if a["documento"] == "cv" and INFO in str(a)]
    assert avisos_del_cv(con) == []
    assert avisos_del_cv(sin)


@pytest.mark.bd
def test_no_solo_para_esta_oferta_no_toca_el_perfil(app, motor_app):
    c, h, u, oferta = _con_nota(app, motor_app)
    antes = _perfil_api(c)
    _corregir(c, h, oferta, informacion=INFO)
    assert _perfil_api(c) == antes


@pytest.mark.bd
def test_si_revisarla_anade_la_propuesta_sin_cambiar_el_perfil(app, motor_app):
    c, h, u, oferta = _con_nota(app, motor_app)
    antes = c.get("/api/perfil").json()
    ruta = f"/api/matches/{oferta}/informacion/perfil"
    assert c.post(ruta, headers=h).status_code == 404   # sin corrección
    _corregir(c, h, oferta)
    assert c.post(ruta, headers=h).status_code == 404   # sin información
    _corregir(c, h, oferta, informacion=INFO)
    assert c.post(ruta).status_code == 403   # sin CSRF
    r = c.post(ruta, headers=h)
    assert r.status_code == 201, r.text
    assert c.post(ruta, headers=h).status_code == 201   # no se duplica
    ahora = c.get("/api/perfil").json()
    propuestas = [p for p in ahora["perfil"]["preguntas_pendientes"] if p["campo"] == "propuesta"]
    assert len(propuestas) == 1 and propuestas[0]["opciones"] == [INFO]
    assert ahora["perfil"]["version"] == antes["perfil"]["version"] == 1
    assert ahora["cv_maestro"] == antes["cv_maestro"] and INFO not in ahora["cv_maestro"]
    sin_pendientes = {k: v for k, v in ahora["perfil"].items() if k != "preguntas_pendientes"}
    assert sin_pendientes == {k: v for k, v in antes["perfil"].items() if k != "preguntas_pendientes"}
    with sesion_de(motor_app, u) as s:
        assert s.execute(text("select count(*) from perfiles")).scalar_one() == 1
        assert s.execute(text("select count(*) from tareas")).scalar_one() == 0   # sin modelo


def _proponer(c, h, oferta):
    _corregir(c, h, oferta, informacion=INFO)
    assert c.post(f"/api/matches/{oferta}/informacion/perfil", headers=h).status_code == 201
    pendientes = _perfil_api(c)["preguntas_pendientes"]
    return next(i for i, p in enumerate(pendientes) if p["campo"] == "propuesta")


@pytest.mark.bd
def test_confirmar_la_propuesta_crea_la_version_y_deja_desfasado_lo_anterior(app, motor_app):
    c, h, u, oferta = _con_nota(app, motor_app)
    cid = _candidatura(motor_app, u, oferta)
    i = _proponer(c, h, oferta)
    assert c.get(f"/api/candidaturas/{cid}").json()["desfasada"] is False
    sin_seccion = c.post("/api/perfil/respuestas", headers=h, json={"indice": i, "dato": {"nombre": INFO}})
    assert sin_seccion.status_code == 422
    mala = c.post("/api/perfil/respuestas", headers=h,
                  json={"indice": i, "campo": "idiomas", "dato": {"idioma": "en"}})
    assert mala.status_code == 422 and _perfil_api(c)["version"] == 1
    editada = "Carné de carretillera (2019)"   # ella puede editarla antes de guardarla
    r = c.post("/api/perfil/respuestas", headers=h,
               json={"indice": i, "campo": "habilidades", "dato": {"nombre": editada}})
    assert r.status_code == 201, r.text
    assert r.json()["version"] == 2 and r.json()["cambio"] == {"campo": "habilidades", "valor": editada}
    p = c.get("/api/perfil").json()
    assert p["perfil"]["habilidades"][-1]["nombre"] == editada
    assert p["perfil"]["habilidades"][-1]["origen"]["fuente"] == "usuaria"
    assert all(x["campo"] != "propuesta" for x in p["perfil"]["preguntas_pendientes"])
    assert editada in p["cv_maestro"]
    assert c.get(f"/api/candidaturas/{cid}").json()["desfasada"] is True


@pytest.mark.bd
@pytest.mark.parametrize("campo, dato", [
    ("experiencias", {"puesto": "Carretillera", "descripcion": INFO}),
    ("formacion", {"titulo": INFO}),
    ("otros", {"valor": INFO}),
])
def test_la_propuesta_se_puede_colocar_en_las_otras_secciones(app, motor_app, campo, dato):
    c, h, u, oferta = _con_nota(app, motor_app)
    i = _proponer(c, h, oferta)
    r = c.post("/api/perfil/respuestas", headers=h, json={"indice": i, "campo": campo, "dato": dato})
    assert r.status_code == 201, r.text
    guardado = _perfil_api(c)[campo][-1]
    assert guardado["origen"]["fuente"] == "usuaria" and INFO in guardado.values()


@pytest.mark.bd
def test_descartar_la_propuesta_la_quita_sin_crear_version(app, motor_app):
    c, h, u, oferta = _con_nota(app, motor_app)
    cid = _candidatura(motor_app, u, oferta)
    i = _proponer(c, h, oferta)
    r = c.post("/api/perfil/respuestas", headers=h, json={"indice": i, "dato": None})
    assert r.status_code == 201, r.text
    p = _perfil_api(c)
    assert p["version"] == 1 and all(x["campo"] != "propuesta" for x in p["preguntas_pendientes"])
    assert len(p["preguntas_pendientes"]) == 1   # la pregunta que ya había sigue ahí
    assert c.get(f"/api/candidaturas/{cid}").json()["desfasada"] is False
    with sesion_de(motor_app, u) as s:
        assert s.execute(text("select count(*) from perfiles")).scalar_one() == 1


@pytest.mark.bd
def test_al_rehacer_el_perfil_el_worker_lleva_las_propuestas(app, motor_app):
    from horma.web.repositories import perfiles
    c, h, u, oferta = _con_nota(app, motor_app)
    _proponer(c, h, oferta)
    with sesion_de(motor_app, u) as s:
        suyo = perfiles.lo_de_la_usuaria(s, u)
    assert [p["opciones"] for p in suyo["propuestas"]] == [[INFO]]
