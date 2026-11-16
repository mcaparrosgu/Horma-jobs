"""Fase 4 · T22: alertas de gasto y de errores (RF-4.7b)."""
import logging
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_f1_t10_t15_api_ingesta import ADMIN, IdentidadFalsa, entrar

from horma import config
from horma.web import alertas
from horma.web.db import sesion_sistema
from horma.web.main import crear_app
from horma.web.queue import worker

pytestmark = pytest.mark.bd


def _ajustes(monkeypatch, **env):
    base = {"HORMA_ADMINS": ADMIN, "ALERTA_GASTO_DIA_USD": "1.0", "ALERTA_TASA_ERRORES": "0.5",
            "ALERTA_MIN_LLAMADAS": "4", "SMTP_HOST": "smtp.prueba.test", "ALERTAS_CORREO": "mar@prueba.test",
            "HORMA_DOMINIO": "horma.prueba.test"}
    for k, v in {**base, **env}.items():
        monkeypatch.setenv(k, v)
    config.ajustes.cache_clear()
    return config.ajustes()


@pytest.fixture(autouse=True)
def _limpiar_cache():
    yield
    config.ajustes.cache_clear()


class Buzon:
    def __init__(self):
        self.enviados = []

    def __call__(self, asunto, cuerpo, a):
        self.enviados.append((asunto, cuerpo))


def _llamadas(motor, n, coste, resultado="ok", minutos=0):
    with sesion_sistema(motor) as s:
        for _ in range(n):
            s.execute(text(
                "insert into llm_llamadas (agente, modelo, tokens_entrada, tokens_salida, coste, "
                "latencia_ms, resultado, creada_en) values ('adaptador', 'mayor', 10, 5, :c, 100, :r, "
                "now() - make_interval(mins => :m))"), {"c": coste, "r": resultado, "m": minutos})


def _alertas(motor):
    with sesion_sistema(motor) as s:
        return s.execute(text("select tipo, valor, umbral, correo_enviado from alertas order by id")).all()


def test_gasto_sobre_el_umbral_crea_alerta_log_y_correo_sin_datos(motor_app, bd_limpia, monkeypatch, caplog):
    a, buzon = _ajustes(monkeypatch), Buzon()
    _llamadas(motor_app, 2, 0.75)
    with caplog.at_level(logging.WARNING, logger="horma.alertas"):
        nuevas = alertas.comprobar(motor_app, a, enviar=buzon)
    assert [n["tipo"] for n in nuevas] == ["gasto_dia"] and nuevas[0]["correo_enviado"] is True
    fila = _alertas(motor_app)
    assert len(fila) == 1 and fila[0].tipo == "gasto_dia" and float(fila[0].valor) == pytest.approx(1.5)
    assert any("ALERTA Gasto del día" in r.getMessage() for r in caplog.records)
    assert len(buzon.enviados) == 1
    asunto, cuerpo = buzon.enviados[0]
    assert "Gasto del día" in asunto and "1.5000 USD" in cuerpo
    assert "https://horma.prueba.test/costes" in cuerpo
    assert "mar@prueba.test" not in cuerpo and "usuaria" not in cuerpo.lower()


def test_segunda_comprobacion_el_mismo_dia_no_repite_correo_ni_alerta(motor_app, bd_limpia, monkeypatch):
    a, buzon = _ajustes(monkeypatch), Buzon()
    _llamadas(motor_app, 2, 0.75)
    alertas.comprobar(motor_app, a, enviar=buzon)
    assert alertas.comprobar(motor_app, a, enviar=buzon) == []
    assert len(buzon.enviados) == 1 and len(_alertas(motor_app)) == 1


def test_otro_dia_vuelve_a_avisar(motor_app, bd_limpia, monkeypatch):
    a, buzon = _ajustes(monkeypatch), Buzon()
    _llamadas(motor_app, 2, 0.75)
    ahora = datetime.now(alertas.ZONA)
    alertas.comprobar(motor_app, a, ahora, enviar=buzon)
    manana = ahora + timedelta(days=1)
    with sesion_sistema(motor_app) as s:
        s.execute(text("insert into llm_llamadas (agente, modelo, tokens_entrada, tokens_salida, coste, "
                       "latencia_ms, resultado, creada_en) values ('x', 'mayor', 1, 1, 2.0, 1, 'ok', :c)"),
                  {"c": manana})
    assert len(alertas.comprobar(motor_app, a, manana, enviar=buzon)) == 1 and len(buzon.enviados) == 2


def test_tasa_de_errores_sobre_el_umbral_con_minimo_de_llamadas(motor_app, bd_limpia, monkeypatch):
    a, buzon = _ajustes(monkeypatch), Buzon()
    _llamadas(motor_app, 1, 0.01)
    _llamadas(motor_app, 3, 0.01, "error")
    nuevas = alertas.comprobar(motor_app, a, enviar=buzon)
    assert [n["tipo"] for n in nuevas] == ["tasa_errores"] and nuevas[0]["valor"] == pytest.approx(0.75)
    assert "Tasa de errores" in buzon.enviados[0][0] and "75.0 %" in buzon.enviados[0][1]


