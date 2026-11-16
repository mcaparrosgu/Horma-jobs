"""Fase 3 · T28-T29: migración 0007 (simplificar la candidatura, reversible, RLS intacta) y tope de coste
en la puerta única y el worker (RF-3.8d, RF-3.11, RT-14, P16)."""
import json
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pydantic import BaseModel
from sqlalchemy import text
from test_f3_t12_t13_bd_worker import FELIZ, _candidatura, _encolar, _fila, _oferta, _perfil_y_cv_base

from horma.llm import metricas
from horma.llm.gateway import completar
from horma.llm.simulado import ProveedorSimulado
from horma.web.db import sesion_de, sesion_sin_usuaria
from horma.web.queue import worker
from horma.web.repositories import tareas

pytestmark = pytest.mark.bd
RAIZ = Path(__file__).resolve().parent.parent


class Salida(BaseModel):
    ok: bool


def _cfg(urls):
    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", urls[1])
    return cfg


def _columnas(c, tabla):
    return {r[0] for r in c.execute(text(
        "select column_name from information_schema.columns where table_name = :t"), {"t": tabla})}


def _usuaria(motor, sub="google-A"):
    with sesion_sin_usuaria(motor) as s:
        return s.execute(text("select obtener_o_crear_usuaria(:g)"), {"g": sub}).scalar_one()


# --- T28: migración 0007 -----------------------------------------------------------------------
def test_0007_sube_y_baja_el_esquema_y_convierte_los_datos(bd_migrada, motor_migrador, bd_limpia):
    cfg = _cfg(bd_migrada)
    command.downgrade(cfg, "0006")
    with motor_migrador.begin() as c:
        assert {"documento", "cv_estetico_id", "respuesta_pendiente", "respuesta_propuesta", "vueltas_cv",
                "vueltas_carta"} <= _columnas(c, "candidaturas")
        assert "redacciones_cv" not in _columnas(c, "candidaturas")
        assert "etiqueta_respuesta" in _columnas(c, "candidatura_eventos")
        assert "candidatura_id" in _columnas(c, "cv_base_versiones")
        u = c.execute(text("select obtener_o_crear_usuaria('g')")).scalar_one()
        o = c.execute(text("insert into ofertas (texto_crudo, estado) values ('t', 'procesada') "
                           "returning id")).scalar_one()
        cv = c.execute(text("insert into cv_base (usuaria_id, perfil_version, nombre, contenido) "
                            "values (:u, 1, 'CV', 'x') returning id"), {"u": u}).scalar_one()
        cid = c.execute(text(
            "insert into candidaturas (usuaria_id, oferta_id, avisos, vueltas_cv, vueltas_carta, "
            "respuesta_pendiente) values (:u, :o, cast(:a as jsonb), 1, 2, 'correo') returning id"),
            {"u": u, "o": o, "a": json.dumps(["Falta una fecha", "Otro aviso"])}).scalar_one()
        for tipo, origen in (("transicion", "respuesta"), ("cv_base_guardado", "usuaria"),
                             ("nota", "usuaria")):
            c.execute(text("insert into candidatura_eventos (usuaria_id, candidatura_id, origen, tipo) "
                           "values (:u, :c, :o, :t)"), {"u": u, "c": cid, "o": origen, "t": tipo})
        c.execute(text("insert into cv_base_versiones (usuaria_id, cv_base_id, nombre, contenido, origen, "
                       "candidatura_id) values (:u, :b, 'CV', 'x', 'candidatura', :c)"),
                  {"u": u, "b": cv, "c": cid})

    command.upgrade(cfg, "0007")
    with motor_migrador.begin() as c:
        cols = _columnas(c, "candidaturas")
        assert {"redacciones_cv", "redacciones_carta", "problemas_juez"} <= cols
        assert not {"documento", "cv_estetico_id", "respuesta_pendiente", "respuesta_propuesta",
                    "vueltas_cv", "vueltas_carta"} & cols
        assert "etiqueta_respuesta" not in _columnas(c, "candidatura_eventos")
        assert "candidatura_id" not in _columnas(c, "cv_base_versiones")
        f = c.execute(text("select avisos, redacciones_cv, redacciones_carta, problemas_juez "
                           "from candidaturas")).one()
        assert f.avisos == [{"documento": "cv", "frase": None, "mensaje": "Falta una fecha"},
                            {"documento": "cv", "frase": None, "mensaje": "Otro aviso"}]
        assert (f.redacciones_cv, f.redacciones_carta, f.problemas_juez) == (1, 2, [])
        eventos = c.execute(text("select tipo, origen from candidatura_eventos order by id")).all()
        assert [tuple(e) for e in eventos] == [("transicion", "usuaria"), ("nota", "usuaria")]
        assert c.execute(text("select origen from cv_base_versiones")).scalar_one() == "edicion"
    with pytest.raises(Exception, match="origen"), motor_migrador.begin() as c:
        c.execute(text("insert into candidatura_eventos (usuaria_id, candidatura_id, origen) "
                       "values (:u, :c, 'respuesta')"), {"u": u, "c": cid})

    command.downgrade(cfg, "0006")
    with motor_migrador.begin() as c:
        f = c.execute(text("select avisos, vueltas_cv, vueltas_carta, documento, respuesta_pendiente "
                           "from candidaturas")).one()
        assert f.avisos == ["Falta una fecha", "Otro aviso"]
        assert (f.vueltas_cv, f.vueltas_carta, f.documento, f.respuesta_pendiente) == (1, 2, None, None)
        assert "etiqueta_respuesta" in _columnas(c, "candidatura_eventos")
    command.upgrade(cfg, "head")


