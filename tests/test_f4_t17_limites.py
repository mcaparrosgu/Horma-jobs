"""T17 (RF-4.6d): límites de ritmo en login, subida de CV y candidaturas. Los umbrales salen de `.env`."""
import pytest
from fastapi.testclient import TestClient

from horma import config
from horma.web.limites import MENSAJE, Limitador
from horma.web.main import crear_app

pytestmark = pytest.mark.bd


class IdentidadFalsa:
    async def redirigir(self, request, redirect_uri):
        from starlette.responses import RedirectResponse
        return RedirectResponse("https://accounts.google.test/auth")

    async def sub_desde_callback(self, request) -> str:
        return request.query_params["code"]


@pytest.fixture
def app(motor_app, bd_limpia, tmp_path, monkeypatch):
    monkeypatch.setenv("RUTA_ARCHIVOS", str(tmp_path / "archivos"))
    monkeypatch.setenv("LIMITE_LOGIN_POR_MINUTO", "2")
    monkeypatch.setenv("LIMITE_CV_POR_MINUTO", "2")
    monkeypatch.setenv("LIMITE_CANDIDATURAS_POR_MINUTO", "2")
    config.ajustes.cache_clear()
    yield crear_app(engine=motor_app, identidad=IdentidadFalsa())
    config.ajustes.cache_clear()


def entrar(app, sub="google-A", ip="10.0.0.1"):
    c = TestClient(app, follow_redirects=False, client=(ip, 50000))
    r = c.get(f"/auth/google/callback?code={sub}")
    assert r.status_code == 302
    return c, {"X-CSRF-Token": c.get("/api/yo").json()["csrf"]}


def _subir(c, h):
    return c.post("/api/cv", headers=h, files={"archivo": ("cv.exe", b"no soy un cv")}).status_code


def test_el_login_se_limita_por_ip_con_mensaje_en_llano(app):
    codigos = [TestClient(app, follow_redirects=False, client=("10.0.0.9", 1)).get(
        "/auth/google/callback?code=x").status_code for _ in range(3)]
    assert codigos == [302, 302, 429]
    r = TestClient(app, follow_redirects=False, client=("10.0.0.9", 1)).get("/auth/google/login")
    assert r.status_code == 429 and r.json()["detail"] == MENSAJE
    # Otra IP no queda afectada
    assert TestClient(app, follow_redirects=False, client=("10.0.0.10", 1)).get(
        "/auth/google/callback?code=y").status_code == 302


def test_la_subida_de_cv_se_limita_por_usuaria(app):
    a, ha = entrar(app, "google-A", "10.0.0.1")
    b, hb = entrar(app, "google-B", "10.0.0.2")
    primeros = [_subir(a, ha), _subir(a, ha)]
    assert 429 not in primeros  # se rechazan por el tipo de archivo, no por el ritmo
    r = a.post("/api/cv", headers=ha, files={"archivo": ("cv.exe", b"x")})
    assert r.status_code == 429 and r.json()["detail"] == MENSAJE
    assert _subir(b, hb) != 429  # otra usuaria no queda afectada


def test_crear_y_reintentar_candidaturas_comparten_limite_por_usuaria(app):
    a, ha = entrar(app, "google-A", "10.0.0.1")
    b, hb = entrar(app, "google-B", "10.0.0.2")
    # Con ofertas que no existen: la petición falla en el servicio, pero cuenta para el ritmo
    c1 = a.post("/api/candidaturas", headers=ha, json={"oferta_id": 999991}).status_code
    c2 = a.post("/api/candidaturas/999992/reintentar", headers=ha).status_code
    assert 429 not in (c1, c2)
    r = a.post("/api/candidaturas", headers=ha, json={"oferta_id": 999993})
    assert r.status_code == 429 and r.json()["detail"] == MENSAJE
    assert a.post("/api/candidaturas/999994/reintentar", headers=ha).status_code == 429
    assert b.post("/api/candidaturas", headers=hb, json={"oferta_id": 999995}).status_code != 429


def test_lo_demas_no_se_limita(app):
    a, ha = entrar(app)
    for _ in range(5):
        assert a.get("/api/candidaturas").status_code == 200
        assert a.get("/api/cv").status_code == 200


def test_sin_sesion_no_cuenta_y_responde_401(app):
    c = TestClient(app, follow_redirects=False, client=("10.0.0.3", 1))
    assert [c.post("/api/candidaturas", json={"oferta_id": 1}).status_code for _ in range(4)] == [401] * 4


def test_los_limites_salen_de_env(monkeypatch):
    monkeypatch.setenv("LIMITE_LOGIN_POR_MINUTO", "7")
    monkeypatch.setenv("LIMITE_CV_POR_MINUTO", "8")
    monkeypatch.setenv("LIMITE_CANDIDATURAS_POR_MINUTO", "9")
    config.ajustes.cache_clear()
    try:
        a = config.ajustes()
        assert (a.limite_login_por_minuto, a.limite_cv_por_minuto,
                a.limite_candidaturas_por_minuto) == (7, 8, 9)
    finally:
        config.ajustes.cache_clear()


def test_el_limitador_olvida_pasada_la_ventana():
    lim = Limitador()
    assert lim.permitir(("x", 1), 1, ahora=0) and not lim.permitir(("x", 1), 1, ahora=30)
    assert lim.permitir(("x", 1), 1, ahora=61)
