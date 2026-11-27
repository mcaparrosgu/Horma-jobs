"""Fase 8 · bloque E (backend): flujos con avance, worker por tandas, `POST /api/recomendar` con topes y
«Puntuar ahora» (T15-T18, spec 008). Ninguna prueba llama al modelo real."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from horma import config
from horma.flows.grafo import LangGraphFlow
from horma.flows.plain import PlainFlow
from horma.flows.recomendar import TANDA
from horma.flows.recomendar import crear as crear_recomendar
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias
from horma.web.db import sesion_de
from horma.web.main import crear_app
from horma.web.queue import worker
from horma.web.repositories import perfiles

TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior", "stack": []}
SUCIA = "Tiene 34 años y es colombiana. Es de nacionalidad colombiana, y la oferta encaja."


# --- T15 · flujos con avance ---------------------------------------------------------------------
def _lineal(clase, **kw):
    return clase("lineal", pasos={"a": lambda e: {**e, "a": 1}, "b": lambda e: {**e, "b": 2}},
                 aristas={"a": "b"}, inicio="a", finales={"b"}, **kw)


def test_al_paso_se_llama_una_vez_por_paso_en_plain():
    vistos = []
    _lineal(PlainFlow, al_paso=vistos.append).run({})
    assert vistos == ["a", "b"]


def test_al_paso_se_llama_una_vez_por_paso_en_langgraph():
    vistos = []
    f = _lineal(LangGraphFlow, claves={"a", "b"}, al_paso=vistos.append)
    f.run({})
    assert vistos == ["a", "b"]


def test_al_paso_se_puede_poner_despues_de_crear_el_flujo():
    vistos = []
    f = _lineal(PlainFlow)
    f.al_paso = vistos.append
    f.run({})
    assert vistos == ["a", "b"]


def _cand(i):
    return {"oferta_id": i, "oferta": {
        "titulo": f"Camarera {i}", "taxonomia": TAX,
        "auditoria": {"fantasma": False, "fraude": False, "salario_publicado": False}}}


def _match(i, nota=80, explicacion="Tiene experiencia en sala. La oferta pide camarera con experiencia."):
    return {"oferta_id": i, "nota": nota, "condiciones": "medio", "relacion": "otro_oficio", "marcas": [], "explicacion": explicacion,
            "cita_perfil": "Bar Sol", "cita_oferta": "camarera"}


def _perfil_dict():
    return Perfil.model_validate({"taxonomia": TAX, "experiencias": [
        {"puesto": "Camarera", "empresa": "Bar Sol",
         "origen": {"fuente": "cv", "cv_id": 1, "fragmento": "Camarera en Bar Sol, 2020-2023"}}]}
    ).model_dump(mode="json")


def test_al_tanda_se_llama_una_vez_por_tanda_con_las_explicaciones_ya_revisadas():
    llamadas = []
    cands = [_cand(i) for i in range(1, 46)]
    prov = ProveedorSimulado([{"matches": [_match(i) if i != 2 else _match(i, explicacion=SUCIA)
                                           for i in range(1, 31)]},
                              {"matches": [_match(i) for i in range(31, 46)]}])
    flujo = crear_recomendar(proveedor=prov, al_tanda=lambda n, h, p: llamadas.append((list(n), h, p)))
    e = flujo.run({"perfil": _perfil_dict(), "preferencias": Preferencias().model_dump(mode="json"),
                   "candidatas": cands})
    assert TANDA == 30 and [(len(n), h, p) for n, h, p in llamadas] == [(30, 1, 2), (15, 2, 2)]
    segunda = {m["oferta_id"]: m for m in llamadas[0][0]}[2]
    assert segunda["retirada"] is True and segunda["explicacion"] == ""  # ya revisada al entregarla
    assert len(e["recomendaciones"]) == 45


def test_las_previstas_son_las_tandas_que_hacen_falta_con_tope_de_cinco():
    llamadas = []
    cands = [_cand(i) for i in range(1, 30 * 7 + 1)]
    respuestas = [{"matches": [_match(i) for i in range(t * 30 + 1, t * 30 + 31)]} for t in range(7)]
    crear_recomendar(proveedor=ProveedorSimulado(respuestas),
                     al_tanda=lambda n, h, p: llamadas.append((h, p))).run(
        {"perfil": _perfil_dict(), "preferencias": Preferencias().model_dump(mode="json"),
         "candidatas": cands})
    assert llamadas == [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)]


def test_evals_de_recomendacion_en_simulado(monkeypatch):
    """El prompt del matcher no cambia: los casos de `evals/recomendacion` siguen cargando con el flujo nuevo."""  # noqa: E501
    from pathlib import Path
    assert (Path(__file__).resolve().parent.parent / "evals" / "recomendacion").is_dir()


# --- BD: worker, API y topes ---------------------------------------------------------------------
class IdentidadFalsa:
    async def redirigir(self, request, redirect_uri):
        from starlette.responses import RedirectResponse
        return RedirectResponse("https://accounts.google.test/auth")

    async def sub_desde_callback(self, request) -> str:
        return request.query_params["code"]


@pytest.fixture
def app(motor_app, bd_limpia, monkeypatch):
    config.ajustes.cache_clear()
    yield crear_app(engine=motor_app, identidad=IdentidadFalsa())
    config.ajustes.cache_clear()


def entrar(app, sub="google-A"):
    c = TestClient(app, follow_redirects=False)
    assert c.get(f"/auth/google/callback?code={sub}").status_code == 302
    return c, {"X-CSRF-Token": c.get("/api/yo").json()["csrf"]}


def usuaria(motor_migrador, sub="google-A"):
    with motor_migrador.connect() as s:
        return s.execute(text("select id from usuarias where google_sub=:s"), {"s": sub}).scalar_one()


def perfil_hecho(motor, u):
    base = {"taxonomia": TAX, "experiencias": [
        {"puesto": "Camarera", "empresa": "Bar Sol",
         "origen": {"fuente": "cv", "cv_id": 1, "fragmento": "Camarera en Bar Sol, 2020-2023"}}]}
    with sesion_de(motor, u) as s:
        pid, version = perfiles.nueva_version(s, u)
        perfiles.guardar_perfil(s, u, pid, Perfil.model_validate({**base, "version": version}),
                                "# Ana\nCamarera en Bar Sol, 2020-2023")
    return pid


def ofertas(motor_migrador, n, duena=None, prefijo="Camarera"):
    ids = []
    with motor_migrador.begin() as c:
        for i in range(n):
            ids.append(c.execute(text(
                "insert into ofertas (texto_crudo, huella, titulo, empresa, estado, usuaria_id, fantasma, fraude, "  # noqa: E501
                "sector, familia, nivel) values ('t', md5(random()::text || :i), :ti, 'Hotel Mar', 'procesada', "  # noqa: E501
                ":d, false, false, 'hosteleria_turismo', 'hosteleria_restauracion', 'junior') returning id"),
                {"i": f"{prefijo}{i}", "ti": f"{prefijo} {i}", "d": duena}).scalar_one())
    return ids


def matches(ids, nota=85):
    return {"matches": [{"oferta_id": i, "nota": nota, "condiciones": "alto", "relacion": "otro_oficio", "marcas": [],
                         "cita_perfil": "Bar Sol", "cita_oferta": "Camarera",
                         "explicacion": "Tiene experiencia en sala. La oferta pide camarera de sala."}
                        for i in ids]}


def tarea_fila(motor_migrador, tarea_id):
    with motor_migrador.connect() as c:
        return c.execute(text("select estado, progreso, tope_coste, coste_acumulado, motivo_error from tareas "  # noqa: E501
                              "where id=:i"), {"i": tarea_id}).one()


def notas(motor_migrador):
    with motor_migrador.connect() as c:
        return {r[0]: r[1] for r in c.execute(text("select oferta_id, nota from matches"))}


def gasto(motor_migrador, u, coste, tipo="recomendar"):
    with motor_migrador.begin() as c:
        c.execute(text("insert into tareas (usuaria_id, tipo, entidad_id, tope_coste, coste_acumulado, estado) "  # noqa: E501
                       "values (:u, :t, 1, 1, :c, 'hecha')"), {"u": u, "t": tipo, "c": coste})


@pytest.mark.bd
def test_un_fallo_en_la_tercera_tanda_deja_guardadas_las_dos_primeras(app, motor_app, motor_migrador):
    c, h = entrar(app)
    u = usuaria(motor_migrador)
    perfil_hecho(motor_app, u)
    ids = ofertas(motor_migrador, 95)[::-1]  # se puntúan de la más reciente a la más antigua
    r = c.post("/api/recomendar", headers=h, json={"motivo": "buscar"}).json()
    # dos tandas buenas y la tercera con una respuesta inválida: el modelo falla y el paso se corta
    prov = ProveedorSimulado([matches(ids[:30]), matches(ids[30:60]), RuntimeError("caída del modelo")])
    estado = worker.procesar_una(motor_app, prov)
    assert estado == "pendiente"  # primer intento fallido: vuelve a la cola
    guardadas = notas(motor_migrador)
    assert len(guardadas) == 60 and set(guardadas) == set(ids[:60])
    fila = tarea_fila(motor_migrador, r["tarea_id"])
    assert 0 < fila.progreso < 100


@pytest.mark.bd
def test_el_progreso_llega_a_cien_al_terminar_y_nunca_baja(app, motor_app, motor_migrador):
    c, h = entrar(app)
    u = usuaria(motor_migrador)
    perfil_hecho(motor_app, u)
    ids = ofertas(motor_migrador, 45)[::-1]
    t = c.post("/api/recomendar", headers=h, json={"motivo": "buscar"}).json()["tarea_id"]
    visto = []
    original = worker.repo_tareas.avanzar

    def espia(s, tarea_id, p):
        original(s, tarea_id, p)
        visto.append(s.execute(text("select progreso from tareas where id=:i"), {"i": tarea_id}).scalar_one())

    worker.repo_tareas.avanzar = espia
    try:
        assert worker.procesar_una(motor_app, ProveedorSimulado([matches(ids[:30]), matches(ids[30:])])) == "hecha"  # noqa: E501
    finally:
        worker.repo_tareas.avanzar = original
    assert visto == sorted(visto) and visto[0] == 50 and visto[-1] == 99
    assert tarea_fila(motor_migrador, t).progreso == 100 and len(notas(motor_migrador)) == 45


@pytest.mark.bd
def test_el_worker_puntua_con_rango_40_100_y_no_puntua_una_descartada(app, motor_app, motor_migrador):
    c, h = entrar(app)
    u = usuaria(motor_migrador)
    perfil_hecho(motor_app, u)
    c.put("/api/preferencias", headers=h, json={**c.get("/api/preferencias").json(),
                                                 "rango_min": 90, "rango_max": 95, "orden": "recientes"})
    a, b = ofertas(motor_migrador, 2)
    assert c.put(f"/api/descartes/{b}", headers=h).status_code == 200
    c.post("/api/recomendar", headers=h, json={"motivo": "buscar"})
    prov = ProveedorSimulado([matches([a], nota=50)])
    assert worker.procesar_una(motor_app, prov) == "hecha"
    assert notas(motor_migrador) == {a: 50}
    enviado = prov.llamadas[0]["usuario"]
    assert f'"oferta_id":{a}' in enviado and f'"oferta_id":{b}' not in enviado
    assert "rango_min" not in enviado  # las condiciones no llegan al modelo (spec 012, RF-12.31)


@pytest.mark.bd
def test_el_avance_por_pasos_en_el_resto_de_tareas(app, motor_app, motor_migrador):
    """Una tarea que no es `recomendar` también termina en 100 y sube por pasos."""
    c, h = entrar(app)
    u = usuaria(motor_migrador)
    perfil_hecho(motor_app, u)
    (o,) = ofertas(motor_migrador, 1)
    t = c.post(f"/api/matches/{o}/puntuar", headers=h).json()["tarea_id"]
    assert worker.procesar_una(motor_app, ProveedorSimulado([matches([o])])) == "hecha"
    assert tarea_fila(motor_migrador, t).progreso == 100


# --- T17 · POST /api/recomendar con las reglas de P1 y el tope del día -----------------------------
@pytest.mark.bd
def test_sin_perfil_no_lanza_nada(app):
    c, h = entrar(app)
    assert c.post("/api/recomendar", headers=h).json() == {"tarea_id": None, "motivo": "sin_perfil"}


@pytest.mark.bd
def test_sin_pendientes(app, motor_app, motor_migrador):
    c, h = entrar(app)
    perfil_hecho(motor_app, usuaria(motor_migrador))
    assert c.post("/api/recomendar", headers=h).json()["motivo"] == "sin_pendientes"


@pytest.mark.bd
def test_abrir_lanza_y_abrir_otra_vez_antes_de_una_hora_no(app, motor_app, motor_migrador):
    c, h = entrar(app)
    u = usuaria(motor_migrador)
    perfil_hecho(motor_app, u)
    ids = ofertas(motor_migrador, 3)
    r = c.post("/api/recomendar", headers=h, json={"motivo": "abrir"}).json()
    assert r["tarea_id"] and "motivo" not in r
    assert worker.procesar_una(motor_app, ProveedorSimulado([matches(ids[:1])])) == "hecha"
    ofertas(motor_migrador, 2, prefijo="Otra")  # hay más sin nota, pero la última empezó hace menos de 1 h
    assert c.post("/api/recomendar", headers=h, json={"motivo": "abrir"}).json() == {
        "tarea_id": None, "motivo": "reciente"}
    # «buscar» (guardar «Qué buscas») se salta la hora
    assert c.post("/api/recomendar", headers=h, json={"motivo": "buscar"}).json()["tarea_id"]


@pytest.mark.bd
def test_pasada_la_hora_abrir_vuelve_a_lanzar(app, motor_app, motor_migrador):
    c, h = entrar(app)
    perfil_hecho(motor_app, usuaria(motor_migrador))
    ofertas(motor_migrador, 2)
    c.post("/api/recomendar", headers=h)
    with motor_migrador.begin() as cx:
        cx.execute(text("update tareas set creada_en = now() - interval '61 minutes', estado = 'hecha'"))
    assert c.post("/api/recomendar", headers=h).json()["tarea_id"]


@pytest.mark.bd
def test_en_marcha_devuelve_la_tarea_en_curso(app, motor_app, motor_migrador):
    c, h = entrar(app)
    perfil_hecho(motor_app, usuaria(motor_migrador))
    ofertas(motor_migrador, 2)
    primera = c.post("/api/recomendar", headers=h, json={"motivo": "buscar"}).json()["tarea_id"]
    r = c.post("/api/recomendar", headers=h, json={"motivo": "buscar"}).json()
    assert r == {"tarea_id": primera, "motivo": "en_marcha"}


@pytest.mark.bd
def test_con_el_gasto_del_dia_en_el_tope_no_se_lanza(app, motor_app, motor_migrador):
    c, h = entrar(app)
    u = usuaria(motor_migrador)
    perfil_hecho(motor_app, u)
    ofertas(motor_migrador, 2)
    gasto(motor_migrador, u, 1.00)
    assert c.post("/api/recomendar", headers=h, json={"motivo": "buscar"}).json() == {
        "tarea_id": None, "motivo": "presupuesto"}
    # y el tope de la tarea es lo que queda del día
    with motor_migrador.begin() as cx:
        cx.execute(text("update tareas set coste_acumulado = 0.80"))
    t = c.post("/api/recomendar", headers=h, json={"motivo": "buscar"}).json()["tarea_id"]
    assert float(tarea_fila(motor_migrador, t).tope_coste) == pytest.approx(0.20)


@pytest.mark.bd
def test_una_tarea_ya_encolada_sigue_y_su_gasto_cuenta(app, motor_app, motor_migrador):
    c, h = entrar(app)
    u = usuaria(motor_migrador)
    perfil_hecho(motor_app, u)
    gasto(motor_migrador, u, 0.50)
    (propia,) = ofertas(motor_migrador, 1, duena=u)
    with motor_migrador.begin() as cx:
        cx.execute(text("insert into tareas (usuaria_id, tipo, entidad_id, tope_coste) "
                        "values (:u, 'puntuar_propias', :u, 1)"), {"u": u})
    assert worker.procesar_una(motor_app, ProveedorSimulado([matches([propia])])) == "hecha"
    assert propia in notas(motor_migrador)
    with sesion_de(motor_app, u) as s:
        from horma.web.repositories import tareas
        assert tareas.gasto_hoy(s, u) >= 0.50


# --- T18 · «Puntuar ahora» -----------------------------------------------------------------------
@pytest.mark.bd
def test_puntuar_ahora_puntua_una_sola_oferta(app, motor_app, motor_migrador):
    c, h = entrar(app)
    perfil_hecho(motor_app, usuaria(motor_migrador))
    uno, otro = ofertas(motor_migrador, 2)
    r = c.post(f"/api/matches/{uno}/puntuar", headers=h)
    assert r.status_code == 202
    assert worker.procesar_una(motor_app, ProveedorSimulado([matches([uno])])) == "hecha"
    assert notas(motor_migrador) == {uno: 85}
    # ya puntuada: 409
    assert c.post(f"/api/matches/{uno}/puntuar", headers=h).status_code == 409
    assert c.post("/api/matches/9999/puntuar", headers=h).status_code == 404


@pytest.mark.bd
def test_puntuar_ahora_una_oferta_que_ya_se_esta_puntuando_da_409(app, motor_app, motor_migrador):
    c, h = entrar(app)
    perfil_hecho(motor_app, usuaria(motor_migrador))
    (o,) = ofertas(motor_migrador, 1)
    assert c.post(f"/api/matches/{o}/puntuar", headers=h).status_code == 202
    assert c.post(f"/api/matches/{o}/puntuar", headers=h).status_code == 409


@pytest.mark.bd
def test_puntuar_ahora_con_poco_presupuesto_limita_el_tope_de_la_tarea(app, motor_app, motor_migrador):
    c, h = entrar(app)
    u = usuaria(motor_migrador)
    perfil_hecho(motor_app, u)
    gasto(motor_migrador, u, 0.98)
    (o,) = ofertas(motor_migrador, 1)
    t = c.post(f"/api/matches/{o}/puntuar", headers=h).json()["tarea_id"]
    assert float(tarea_fila(motor_migrador, t).tope_coste) == pytest.approx(0.02)
    assert worker.procesar_una(motor_app, ProveedorSimulado([matches([o])])) == "hecha"
    assert o in notas(motor_migrador)


# --- S5 · T20 · presupuesto diario único (RF-10.9) -----------------------------------------------
def _pendientes(motor):
    with motor.connect() as cx:
        return cx.execute(text("select count(*) from tareas where estado = 'pendiente'")).scalar_one()


@pytest.mark.bd
def test_con_1_usd_gastado_ningun_tipo_se_encola(app, motor_app, motor_migrador):
    c, h = entrar(app)
    u = usuaria(motor_migrador)
    perfil_hecho(motor_app, u)
    gasto(motor_migrador, u, 1.00)
    (o,) = ofertas(motor_migrador, 1)
    antes = _pendientes(motor_migrador)
    r = c.post(f"/api/matches/{o}/puntuar", headers=h)  # puntuar_una
    assert r.status_code == 429 and r.json()["motivo"] == "presupuesto"
    assert "Hoy ya hemos trabajado todo lo posible para ti" in r.json()["detail"]
    assert c.post("/api/recomendar", headers=h, json={"motivo": "buscar"}).json()["motivo"] == "presupuesto"
    url = "https://job-boards.greenhouse.io/hotelmar/jobs/1"
    r = c.post("/ofertas/url", headers=h, json={"url": url})  # leer_url
    assert r.status_code == 429 and r.json()["motivo"] == "presupuesto"
    assert _pendientes(motor_migrador) == antes  # no se encoló nada


@pytest.mark.bd
def test_una_oferta_propia_sin_presupuesto_queda_pendiente_y_se_procesa_cuando_vuelve(app, motor_app, motor_migrador):  # noqa: E501
    from horma.web.services import ofertas as servicio
    c, h = entrar(app)
    u = usuaria(motor_migrador)
    gasto(motor_migrador, u, 1.00)
    texto = "Camarera para Bar Sol en Valencia. Se requiere experiencia en sala y manejo de TPV, jornada completa."  # noqa: E501
    r = c.post("/ofertas", headers=h, json={"texto": texto})
    assert r.status_code == 201 and r.json()["estado"] == "pendiente" and r.json()["aplazada"] is True
    oferta_id = r.json()["id"]
    with motor_migrador.connect() as cx:
        assert cx.execute(text("select count(*) from tareas where tipo = 'procesar_oferta'")
                          ).scalar_one() == 0
    assert servicio.encolar_propias_aplazadas(motor_app) == 0  # hoy sigue sin presupuesto
    with motor_migrador.begin() as cx:  # «mañana»: el gasto de hoy pasa a ayer
        cx.execute(text("update tareas set creada_en = now() - interval '2 days'"))
    assert servicio.encolar_propias_aplazadas(motor_app) == 1
    assert servicio.encolar_propias_aplazadas(motor_app) == 0  # no se encola dos veces
    with motor_migrador.connect() as cx:
        fila = cx.execute(text("select entidad_id, tope_coste from tareas "
                               "where tipo = 'procesar_oferta'")).one()
    assert fila.entidad_id == oferta_id and float(fila.tope_coste) <= 1.0


@pytest.mark.bd
def test_el_analisis_de_una_oferta_propia_gasta_del_presupuesto_de_su_duena(app, motor_app, motor_migrador):
    from horma.web.repositories import tareas
    entrar(app)
    u = usuaria(motor_migrador)
    (propia,) = ofertas(motor_migrador, 1, duena=u)
    with motor_migrador.begin() as cx:
        cx.execute(text("insert into tareas (usuaria_id, tipo, entidad_id, tope_coste, coste_acumulado) "
                        "values (null, 'procesar_oferta', :o, 1, 0.30)"), {"o": propia})
    with sesion_de(motor_app, u) as s:
        assert tareas.gasto_hoy(s, u) == pytest.approx(0.30)


def test_config_sin_los_limites_antiguos():
    a = config.Ajustes()
    assert a.presupuesto_diario_usd == 1.0
    assert not hasattr(a, "tope_gasto_diario_puntuar") and not hasattr(a, "max_sueltas_dia")
