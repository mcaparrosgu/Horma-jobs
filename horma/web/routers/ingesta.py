"""Dashboard de ingesta (solo administradoras) y rutas del ingestor (clave de alcance `ingesta`)."""
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from horma.config import ajustes
from horma.schemas.fuente import Fuente
from horma.web.auth import claves
from horma.web.auth.sesion import exigir_admin, exigir_admin_con_csrf, exigir_csrf, usuaria_actual
from horma.web.queue import worker
from horma.web.services import ingesta as servicio

router = APIRouter()
ESTATICOS = Path(__file__).resolve().parent.parent / "static"


def _errores(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except servicio.NoEncontrada as e:
        raise HTTPException(status_code=404, detail="No existe") from e
    except servicio.Conflicto as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except servicio.NoValida as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


def admin_o_ingesta(request: Request) -> None:
    """Con clave de ingesta (consola) o con sesión de administradora (dashboard; CSRF si cambia)."""
    if claves.portador(request):
        claves.clave_valida(request, {"ingesta"})
        return
    usuaria = usuaria_actual(request)
    exigir_admin(request, usuaria)
    if request.method != "GET":
        exigir_csrf(request, usuaria)


def solo_ingesta(request: Request) -> None:
    claves.clave_valida(request, {"ingesta"})


# --- dashboard ---------------------------------------------------------------------------------
@router.get("/ingesta", include_in_schema=False, dependencies=[Depends(exigir_admin)])
def pagina():
    return FileResponse(ESTATICOS / "ingesta.html")


@router.get("/api/ingesta/resumen", dependencies=[Depends(exigir_admin)])
def resumen(request: Request):
    return servicio.resumen(request.app.state.engine)


@router.post("/api/fuentes", status_code=201, dependencies=[Depends(exigir_admin_con_csrf)])
def crear_fuente(f: Fuente, request: Request):
    return {"id": _errores(servicio.crear_fuente, request.app.state.engine, f)}


@router.put("/api/fuentes/{fuente_id}", dependencies=[Depends(exigir_admin_con_csrf)])
def editar_fuente(fuente_id: int, f: Fuente, request: Request):
    _errores(servicio.actualizar_fuente, request.app.state.engine, fuente_id, f)
    return {"id": fuente_id}


# --- ejecuciones de ingesta -----------------------------------------------------------------------
class PedirEjecucion(BaseModel):
    fuente_id: int | None = None
    fuente: str | None = Field(default=None, max_length=41)
    limite: int = Field(default=20, ge=1, le=500)


@router.post("/api/ingesta/ejecuciones", status_code=201, dependencies=[Depends(admin_o_ingesta)])
def pedir_ejecucion(datos: PedirEjecucion, request: Request):
    """Dashboard: deja la ejecución pendiente. Consola (clave): la crea en curso y devuelve la fuente."""
    engine = request.app.state.engine
    if claves.portador(request):
        if not datos.fuente:
            raise HTTPException(status_code=422, detail="Falta el nombre de la fuente")
        return _errores(servicio.empezar_ejecucion, engine, datos.fuente, datos.limite)
    if datos.fuente_id is None:
        raise HTTPException(status_code=422, detail="Falta fuente_id")
    return _errores(servicio.pedir_ejecucion, engine, datos.fuente_id, datos.limite)


@router.post("/api/ingesta/reclamar", dependencies=[Depends(solo_ingesta)])
def reclamar(request: Request):
    r = servicio.reclamar_ejecucion(request.app.state.engine)
    return r if r else Response(status_code=204)


class FinEjecucion(BaseModel):
    recibidas: int = Field(ge=0)
    nuevas: int = Field(ge=0)
    repetidas: int = Field(ge=0)
    errores: int = Field(ge=0)
    motivo: str | None = Field(default=None, max_length=500)


@router.post("/api/ingesta/ejecuciones/{ejecucion_id}/fin", status_code=204,
             dependencies=[Depends(solo_ingesta)])
def cerrar(ejecucion_id: int, datos: FinEjecucion, request: Request):
    _errores(servicio.cerrar_ejecucion, request.app.state.engine, ejecucion_id,
             recibidas=datos.recibidas, nuevas=datos.nuevas, repetidas=datos.repetidas,
             errores=datos.errores, motivo=datos.motivo)
    return Response(status_code=204)


# --- calificaciones ----------------------------------------------------------------------------
class PedirCalificacion(BaseModel):
    url: str = Field(pattern=r"^https://", max_length=2000)


@router.post("/api/fuentes/calificaciones", status_code=202, dependencies=[Depends(admin_o_ingesta)])
def pedir_calificacion(datos: PedirCalificacion, request: Request):
    engine = request.app.state.engine
    r = servicio.pedir_calificacion(engine, datos.url)
    if ajustes().horma_flujo_en_linea:  # solo desarrollo
        worker.procesar_una(engine)
    return r


@router.get("/api/fuentes/calificaciones/{calificacion_id}", dependencies=[Depends(admin_o_ingesta)])
def ver_calificacion(calificacion_id: int, request: Request):
    return _errores(servicio.ver_calificacion, request.app.state.engine, calificacion_id)


# --- claves de API -----------------------------------------------------------------------------
class NuevaClave(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    alcance: Literal["ofertas", "ingesta"]


@router.get("/api/claves", dependencies=[Depends(exigir_admin)])
def listar_claves(request: Request):
    return servicio.claves(request.app.state.engine)


@router.post("/api/claves", status_code=201, dependencies=[Depends(exigir_admin_con_csrf)])
def crear_clave(datos: NuevaClave, request: Request):
    """La clave en claro solo se devuelve aquí, una vez."""
    return servicio.crear_clave(request.app.state.engine, datos.nombre, datos.alcance)


@router.delete("/api/claves/{clave_id}", status_code=204,
               dependencies=[Depends(exigir_admin_con_csrf)])
def revocar_clave(clave_id: int, request: Request):
    _errores(servicio.revocar_clave, request.app.state.engine, clave_id)
    return Response(status_code=204)
