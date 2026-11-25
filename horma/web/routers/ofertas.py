from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from horma.config import ajustes
from horma.tools.validar_url import validar_url
from horma.web import limites
from horma.web.auth import claves
from horma.web.auth.sesion import exigir_admin, exigir_csrf, usuaria_actual
from horma.web.services import ofertas as servicio

router = APIRouter()


class NuevaOferta(BaseModel):
    texto: str = Field(min_length=1, max_length=20000)
    fuente: str | None = Field(default=None, max_length=41)
    id_externo: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=2000)
    caduca_en: datetime | None = None


@router.post("/ofertas", status_code=201)
def crear(datos: NuevaOferta, request: Request, response: Response):
    """Con sesión y CSRF (web) o con clave de API (ingesta o empresa). RF-1.3."""
    clave_id = None
    usuaria_id = None
    if claves.portador(request):
        clave = claves.clave_valida(request, {"ofertas", "ingesta"})
        if datos.fuente and clave.alcance != "ingesta":
            raise HTTPException(status_code=403, detail="Solo la ingesta entrega en nombre de una fuente")
        claves.contar_ritmo(request, clave)
        clave_id = clave.id
    else:
        usuaria_id = usuaria_actual(request)
        exigir_csrf(request, usuaria_id)
        if datos.fuente:
            raise HTTPException(status_code=403, detail="Solo la ingesta entrega en nombre de una fuente")
    engine = request.app.state.engine
    try:
        r = servicio.recibir(engine, datos.texto, fuente=datos.fuente, clave_id=clave_id,
                             id_externo=datos.id_externo, url=datos.url,
                             usuaria_id=usuaria_id, caduca_en=datos.caduca_en)
    except servicio.NoPareceOferta as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except servicio.FuenteNoValida as e:
        raise HTTPException(status_code=409, detail=f"Fuente no válida o inactiva: {e}") from e
    if not r["nueva"]:
        response.status_code = 200
    elif ajustes().horma_flujo_en_linea:  # solo desarrollo: sin cola ni worker aparte
        r["estado"] = "procesada" if servicio.procesar_en_linea(engine) == "hecha" else "pendiente"
    return r


class NuevaUrl(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    releer: bool = False   # «Leer de nuevo» (RF-11.29): vuelve a leer una oferta ya añadida


@router.post("/ofertas/url", status_code=202, dependencies=[Depends(limites.limite_url)])
def crear_desde_url(datos: NuevaUrl, request: Request, response: Response,
                    usuaria_id: int = Depends(usuaria_actual)):
    """Lee la página con el proveedor y sigue como una oferta pegada, privada de la usuaria (RF-5.3f)."""
    exigir_csrf(request, usuaria_id)
    if (motivo := validar_url(datos.url)) is not None:
        raise HTTPException(status_code=422, detail=motivo)
    r = servicio.pedir_lectura_url(request.app.state.engine, usuaria_id, datos.url, datos.releer)
    if r.get("repetida"):
        response.status_code = 200   # ya estaba añadida: no se lee ni se encola nada (RF-11.29)
    return r


@router.get("/ofertas/url/{importacion_id}")
def estado_de_la_url(importacion_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """En qué punto va la lectura de una URL (solo su dueña la ve)."""
    fila = servicio.estado_lectura_url(request.app.state.engine, usuaria_id, importacion_id)
    if fila is None:
        raise HTTPException(status_code=404, detail="No existe esa lectura")
    return fila


@router.get("/api/ofertas/total", dependencies=[Depends(exigir_admin)])
def total(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Cuántas ofertas hay en el catálogo (todas, no solo las listadas), por estado."""
    por_estado = servicio.por_estado(request.app.state.engine, usuaria_id)
    return {"total": sum(por_estado.values()), "por_estado": por_estado}


@router.get("/api/ofertas", dependencies=[Depends(exigir_admin)])
def listar(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """El catálogo común con su auditoría y su taxonomía (RF-8.2c: solo administradoras)."""
    return servicio.catalogo(request.app.state.engine, usuaria_id)


@router.get("/api/ofertas/propias")
def propias(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Las ofertas que la usuaria ha añadido, con el avance de su análisis (RF-8.2c, RF-8.7)."""
    return servicio.propias(request.app.state.engine, usuaria_id)


@router.get("/api/ofertas/{oferta_id}/original")
def original(oferta_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """La oferta tal como entró (RF-8.3). La RLS hace que una propia ajena no exista: 404."""
    fila = servicio.original(request.app.state.engine, usuaria_id, oferta_id)
    if fila is None:
        raise HTTPException(status_code=404, detail="No existe esa oferta")
    return fila
