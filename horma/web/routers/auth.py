import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from horma.config import ajustes
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.db import sesion_sin_usuaria

router = APIRouter()


@router.get("/auth/google/login")
async def login(request: Request):
    return await request.app.state.identidad.redirigir(request, ajustes().google_redirect_uri)


@router.get("/auth/google/callback")
async def callback(request: Request):
    try:
        sub = await request.app.state.identidad.sub_desde_callback(request)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - estado inválido, código caducado, etc.
        raise HTTPException(status_code=400, detail="No se pudo iniciar sesión") from e
    with sesion_sin_usuaria(request.app.state.engine) as s:
        usuaria_id = s.execute(text("select obtener_o_crear_usuaria(:s)"), {"s": sub}).scalar_one()
    request.session.clear()  # sesión nueva: evita fijación de sesión
    request.session["usuaria_id"] = usuaria_id
    request.session["csrf"] = secrets.token_urlsafe(32)
    return RedirectResponse("/", status_code=302)


@router.get("/api/yo")
def yo(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return {"usuaria_id": usuaria_id, "csrf": request.session["csrf"]}


@router.post("/auth/logout", status_code=204, dependencies=[Depends(exigir_csrf)])
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=204)
