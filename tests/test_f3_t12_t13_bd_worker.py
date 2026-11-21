"""Fase 3 · T12-T13: esquema de candidaturas (migraciones 0006 y 0007), historial, versiones de CV base,
RLS, índice único y worker `candidatura` (puerta simulada) (RF-3.7, RF-3.7b, RF-3.8d, RF-3.10, RF-3.11,
RT-14). La migración 0007 y el tope de coste tienen su propio fichero (T28-T29)."""
import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from horma.config import ajustes
from horma.llm.simulado import ProveedorSimulado
from horma.web.db import sesion_de, sesion_sin_usuaria, sesion_sistema
from horma.web.queue import worker
from horma.web.repositories import tareas

pytestmark = pytest.mark.bd

MAESTRO = "# Ana Pérez\n\n## Experiencia\nCamarera en Bar Sol, 2020-2023\nManejo de TPV\n"
BASE = "## Experiencia\nCamarera en Bar Sol, 2020-2023\nManejo de TPV"
CV = {"contenido": "## Experiencia\nCamarera en Bar Sol, 2020-2023\nManejo de TPV",
      "traza": [{"frase": "Camarera en Bar Sol, 2020-2023", "fragmento": "Camarera en Bar Sol, 2020-2023"},
                {"frase": "Manejo de TPV", "fragmento": "Manejo de TPV"}], "huecos": []}
APROBADO = {"veredicto_cv": "aprobado", "veredicto_carta": "aprobado", "problemas": []}
CARTA = {"contenido": "Hola equipo,\nTrabajé en Bar Sol desde 2020.\nUn saludo",
         "traza": [{"frase": "Trabajé en Bar Sol desde 2020.",
                    "fragmento": "Camarera en Bar Sol, 2020-2023"}]}
FELIZ = [CV, CARTA, APROBADO]


def _usuarias(motor):
    with sesion_sin_usuaria(motor) as s:
        a = s.execute(text("select obtener_o_crear_usuaria('google-A')")).scalar_one()
        b = s.execute(text("select obtener_o_crear_usuaria('google-B')")).scalar_one()
    return a, b


def _oferta(motor):
    with sesion_sistema(motor) as s:
        return s.execute(text(
            "insert into ofertas (texto_crudo, estado, titulo, empresa, requisitos, sector, familia, nivel) "
            "values ('texto', 'procesada', 'Camarera', 'Bar Luna', cast('[\"inglés\"]' as jsonb), "
            "'hosteleria_turismo', 'hosteleria_restauracion', 'junior') returning id")).scalar_one()


def _perfil_y_cv_base(motor, u, n_cv_base=1):
    """Perfil v1 hecho con su CV maestro y `n_cv_base` CV base válidos."""
    with sesion_de(motor, u) as s:
        s.execute(text("insert into perfiles (usuaria_id, version, estado, cv_maestro) "
                       "values (:u, 1, 'hecha', :m)"), {"u": u, "m": MAESTRO})
        return [s.execute(text(
            "insert into cv_base (usuaria_id, perfil_version, nombre, sector, familia, contenido) "
            "values (:u, 1, :n, 'hosteleria_turismo', 'hosteleria_restauracion', :c) returning id"),
            {"u": u, "n": f"CV {i}", "c": BASE}).scalar_one() for i in range(1, n_cv_base + 1)]


def _candidatura(motor, u, oferta_id, **extra):
    campos = {"usuaria_id": u, "oferta_id": oferta_id, **extra}
    cols, marcas = ", ".join(campos), ", ".join(f":{k}" for k in campos)
    with sesion_de(motor, u) as s:
        return s.execute(text(f"insert into candidaturas ({cols}) values ({marcas}) returning id"),
                         campos).scalar_one()


def _encolar(motor, u, tipo, entidad_id, tope_coste=1.0, tope_reintentos=3):
    with sesion_de(motor, u) as s:
        tareas.encolar(s, u, tipo, entidad_id, tope_coste, tope_reintentos)


def _fila(motor, u, cid):
    with sesion_de(motor, u) as s:
        return s.execute(text("select * from candidaturas where id = :i"), {"i": cid}).mappings().one()