def test_la_tasa_no_salta_por_debajo_del_minimo_de_llamadas(motor_app, bd_limpia, monkeypatch):
    a, buzon = _ajustes(monkeypatch), Buzon()
    _llamadas(motor_app, 3, 0.01, "error")  # 100 % de errores, pero solo 3 llamadas (mínimo 4)
    assert alertas.comprobar(motor_app, a, enviar=buzon) == [] and buzon.enviados == []


def test_las_llamadas_de_hace_mas_de_una_hora_no_cuentan_para_la_tasa(motor_app, bd_limpia, monkeypatch):
    a, buzon = _ajustes(monkeypatch), Buzon()
    _llamadas(motor_app, 5, 0.01, "error", minutos=90)
    assert alertas.comprobar(motor_app, a, enviar=buzon) == []


def test_sin_smtp_host_solo_hay_pantalla_y_log(motor_app, bd_limpia, monkeypatch, caplog):
    a, buzon = _ajustes(monkeypatch, SMTP_HOST=""), Buzon()
    _llamadas(motor_app, 2, 0.75)
    with caplog.at_level(logging.WARNING, logger="horma.alertas"):
        nuevas = alertas.comprobar(motor_app, a, enviar=buzon)
    assert nuevas[0]["correo_enviado"] is False and buzon.enviados == []
    assert _alertas(motor_app)[0].correo_enviado is False
    assert any("ALERTA" in r.getMessage() for r in caplog.records)


def test_un_fallo_de_smtp_no_para_la_alerta_y_no_cuela_el_error_en_el_log(motor_app, bd_limpia, monkeypatch,
                                                                           caplog):
    a = _ajustes(monkeypatch)

    def roto(*_):
        raise OSError("contraseña=secreta")

    _llamadas(motor_app, 2, 0.75)
    with caplog.at_level(logging.ERROR, logger="horma.alertas"):
        nuevas = alertas.comprobar(motor_app, a, enviar=roto)
    assert nuevas[0]["correo_enviado"] is False and len(_alertas(motor_app)) == 1
    assert "secreta" not in caplog.text and "OSError" in caplog.text


def test_el_correo_sale_por_smtp_con_starttls_y_login(monkeypatch):
    a = _ajustes(monkeypatch, SMTP_USUARIO="avisos@prueba.test", SMTP_PASSWORD="clave")
    pasos = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            pasos.append(("conectar", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def starttls(self):
            pasos.append(("starttls",))

        def login(self, u, p):
            pasos.append(("login", u, p))

        def send_message(self, msg):
            pasos.append(("enviar", msg["To"], msg["From"], msg["Subject"]))

    monkeypatch.setattr(alertas.smtplib, "SMTP", FakeSMTP)
    alertas.enviar_correo("Asunto", "Cuerpo", a)
    assert [p[0] for p in pasos] == ["conectar", "starttls", "login", "enviar"]
    assert pasos[0][1:] == ("smtp.prueba.test", 587)
    assert pasos[3][1:] == ("mar@prueba.test", "avisos@prueba.test", "Asunto")


def test_costes_muestra_la_alerta(motor_app, bd_limpia, monkeypatch):
    a = _ajustes(monkeypatch)
    _llamadas(motor_app, 2, 0.75)
    alertas.comprobar(motor_app, a, enviar=Buzon())
    with TestClient(crear_app(engine=motor_app, identidad=IdentidadFalsa()), follow_redirects=False) as c:
        entrar(c)
        r = c.get("/api/costes").json()
    assert [x["tipo"] for x in r["alertas"]] == ["gasto_dia"] and r["alertas"][0]["correo_enviado"] is True


def test_el_worker_comprueba_cada_intervalo_y_un_fallo_no_lo_para(motor_app, monkeypatch, caplog):
    _ajustes(monkeypatch, ALERTA_INTERVALO_MIN="5")
    llamadas = []
    monkeypatch.setattr(worker.alertas, "comprobar", lambda e, a: llamadas.append(1))
    t = worker.comprobar_alertas(motor_app, None, 1000.0)
    assert t == 1000.0 and len(llamadas) == 1
    assert worker.comprobar_alertas(motor_app, t, 1100.0) == t and len(llamadas) == 1  # aún no toca
    assert worker.comprobar_alertas(motor_app, t, 1300.0) == 1300.0 and len(llamadas) == 2

    def roto(e, a):
        raise RuntimeError("fallo con datos")

    monkeypatch.setattr(worker.alertas, "comprobar", roto)
    with caplog.at_level(logging.ERROR, logger="horma.worker"):
        assert worker.comprobar_alertas(motor_app, None, 5000.0) == 5000.0
    assert "RuntimeError" in caplog.text and "datos" not in caplog.text
