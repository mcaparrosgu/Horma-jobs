"""Páginas de la fase 2 (RF-2.15): perfil, preferencias, CV base y recomendadas.

Solo se sirven con sesión; sin ella, a la portada para entrar. Los datos los pide cada página a la API
(que aplica RLS), así que aquí no hay datos de nadie."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter()
ESTATICOS = Path(__file__).resolve().parent.parent / "static"
PAGINAS = {"/perfil": "perfil.html", "/preferencias": "preferencias.html", "/cv-base": "cv-base.html",
           "/recomendadas": "recomendadas.html"}


def _pagina(archivo: str):
    def servir(request: Request):
        if not request.session.get("usuaria_id"):
            return RedirectResponse("/", status_code=302)
        return FileResponse(ESTATICOS / archivo)
    return servir


for _ruta, _archivo in PAGINAS.items():
    router.add_api_route(_ruta, _pagina(_archivo), methods=["GET"], include_in_schema=False)