# --- T12: esquema, RLS, índice único y cascada -------------------------------------------------
def test_las_tablas_y_columnas_del_esquema_de_la_fase_3(motor_migrador):
    with motor_migrador.connect() as c:
        def columnas(tabla):
            return {r[0] for r in c.execute(text(
                "select column_name from information_schema.columns where table_name=:t"), {"t": tabla})}
        assert {"usuaria_id", "oferta_id", "cv_base_id", "cv_base_motivo", "perfil_version", "estado",
                "motivo_cierre", "preparacion", "motivo_error", "cv_contenido", "cv_traza",
                "carta_contenido", "carta_traza", "huecos", "avisos", "cobertura_ats", "redacciones_cv",
                "redacciones_carta", "problemas_juez", "instrucciones_embebidas", "canal",
                "canal_otro", "enviada_en", "creado_en", "actualizado_en"} <= columnas("candidaturas")
        assert {"usuaria_id", "candidatura_id", "de", "a", "motivo", "canal", "origen", "tipo",
                "creado_en"} <= columnas("candidatura_eventos")
        assert {"usuaria_id", "cv_base_id", "nombre", "contenido", "origen",
                "creado_en"} <= columnas("cv_base_versiones")


def test_una_usuaria_no_lee_candidaturas_historial_ni_versiones_de_otra(motor_app, bd_limpia):
    a, b = _usuarias(motor_app)
    oferta = _oferta(motor_app)
    [cv_base] = _perfil_y_cv_base(motor_app, a)
    cid = _candidatura(motor_app, a, oferta)
    with sesion_de(motor_app, a) as s:
        s.execute(text("insert into candidatura_eventos (usuaria_id, candidatura_id, de, a) "
                       "values (:u, :c, 'borrador', 'aprobada')"), {"u": a, "c": cid})
        s.execute(text("insert into cv_base_versiones (usuaria_id, cv_base_id, nombre, contenido, origen) "
                       "values (:u, :b, 'CV 1', 'texto', 'edicion')"), {"u": a, "b": cv_base})
    with sesion_de(motor_app, b) as s:
        for tabla in ("candidaturas", "candidatura_eventos", "cv_base_versiones"):
            assert s.execute(text(f"select count(*) from {tabla}")).scalar_one() == 0, tabla
        assert s.execute(text("update candidaturas set estado = 'cerrada'")).rowcount == 0
    with pytest.raises(DBAPIError), sesion_de(motor_app, b) as s:
        s.execute(text("insert into candidaturas (usuaria_id, oferta_id) values (:u, :o)"),
                  {"u": a, "o": oferta})


def test_no_se_pueden_crear_dos_candidaturas_no_cerradas_para_la_misma_oferta(motor_app, bd_limpia):
    a, b = _usuarias(motor_app)
    oferta = _oferta(motor_app)
    primera = _candidatura(motor_app, a, oferta)
    with pytest.raises(IntegrityError):
        _candidatura(motor_app, a, oferta)
    _candidatura(motor_app, b, oferta)  # otra usuaria sí puede
    with sesion_de(motor_app, a) as s:  # cerrada la primera, se puede volver a crear
        s.execute(text("update candidaturas set estado = 'cerrada', motivo_cierre = 'descartada' "
                       "where id = :i"), {"i": primera})
    assert _candidatura(motor_app, a, oferta) != primera


