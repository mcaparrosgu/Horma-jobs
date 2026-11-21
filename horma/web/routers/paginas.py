"""Páginas de la usuaria: perfil, CV base (escondida hasta S2), ofertas, candidaturas y landing.

Solo se sirven con sesión; sin ella, a la landing. Los datos los pide cada página a la API
(que aplica RLS), así que aquí no hay datos de nadie. Las direcciones antiguas redirigen (RF-10.1e)."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

from horma.web.db import sesion_de
from horma.web.repositories import perfiles

router = APIRouter()
ESTATICOS = Path(__file__).resolve().parent.parent / "static"
PAGINAS = {"/perfil": "perfil.html", "/cv-base": "cv-base.html", "/ofertas": "ofertas.html",
           "/candidaturas": "candidaturas.html",
           "/candidaturas/{candidatura_id}": "candidatura.html"}


def _pagina(archivo: str):
    def servir(request: Request):
        if not request.session.get("usuaria_id"):
            return RedirectResponse("/", status_code=302)
        return FileResponse(ESTATICOS / archivo)
    return servir


for _ruta, _archivo in PAGINAS.items():
    router.add_api_route(_ruta, _pagina(_archivo), methods=["GET"], include_in_schema=False)


def _entrada(request: Request):
    """`/` (RF-10.1d): con sesión, a Ofertas (o a Perfil si aún no hay perfil); sin ella, la landing."""
    usuaria_id = request.session.get("usuaria_id")
    if not usuaria_id:
        return FileResponse(ESTATICOS / "index.html")
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        hay_perfil = perfiles.vigente(s) is not None
    return RedirectResponse("/ofertas" if hay_perfil else "/perfil", status_code=302)


router.add_api_route("/", _entrada, methods=["GET"], include_in_schema=False)


def _redireccion(destino: str):
    def ir() -> RedirectResponse:
        return RedirectResponse(destino, status_code=308)
    return ir


# Direcciones antiguas (RF-10.1e): marcadores y enlaces de antes siguen funcionando.
for _antigua, _destino in {"/entrar": "/", "/recomendadas": "/ofertas", "/anadir-oferta": "/ofertas#anadir"}.items():  # noqa: E501
    router.add_api_route(_antigua, _redireccion(_destino), methods=["GET"], include_in_schema=False)
