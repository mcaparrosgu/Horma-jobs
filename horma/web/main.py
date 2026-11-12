"""API de Horma: FastAPI por capas (routers → servicios → repositorios)."""
import logging
import secrets
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine
from starlette.middleware.sessions import SessionMiddleware

from horma.config import ajustes
from horma.web.auth.identidad import Identidad, crear_identidad
from horma.web.db import motor
from horma.web.routers import auth, ofertas

ESTATICOS = Path(__file__).parent / "static"
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; "
       "frame-ancestors 'none'")


def crear_app(engine: Engine | None = None, identidad: Identidad | None = None) -> FastAPI:
    a = ajustes()
    en_desarrollo = a.app_env == "development"
    secreto = a.session_secret
    if not secreto:
        if not en_desarrollo:
            raise RuntimeError("Falta SESSION_SECRET.")
        logging.getLogger("horma").warning("SESSION_SECRET vacío: secreto efímero (solo desarrollo)")
        secreto = secrets.token_urlsafe(32)

    app = FastAPI(title="Horma", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.engine = engine or motor()
    app.state.identidad = identidad or crear_identidad(a)

    app.add_middleware(SessionMiddleware, secret_key=secreto, session_cookie="horma_sesion",
                       same_site="lax", https_only=not en_desarrollo, max_age=7 * 24 * 3600)

    @app.middleware("http")
    async def cabeceras_de_seguridad(request, call_next):
        r = await call_next(request)
        r.headers["Content-Security-Policy"] = CSP
        r.headers["X-Content-Type-Options"] = "nosniff"
        r.headers["Referrer-Policy"] = "no-referrer"
        r.headers["X-Frame-Options"] = "DENY"
        return r

    app.include_router(auth.router)
    app.include_router(ofertas.router)
    app.mount("/static", StaticFiles(directory=ESTATICOS), name="static")

    @app.get("/", include_in_schema=False)
    def portada():
        return FileResponse(ESTATICOS / "index.html")

    return app