def test_los_valores_de_estado_y_preparacion_estan_acotados(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    oferta = _oferta(motor_app)
    with pytest.raises(IntegrityError):
        _candidatura(motor_app, a, oferta, estado="inventado")
    with pytest.raises(IntegrityError):
        _candidatura(motor_app, a, oferta, preparacion="inventada")


def test_eliminar_un_cv_base_borra_sus_versiones_y_no_la_candidatura(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    oferta = _oferta(motor_app)
    [cv_base] = _perfil_y_cv_base(motor_app, a)
    cid = _candidatura(motor_app, a, oferta, cv_base_id=cv_base)
    with sesion_de(motor_app, a) as s:
        s.execute(text("insert into cv_base_versiones (usuaria_id, cv_base_id, nombre, contenido, origen) "
                       "values (:u, :b, 'CV 1', 'texto', 'edicion')"), {"u": a, "b": cv_base})
        assert s.execute(text("delete from cv_base where id = :i"), {"i": cv_base}).rowcount == 1
        assert s.execute(text("select count(*) from cv_base_versiones")).scalar_one() == 0
        c = s.execute(text("select cv_base_id from candidaturas where id = :i"), {"i": cid}).one()
    assert c.cv_base_id is None


@pytest.fixture
def respaldo(monkeypatch):
    """RF-10.3d: con el respaldo activo el worker pasa los CV base al flujo."""
    from horma import config
    monkeypatch.setenv("HORMA_CV_BASE_RESPALDO", "true")
    config.ajustes.cache_clear()
    yield
    monkeypatch.undo()
    config.ajustes.cache_clear()


# --- T13: worker `candidatura` -----------------------------------------------------------------
def test_candidatura_guarda_el_cv_base_elegido_con_motivo_cv_carta_trazas_y_preparacion(
        motor_app, bd_limpia, respaldo):
    a, _ = _usuarias(motor_app)
    ids = _perfil_y_cv_base(motor_app, a, n_cv_base=2)
    cid = _candidatura(motor_app, a, _oferta(motor_app))
    _encolar(motor_app, a, "candidatura", cid)
    prov = ProveedorSimulado(FELIZ)
    assert worker.procesar_una(motor_app, prov) == "hecha"
    f = _fila(motor_app, a, cid)
    # Los dos coinciden en puesto y sector: gana el más reciente (id mayor); lo elige el código.
    assert f["cv_base_id"] == ids[1] and f["cv_base_motivo"] == "Coincide en puesto y sector con la oferta"
    assert f["cv_contenido"].startswith("## Experiencia") and f["carta_contenido"].startswith("Hola equipo")
    assert f["cv_traza"][0]["frase"] == "Camarera en Bar Sol, 2020-2023"
    assert f["carta_traza"][0]["fragmento"] == "Camarera en Bar Sol, 2020-2023"
    assert [h["requisito"] for h in f["huecos"]] == ["inglés"]  # la oferta lo pide y el CV no lo tiene
    assert f["avisos"] == [] and f["perfil_version"] == 1
    assert f["preparacion"] == "lista" and f["estado"] == "borrador" and f["motivo_error"] is None
    assert f["redacciones_cv"] == 1 and f["redacciones_carta"] == 1 and len(prov.llamadas) == 3
    assert f["problemas_juez"] == [] and len(prov.llamadas) == 3


def test_candidatura_sin_respaldo_parte_del_maestro_aunque_haya_cv_base(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    _perfil_y_cv_base(motor_app, a, n_cv_base=2)
    cid = _candidatura(motor_app, a, _oferta(motor_app))
    _encolar(motor_app, a, "candidatura", cid)
    assert worker.procesar_una(motor_app, ProveedorSimulado(FELIZ)) == "hecha"
    f = _fila(motor_app, a, cid)
    assert f["cv_base_id"] is None and f["cv_base_motivo"] is None and f["preparacion"] == "lista"


def test_candidatura_con_un_solo_cv_base_hace_3_llamadas(motor_app, bd_limpia, respaldo):
    a, _ = _usuarias(motor_app)
    [cv_base] = _perfil_y_cv_base(motor_app, a)
    cid = _candidatura(motor_app, a, _oferta(motor_app))
    _encolar(motor_app, a, "candidatura", cid)
    prov = ProveedorSimulado(FELIZ)
    assert worker.procesar_una(motor_app, prov) == "hecha" and len(prov.llamadas) == 3
    assert _fila(motor_app, a, cid)["cv_base_id"] == cv_base


def test_candidatura_ignora_los_cv_base_rechazados_y_los_de_otra_usuaria(motor_app, bd_limpia, respaldo):
    a, b = _usuarias(motor_app)
    _perfil_y_cv_base(motor_app, b)
    [bueno] = _perfil_y_cv_base(motor_app, a)
    with sesion_de(motor_app, a) as s:
        s.execute(text("insert into cv_base (usuaria_id, perfil_version, nombre, estado, motivo_error) "
                       "values (:u, 1, 'CV malo', 'rechazado', 'x')"), {"u": a})
    cid = _candidatura(motor_app, a, _oferta(motor_app))
    _encolar(motor_app, a, "candidatura", cid)
    prov = ProveedorSimulado(FELIZ)
    assert worker.procesar_una(motor_app, prov) == "hecha" and len(prov.llamadas) == 3
    assert _fila(motor_app, a, cid)["cv_base_id"] == bueno


def test_candidatura_sin_cv_base_se_prepara_con_el_maestro(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    _perfil_y_cv_base(motor_app, a, n_cv_base=0)
    cid = _candidatura(motor_app, a, _oferta(motor_app))
    _encolar(motor_app, a, "candidatura", cid, tope_reintentos=1)
    prov = ProveedorSimulado(FELIZ)
    assert worker.procesar_una(motor_app, prov) == "hecha" and len(prov.llamadas) == 3
    assert _fila(motor_app, a, cid)["preparacion"] == "lista"


def test_con_respaldo_y_solo_cv_base_rechazados_deja_preparacion_error_con_motivo(
        motor_app, bd_limpia, respaldo):
    a, _ = _usuarias(motor_app)
    _perfil_y_cv_base(motor_app, a, n_cv_base=0)
    with sesion_de(motor_app, a) as s:
        s.execute(text("insert into cv_base (usuaria_id, perfil_version, nombre, estado, motivo_error) "
                       "values (:u, 1, 'CV malo', 'rechazado', 'x')"), {"u": a})
    cid = _candidatura(motor_app, a, _oferta(motor_app))
    _encolar(motor_app, a, "candidatura", cid, tope_reintentos=1)
    assert worker.procesar_una(motor_app, ProveedorSimulado([])) == "error"
    f = _fila(motor_app, a, cid)
    assert f["preparacion"] == "error" and "CV base" in f["motivo_error"] and f["estado"] == "borrador"


def test_un_tope_de_coste_bajo_deja_preparacion_error_con_motivo(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    _perfil_y_cv_base(motor_app, a)
    cid = _candidatura(motor_app, a, _oferta(motor_app))
    _encolar(motor_app, a, "candidatura", cid, tope_coste=0.0000001, tope_reintentos=5)
    assert worker.procesar_una(motor_app, ProveedorSimulado([{"mal": 1}] * 5)) == "error"
    f = _fila(motor_app, a, cid)
    assert f["preparacion"] == "error" and "coste" in f["motivo_error"]


def test_una_usuaria_no_puede_preparar_la_candidatura_de_otra(motor_app, bd_limpia):
    a, b = _usuarias(motor_app)
    _perfil_y_cv_base(motor_app, b)
    cid_a = _candidatura(motor_app, a, _oferta(motor_app))
    _encolar(motor_app, b, "candidatura", cid_a, tope_reintentos=1)
    assert worker.procesar_una(motor_app, ProveedorSimulado([])) == "error"
    with sesion_de(motor_app, b) as s:
        assert "no existe la candidatura" in s.execute(text("select motivo_error from tareas")).scalar_one()
    assert _fila(motor_app, a, cid_a)["preparacion"] == "en_curso"


# --- T29: `clasificar_respuesta` ya no es una tarea del worker (P17) ------------------------------------
def test_clasificar_respuesta_ya_no_es_una_tarea_del_worker(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    cid = _candidatura(motor_app, a, _oferta(motor_app))
    _encolar(motor_app, a, "clasificar_respuesta", cid, tope_reintentos=1)
    assert "clasificar_respuesta" not in worker.MANEJADORES
    assert worker.procesar_una(motor_app, ProveedorSimulado([])) == "error"
    with sesion_de(motor_app, a) as s:
        assert "desconocido" in s.execute(text("select motivo_error from tareas")).scalar_one()


def test_los_topes_de_construccion_estan_en_la_configuracion():
    a = ajustes()
    assert a.tope_coste_candidatura == 1.00 and not hasattr(a, "tope_coste_respuesta")
    assert json.dumps(a.tope_coste_candidatura)  # número simple, no una estructura