def test_0007_mantiene_la_rls_de_las_tres_tablas(motor_app, bd_limpia):
    a, b = _usuaria(motor_app, "google-A"), _usuaria(motor_app, "google-B")
    oferta = _oferta(motor_app)
    [cv_base] = _perfil_y_cv_base(motor_app, a)
    cid = _candidatura(motor_app, a, oferta, redacciones_cv=1)
    with sesion_de(motor_app, a) as s:
        s.execute(text("insert into candidatura_eventos (usuaria_id, candidatura_id, de, a) "
                       "values (:u, :c, 'borrador', 'aprobada')"), {"u": a, "c": cid})
        s.execute(text("insert into cv_base_versiones (usuaria_id, cv_base_id, nombre, contenido, origen) "
                       "values (:u, :b, 'CV', 'x', 'restauracion')"), {"u": a, "b": cv_base})
    with sesion_de(motor_app, b) as s:
        for tabla in ("candidaturas", "candidatura_eventos", "cv_base_versiones"):
            assert s.execute(text(f"select count(*) from {tabla}")).scalar_one() == 0, tabla


# --- T29: tope de coste ------------------------------------------------------------------------
def _completar(prov):
    return completar(agente="x", prompt="p", entrada=Salida(ok=True), esquema_salida=Salida, proveedor=prov)


def test_capturar_con_tope_corta_antes_de_la_llamada_siguiente_sin_llamar_al_proveedor():
    prov = ProveedorSimulado([{"ok": True}] * 5)
    with metricas.capturar(tope=0.0) as llamadas:
        _completar(prov)  # nada acumulado todavía: pasa
        assert llamadas[0].coste > 0
        with pytest.raises(metricas.TopeSuperado):
            _completar(prov)
    assert len(prov.llamadas) == 1


def test_capturar_sin_tope_no_corta_y_con_tope_holgado_tampoco():
    prov = ProveedorSimulado([{"ok": True}] * 3)
    with metricas.capturar():
        _completar(prov)
        _completar(prov)
    with metricas.capturar(tope=100.0):
        _completar(prov)
    assert len(prov.llamadas) == 3


def test_el_tope_no_sobrevive_al_bloque():
    prov = ProveedorSimulado([{"ok": True}] * 3)
    with metricas.capturar(tope=0.0):
        pass
    _completar(prov)
    _completar(prov)
    assert len(prov.llamadas) == 2


