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
from horma.logs import configurar_logs
from horma.web.arranque import problemas_de_arranque
from horma.web.auth.identidad import Identidad, crear_identidad
from horma.web.db import motor
from horma.web.limites import Limitador
from horma.web.routers import (
    auth,
    candidaturas,
    costes,
    cv,
    estilo,
    ingesta,
    ofertas,
    paginas,
    perfil,
    preferencias,
    recomendaciones,
)

ESTATICOS = Path(__file__).parent / "static"
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; "
       "frame-ancestors 'none'; manifest-src 'self'; worker-src 'self'")
CSP_VISOR = CSP.replace("frame-ancestors 'none'", "frame-ancestors 'self'")
HSTS = "max-age=31536000; includeSubDomains"
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
MAX_CUERPO = 64 * 1024  # RF-1.3: límite de tamaño de cualquier petición
MARGEN_MULTIPART = 64 * 1024  # cabeceras y campos del formulario que acompañan al archivo


def crear_app(engine: Engine | None = None, identidad: Identidad | None = None) -> FastAPI:
    a = ajustes()
    configurar_logs()
    en_desarrollo = a.app_env == "development"
    en_produccion = a.app_env == "produccion"
    if en_produccion and (problemas := problemas_de_arranque(a)):
        raise RuntimeError("Configuración de producción no válida: " + "; ".join(problemas))
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
        # Única ruta que se deja enmarcar: el visor de CV de la propia página de perfil (RF-2.1c)
        visor = request.method == "GET" and request.url.path.startswith("/api/cv/") \
            and request.url.path.endswith("/ver")
        r.headers["Content-Security-Policy"] = CSP_VISOR if visor else CSP
        es_html = r.headers.get("content-type", "").startswith("text/html")
        if request.url.path.startswith("/static/") or es_html:
            # Revalidar siempre (ETag → 304): así un JS nuevo nunca convive con otro viejo en caché,
            # y las páginas (/perfil, /recomendadas…) no se sirven desfasadas al pulsar el menú en el móvil.
            r.headers["Cache-Control"] = "no-cache"
        r.headers["X-Content-Type-Options"] = "nosniff"
        r.headers["Referrer-Policy"] = "no-referrer"
        r.headers["X-Frame-Options"] = "SAMEORIGIN" if visor else "DENY"
        if en_produccion:
            r.headers["Strict-Transport-Security"] = HSTS
            r.headers["Permissions-Policy"] = PERMISSIONS_POLICY
        return r

    app.include_router(auth.router)
    app.include_router(ofertas.router)
    app.include_router(ingesta.router)
    app.include_router(costes.router)
    for r in (cv, estilo, perfil, preferencias, recomendaciones, candidaturas, paginas):
        app.include_router(r.router)
    app.mount("/static", StaticFiles(directory=ESTATICOS), name="static")

    @app.get("/", include_in_schema=False)
    def portada():
        return FileResponse(ESTATICOS / "index.html")

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifiesto():
        return FileResponse(ESTATICOS / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/sw.js", include_in_schema=False)
    def service_worker():
        # En la raíz para que su alcance sea toda la web; el navegador lo revalida siempre.
        return FileResponse(ESTATICOS / "sw.js", media_type="text/javascript",
                            headers={"Cache-Control": "no-cache"})

    @app.get("/salud", include_in_schema=False)
    def salud():
        return {"estado": "ok"}  # sin datos: solo dice que la API responde

    return app
