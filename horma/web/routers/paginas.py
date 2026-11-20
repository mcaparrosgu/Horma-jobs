"""Páginas de las fases 2, 3 y 8: perfil, CV base, recomendadas, candidaturas, landing y entrada.

Solo se sirven con sesión; sin ella, a la landing. Los datos los pide cada página a la API
(que aplica RLS), así que aquí no hay datos de nadie."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

from horma.web.db import sesion_de
from horma.web.repositories import perfiles

router = APIRouter()
ESTATICOS = Path(__file__).resolve().parent.parent / "static"
PAGINAS = {"/perfil": "perfil.html", "/cv-base": "cv-base.html",
           "/recomendadas": "recomendadas.html", "/anadir-oferta": "anadir-oferta.html",
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


def _entrada(archivo: str):
    """`/` y `/entrar` (RF-8.1d): con sesión, a Recomendadas (o a Perfil si aún no hay perfil); sin ella, la
    landing o la pantalla de entrada."""
    def servir(request: Request):
        usuaria_id = request.session.get("usuaria_id")
        if not usuaria_id:
            return FileResponse(ESTATICOS / archivo)
        with sesion_de(request.app.state.engine, usuaria_id) as s:
            hay_perfil = perfiles.vigente(s) is not None
        return RedirectResponse("/recomendadas" if hay_perfil else "/perfil", status_code=302)
    return servir


router.add_api_route("/", _entrada("index.html"), methods=["GET"], include_in_schema=False)
router.add_api_route("/entrar", _entrada("entrar.html"), methods=["GET"], include_in_schema=False)


@router.get("/preferencias", include_in_schema=False)
def preferencias_ahora_en_recomendadas():
    """Preferencias pasó a ser el panel «Qué buscas» de Recomendadas (RF-8.4b)."""
    return RedirectResponse("/recomendadas#que-buscas", status_code=302)
