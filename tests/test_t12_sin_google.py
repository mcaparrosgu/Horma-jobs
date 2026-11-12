from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from horma.web.main import crear_app


def test_sin_credenciales_de_google_la_app_arranca_y_el_login_da_503(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
    from horma import config

    config.ajustes.cache_clear()
    try:
        app = crear_app(engine=create_engine("sqlite://"))  # el login no toca la base de datos
        c = TestClient(app, follow_redirects=False)
        assert c.get("/").status_code == 200
        assert c.get("/auth/google/login").status_code == 503
        assert c.get("/auth/google/callback?code=x").status_code == 503
        assert c.get("/ofertas").status_code == 401
    finally:
        config.ajustes.cache_clear()
