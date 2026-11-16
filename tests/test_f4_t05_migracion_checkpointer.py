"""Fase 4 · T05: migración 0008 (PDF guardados, señales de entrada, alertas y tablas del checkpointer) y
`horma.web.checkpointer` (RF-4.3, RF-4.3e, RF-4.7b)."""
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from horma.flows.grafo import LangGraphFlow
from horma.web import checkpointer
from horma.web.db import sesion_de, sesion_sin_usuaria, sesion_sistema

pytestmark = pytest.mark.bd
RAIZ = Path(__file__).resolve().parent.parent
TABLAS_CHECKPOINT = {"checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations"}


def _cfg(urls):
    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", urls[1])
    return cfg


def _columnas(c, tabla):
    return {r[0] for r in c.execute(text(
        "select column_name from information_schema.columns where table_name = :t"), {"t": tabla})}


def _tablas(c):
    return {r[0] for r in c.execute(text("select table_name from information_schema.tables "
                                         "where table_schema = 'public'"))}


def test_0008_sube_y_baja_sin_errores(bd_migrada, motor_migrador):
    cfg = _cfg(bd_migrada)
    command.downgrade(cfg, "0007")
    with motor_migrador.begin() as c:
        assert not {"cv_pdf", "carta_pdf", "entregada_en"} & _columnas(c, "candidaturas")
        assert "senales_entrada" not in _columnas(c, "llm_llamadas")
        assert "alertas" not in _tablas(c) and not TABLAS_CHECKPOINT & _tablas(c)
    command.upgrade(cfg, "head")
    with motor_migrador.begin() as c:
        assert {"cv_pdf", "carta_pdf", "entregada_en"} <= _columnas(c, "candidaturas")
        assert "senales_entrada" in _columnas(c, "llm_llamadas")
        assert {"id", "tipo", "valor", "umbral", "creada_en", "correo_enviado"} <= _columnas(c, "alertas")
        assert TABLAS_CHECKPOINT <= _tablas(c)


def _juguete(checkpointer_):
    def a(e):
        e["cv_contenido"] = "texto"
        return e

    def entregar(e):
        e["cv_pdf"] = b"%PDF"
        return e

    return LangGraphFlow("prueba", pasos={"a": a, "entregar": entregar}, aristas={"a": "entregar"},
                         inicio="a", finales={"entregar"}, claves={"cv_contenido", "cv_pdf"},
                         pausas={"entregar"}, checkpointer=checkpointer_)


def test_horma_app_lee_y_escribe_checkpoints_y_un_hilo_se_recupera_desde_otra_conexion(bd_migrada):
    url = bd_migrada[0]
    pg1, pg2 = checkpointer.crear(url), checkpointer.crear(url)
    try:
        assert _juguete(pg1).run({}, hilo="candidatura-t05")["en_pausa"] == "entregar"
        r = _juguete(pg2).reanudar("candidatura-t05", {"cv_contenido": "editado"})
        assert r["cv_pdf"] == b"%PDF" and r["cv_contenido"] == "editado" and r["en_pausa"] is None
        pg2.delete_thread("candidatura-t05")
        assert pg1.get_tuple({"configurable": {"thread_id": "candidatura-t05"}}) is None
    finally:
        pg1.conn.close()
        pg2.conn.close()


def test_la_rls_de_candidaturas_no_cambia(motor_app, bd_limpia):
    with sesion_sin_usuaria(motor_app) as s:
        a = s.execute(text("select obtener_o_crear_usuaria('google-A')")).scalar_one()
        b = s.execute(text("select obtener_o_crear_usuaria('google-B')")).scalar_one()
    with sesion_sistema(motor_app) as s:
        oferta = s.execute(text("insert into ofertas (texto_crudo, estado) values ('t', 'procesada') "
                                "returning id")).scalar_one()
    with sesion_de(motor_app, a) as s:
        s.execute(text("insert into candidaturas (usuaria_id, oferta_id, cv_pdf, entregada_en) "
                       "values (:u, :o, :p, now())"), {"u": a, "o": oferta, "p": b"%PDF"})
    with sesion_de(motor_app, b) as s:
        assert s.execute(text("select count(*) from candidaturas")).scalar_one() == 0
        assert s.execute(text("select count(*) from candidaturas where cv_pdf is not null")).scalar_one() == 0
    with sesion_de(motor_app, a) as s:
        assert s.execute(text("select count(*) from candidaturas")).scalar_one() == 1


def test_alertas_solo_la_ve_el_modo_sistema(motor_app, bd_limpia):
    with sesion_sistema(motor_app) as s:
        s.execute(text("insert into alertas (tipo, valor, umbral) values ('gasto_dia', 5, 3)"))
        assert s.execute(text("select count(*) from alertas")).scalar_one() == 1
    with sesion_sin_usuaria(motor_app) as s:
        u = s.execute(text("select obtener_o_crear_usuaria('google-A')")).scalar_one()
    with sesion_de(motor_app, u) as s:
        assert s.execute(text("select count(*) from alertas")).scalar_one() == 0
    with pytest.raises(DBAPIError):
        with sesion_de(motor_app, u) as s:
            s.execute(text("insert into alertas (tipo, valor, umbral) values ('gasto_dia', 5, 3)"))


def test_senales_entrada_guarda_solo_tipos(motor_app, bd_limpia):
    with sesion_sistema(motor_app) as s:
        s.execute(text("insert into llm_llamadas (agente, modelo, tokens_entrada, tokens_salida, coste, "
                       "latencia_ms, resultado, senales_entrada) values ('x', 'm', 1, 1, 0, 1, 'ok', "
                       "cast(:s as text[]))"), {"s": "{orden_a_ia}"})
        assert s.execute(text("select senales_entrada from llm_llamadas")).scalar_one() == ["orden_a_ia"]


def test_el_checkpointer_usa_conexion_autocommit(bd_migrada):
    pg = checkpointer.crear(bd_migrada[0])
    try:
        assert pg.conn.autocommit is True
    finally:
        pg.conn.close()


def test_fuera_de_la_migracion_no_hay_otra_forma_de_crear_las_tablas(bd_migrada):
    e = create_engine(bd_migrada[0])
    with e.connect() as c:
        assert TABLAS_CHECKPOINT <= _tablas(c)
    e.dispose()
