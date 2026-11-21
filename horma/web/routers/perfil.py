"""Perfil con versiones (RF-2.2 a 2.4): verlo con sus orígenes y pendientes, responder o corregir."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from horma.tools.avisos_perfil import aviso_de_hueco, avisos_perfil
from horma.tools.detectar_huecos import detectar_huecos
from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.db import sesion_de
from horma.web.repositories import perfiles
from horma.web.services import perfil as servicio

router = APIRouter()


class Respuesta(BaseModel):
    indice: int
    dato: dict | None = None


class Correccion(BaseModel):
    campo: str
    indice: int | None = None
    dato: dict | None = None


@router.get("/api/perfil")
def ver(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        fila, ultima = perfiles.vigente(s), perfiles.ultima(s)
        if fila is None:
            return {"perfil": None, "origenes": [],
                    "construyendo": bool(ultima) and ultima["estado"] == "pendiente",
                    "error": ultima["motivo_error"] if ultima and ultima["estado"] == "error" else None}
        return {"perfil": perfiles.perfil_modelo(fila).model_dump(mode="json"),
                "cv_maestro": fila["cv_maestro"], "creado_en": fila["creado_en"],
                "origenes": perfiles.origenes(s, fila["id"]),
                "construyendo": ultima["version"] > fila["version"] and ultima["estado"] == "pendiente",
                "error": ultima["motivo_error"] if ultima["version"] > fila["version"]
                and ultima["estado"] == "error" else None}


def _cambiar(request: Request, usuaria_id: int, accion):
    try:
        return accion(request.app.state.engine, usuaria_id)
    except servicio.SinPerfil as e:
        raise HTTPException(status_code=409, detail="Aún no tienes un perfil: sube un CV primero.") from e
    except servicio.DatoNoValido as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/api/perfil/respuestas", status_code=201, dependencies=[Depends(exigir_csrf)])
def responder(datos: Respuesta, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _cambiar(request, usuaria_id, lambda e, u: servicio.responder(e, u, datos.indice, datos.dato))


@router.patch("/api/perfil/datos", status_code=201, dependencies=[Depends(exigir_csrf)])
def corregir(datos: Correccion, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    return _cambiar(request, usuaria_id,
                    lambda e, u: servicio.corregir(e, u, datos.campo, datos.indice, datos.dato))


class Visto(BaseModel):
    clave: str = Field(min_length=1, max_length=300)
    huella: str = Field(min_length=1, max_length=64)


class Longitud(BaseModel):
    longitud: Literal["mantener", "sintetizar"]


@router.get("/api/perfil/avisos")
def avisos(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Huecos y avisos por reglas del perfil vigente, sin los que ella dio por vistos (RF-9.1c, RF-9.2).
    Se calculan al pedirlos; no se guardan."""
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        fila = perfiles.vigente(s)
        longitud = perfiles.longitud_cv(s)
        if fila is None:
            return {"huecos": [], "avisos": [], "total": 0, "longitud": longitud}
        perfil = perfiles.perfil_modelo(fila)
        textos = {c["cv_id"]: c["texto"] for c in perfiles.cvs_fuente(s)}
        vistos = perfiles.avisos_vistos(s)
        huecos = [aviso_de_hueco(h) for h in detectar_huecos(perfil, date.today())]
        por_reglas = avisos_perfil(perfil, fila["cv_maestro"] or "", textos)
    if longitud:  # elegir una longitud cuenta como dar por visto el aviso de CV largo (RF-9.2d)
        por_reglas = [a for a in por_reglas if a.clave != "largo"]

    def visibles(lista):
        return [{"clave": a.clave, "huella": a.huella, "texto": a.texto, "seccion": a.seccion}
                for a in lista if vistos.get(a.clave) != a.huella]
    h, a = visibles(huecos), visibles(por_reglas)
    return {"huecos": h, "avisos": a, "total": len(h) + len(a), "longitud": longitud}


@router.put("/api/perfil/avisos/visto", dependencies=[Depends(exigir_csrf)])
def dar_por_visto(datos: Visto, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        perfiles.marcar_visto(s, usuaria_id, datos.clave, datos.huella)
    return {"ok": True}


@router.put("/api/perfil/longitud", dependencies=[Depends(exigir_csrf)])
def elegir_longitud(datos: Longitud, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    with sesion_de(request.app.state.engine, usuaria_id) as s:
        perfiles.fijar_longitud(s, usuaria_id, datos.longitud)
    return {"longitud": datos.longitud}
