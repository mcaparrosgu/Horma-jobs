"""API de Horma: FastAPI por capas (routers → servicios → repositorios)."""
import logging
import secrets
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine
from starlette.middleware.sessions import SessionMiddleware

from horma.config import ajustes
from horma.web.auth.claves import Limitador
from horma.web.auth.identidad import Identidad, crear_identidad
from horma.web.db import motor
from horma.web.routers import auth, cv, ingesta, ofertas, perfil, preferencias, recomendaciones

ESTATICOS = Path(__file__).parent / "static"
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; "
       "frame-ancestors 'none'")
MAX_CUERPO = 64 * 1024  # RF-1.3: límite de tamaño de cualquier petición
MARGEN_MULTIPART = 64 * 1024  # cabeceras y campos del formulario que acompañan al archivo


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
    app.state.limitador = Limitador()

    app.add_middleware(SessionMiddleware, secret_key=secreto, session_cookie="horma_sesion",
                       same_site="lax", https_only=not en_desarrollo, max_age=7 * 24 * 3600)

    @app.middleware("http")
    async def cabeceras_de_seguridad(request, call_next):
        longitud = request.headers.get("content-length", "0")
        # Única excepción al límite: la subida de un CV (el archivo lleva su propio tope, RF-2.1)
        subida = request.method == "POST" and request.url.path == "/api/cv"
        maximo = a.max_cv_bytes + MARGEN_MULTIPART if subida else MAX_CUERPO
        if not longitud.isdigit() or int(longitud) > maximo:
            r = JSONResponse({"detail": "Petición demasiado grande"}, status_code=413)
        else:
            r = await call_next(request)
        r.headers["Content-Security-Policy"] = CSP
        r.headers["X-Content-Type-Options"] = "nosniff"
        r.headers["Referrer-Policy"] = "no-referrer"
        r.headers["X-Frame-Options"] = "DENY"
        return r

    app.include_router(auth.router)
    app.include_router(ofertas.router)
    app.include_router(ingesta.router)
    for r in (cv, perfil, preferencias, recomendaciones):
        app.include_router(r.router)
    app.mount("/static", StaticFiles(directory=ESTATICOS), name="static")

    @app.get("/", include_in_schema=False)
    def portada():
        return FileResponse(ESTATICOS / "index.html")

    return app