def test_una_tarea_que_supera_el_tope_queda_en_error_sin_reintento_y_sin_guardar(motor_app, bd_limpia):
    a = _usuaria(motor_app)
    _perfil_y_cv_base(motor_app, a)
    cid = _candidatura(motor_app, a, _oferta(motor_app))
    # Con este tope la primera llamada pasa y la segunda se corta; la tarea no se guarda ni se reintenta.
    _encolar(motor_app, a, "candidatura", cid, tope_coste=0.0000001, tope_reintentos=5)
    assert worker.procesar_una(motor_app, ProveedorSimulado(FELIZ)) == "error"
    f = _fila(motor_app, a, cid)
    assert f["preparacion"] == "error" and "tope de coste" in f["motivo_error"] and f["cv_contenido"] == ""
    with sesion_de(motor_app, a) as s:
        t = s.execute(text("select estado, intentos, motivo_error from tareas")).one()
    assert t.estado == "error" and t.intentos == 1 and "tope de coste" in t.motivo_error


def test_una_tarea_que_acaba_bien_pero_supera_el_tope_no_se_guarda(motor_app, bd_limpia, monkeypatch):
    a = _usuaria(motor_app)
    cid = _candidatura(motor_app, a, _oferta(motor_app))
    hecho = {"guardado": False, "motivo": None}

    class Gastona:  # una sola llamada: pasa el corte previo, pero cuesta más que el tope y no lanza nada
        def cargar(self, s, tarea):
            return {}

        def ejecutar(self, estado, d):
            _completar(d.proveedor)
            return {}

        def guardar(self, s, tarea, estado):
            hecho["guardado"] = True

        def marcar_error(self, s, tarea, motivo):
            hecho["motivo"] = motivo

    monkeypatch.setitem(worker.MANEJADORES, "candidatura", Gastona())
    _encolar(motor_app, a, "candidatura", cid, tope_coste=0.0000001, tope_reintentos=5)
    assert worker.procesar_una(motor_app, ProveedorSimulado([{"ok": True}])) == "error"
    assert hecho["guardado"] is False and "tope de coste" in hecho["motivo"]
    with sesion_de(motor_app, a) as s:
        assert s.execute(text("select intentos from tareas")).scalar_one() == 1


def test_el_tope_vale_para_cualquier_tipo_de_tarea(motor_app, bd_limpia):
    a = _usuaria(motor_app)
    with sesion_de(motor_app, a) as s:
        s.execute(text("insert into perfiles (usuaria_id, version, estado, cv_maestro) "
                       "values (:u, 1, 'pendiente', 'CV')"), {"u": a})
        pid = s.execute(text("select id from perfiles")).scalar_one()
        tareas.encolar(s, a, "clasificar_perfil", pid, 0.0000001, 5)
    assert worker.procesar_una(motor_app, ProveedorSimulado([{"mal": 1}] * 5)) == "error"
    with sesion_de(motor_app, a) as s:
        assert "tope de coste" in s.execute(text("select motivo_error from tareas")).scalar_one()


def test_el_worker_abre_el_tope_con_lo_que_queda_de_la_tarea(motor_app, motor_migrador, bd_limpia):
    a = _usuaria(motor_app)
    _perfil_y_cv_base(motor_app, a)
    cid = _candidatura(motor_app, a, _oferta(motor_app))
    _encolar(motor_app, a, "candidatura", cid, tope_coste=1.0)
    with motor_migrador.begin() as c:
        assert c.execute(text("update tareas set coste_acumulado = 0.9999999")).rowcount == 1
    prov = ProveedorSimulado(FELIZ)
    assert worker.procesar_una(motor_app, prov) == "error"
    assert len(prov.llamadas) < 3  # el corte llega antes de acabar la preparación


def test_cargar_da_creado_en_de_cada_cv_base(motor_app, bd_limpia):
    a = _usuaria(motor_app)
    _perfil_y_cv_base(motor_app, a, n_cv_base=2)
    cid = _candidatura(motor_app, a, _oferta(motor_app))
    with sesion_de(motor_app, a) as s:
        entrada = worker.MANEJADORES["candidatura"].cargar(s, {"entidad_id": cid, "usuaria_id": a})
    assert len(entrada["cvs_base"]) == 2 and all(cv["creado_en"] for cv in entrada["cvs_base"])
