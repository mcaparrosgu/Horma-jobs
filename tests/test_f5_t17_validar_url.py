"""Fase 5 · T17: `validar_url` y portales vetados (RF-5.3g, RF-5.3h)."""
import pytest

from horma.tools.validar_url import validar_url

PUBLICA = "203.0.113.7"  # documentación; en los tests actúa como IP pública


def _publico(_host):
    return ["151.101.1.1"]


def test_pasa_una_url_publica_de_greenhouse():
    assert validar_url("https://job-boards.greenhouse.io/anthropic/jobs/123", _publico) is None


@pytest.mark.parametrize("url", [
    "http://boards.greenhouse.io/x",
    "ftp://empresa.com/oferta",
    "empresa.com/oferta",
    "https://",
    "",
])
def test_rechaza_lo_que_no_es_https(url):
    assert validar_url(url, _publico)


@pytest.mark.parametrize("url", [
    "https://127.0.0.1/oferta",
    "https://10.0.0.5/oferta",
    "https://192.168.1.1/oferta",
    "https://169.254.169.254/latest/meta-data",
    "https://8.8.8.8/oferta",
    "https://[::1]/oferta",
    "https://2130706433/oferta",
])
def test_rechaza_ip_literal(url):
    assert "IP" in validar_url(url, _publico)


@pytest.mark.parametrize("url", [
    "https://localhost/oferta",
    "https://intranet/oferta",
    "https://servidor.local/oferta",
    "https://mi.localhost/oferta",
    "https://api.internal/oferta",
])
def test_rechaza_nombres_locales(url):
    assert validar_url(url, _publico)


@pytest.mark.parametrize("ip", ["10.1.2.3", "127.0.0.1", "169.254.169.254", "192.168.0.9", "::1", "fd00::1"])
def test_rechaza_dominio_que_resuelve_a_ip_privada(ip):
    assert validar_url("https://empresa.com/oferta", lambda _h: ["151.101.1.1", ip])


def test_rechaza_dominio_que_no_resuelve():
    def falla(_h):
        raise OSError("no resuelve")
    assert validar_url("https://noexiste-xyz.com/oferta", falla)
    assert validar_url("https://vacio.com/oferta", lambda _h: [])


@pytest.mark.parametrize("url", [
    "https://usuaria:clave@empresa.com/oferta",
    "https://usuaria@empresa.com/oferta",
])
def test_rechaza_credenciales_en_la_url(url):
    assert "credenciales" in validar_url(url, _publico)


@pytest.mark.parametrize("url", [
    "https://www.linkedin.com/jobs/view/1",
    "https://es.linkedin.com/jobs/view/1",
    "https://LinkedIn.com/jobs/view/1",
    "https://es.indeed.com/viewjob?jk=1",
    "https://www.glassdoor.es/job/1",
    "https://www.infojobs.net/oferta/1",
])
def test_rechaza_portales_vetados_con_sus_subdominios(url):
    motivo = validar_url(url, _publico)
    assert motivo and "pega el texto" in motivo.lower()


def test_un_dominio_parecido_a_un_portal_vetado_no_se_veta():
    assert validar_url("https://notlinkedin.com/oferta", _publico) is None
    assert validar_url("https://linkedin.com.empresa.com/oferta", _publico) is None


def test_la_lista_es_configurable(monkeypatch):
    from horma.tools import validar_url as mod
    monkeypatch.setattr(mod, "_vetados", lambda: {"empresa.com": "Empresa"})
    assert "Empresa" in validar_url("https://jobs.empresa.com/1", _publico)
