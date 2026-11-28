"""Ofertas recomendadas (RF-2.11 a 2.13, RF-8.4 a 8.6).

`GET /api/recomendaciones` solo lee lo ya puntuado: no llama al modelo ni encola nada.
Puntuar lo que falta es `POST /api/recomendar`."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator

from horma.web.auth.sesion import exigir_csrf, usuaria_actual
from horma.web.routers.ingesta import solo_ingesta
from horma.web.services import recomendaciones as servicio

router = APIRouter()


class Correccion(BaseModel):
    nota: int | None = Field(default=None, ge=0, le=100)
    comentario: str = Field(default="", max_length=1000)   # «En qué nos hemos equivocado»: opcional
    informacion: str | None = Field(default=None, max_length=1000)   # «Información nueva sobre ti» (RF-10.15)

    @field_validator("informacion")
    @classmethod
    def _sin_espacios(cls, v: str | None) -> str | None:
        return (v or "").strip() or None

    @model_validator(mode="after")
    def _algo_que_decir(self):
        """El motivo es opcional, pero la corrección no puede ir vacía del todo."""
        self.comentario = self.comentario.strip()
        if not (self.comentario or self.informacion or self.nota is not None):
            raise ValueError("Escribe al menos un motivo, una compatibilidad o información nueva.")
        return self


def _salario(f: dict) -> str | None:
    """El texto tal como lo dice la oferta (P17): nunca convertido. Con «por hora» si lo es (D-123)."""
    texto = f["salario_rango"]
    if not texto:
        if f["salario_minimo"] is None and f["salario_maximo"] is None:
            return None
        partes = [f"{float(v):g}" for v in (f["salario_minimo"], f["salario_maximo"]) if v is not None]
        moneda = f" {f['salario_moneda']}" if f["salario_moneda"] else ""
        texto = " - ".join(dict.fromkeys(partes)) + moneda
    return f"{texto} por hora" if f.get("salario_por_hora") else texto



def _aviso_auditor(f: dict) -> str | None:
    """Señales de fraude que el auditor vio en una oferta propia (RF-5.3e). Solo avisa; no oculta."""
    avisos = []
    if f["fraude"]:
        senales = "; ".join(f["senales_fraude"] or [])
        avisos.append("Posibles señales de fraude" + (f": {senales}" if senales else ""))
    # «Fantasma» no se avisa: la oferta la ha pegado ella misma (RF-5.3e, enmienda P19, 20-nov).
    return ". ".join(avisos) or None


class Recomendar(BaseModel):
    motivo: Literal["abrir", "buscar"] = "abrir"


@router.post("/api/recomendar", dependencies=[Depends(exigir_csrf)])
def recomendar(request: Request, datos: Recomendar | None = None, usuaria_id: int = Depends(usuaria_actual)):
    """Puntúa lo que falta sin botón (RF-8.5). Siempre responde 200 con `{tarea_id}` o, si no lanza nada,
    `{tarea_id: null, motivo}`: `sin_perfil`, `en_marcha` (con la tarea en curso),
    `sin_pendientes`, `reciente`
    (solo al abrir: la última empezó hace menos de una hora) o `presupuesto` (RF-10.9c: hoy ya no queda)."""
    motivo_pedido = (datos or Recomendar()).motivo
    return servicio.recomendar(request.app.state.engine, usuaria_id, motivo_pedido)


@router.post("/api/matches/{oferta_id}/puntuar", status_code=202, dependencies=[Depends(exigir_csrf)])
def puntuar_ahora(oferta_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """«Puntuar ahora» (RF-8.5e): puntúa solo esa oferta. Funciona con una tanda en marcha; gasta del
    presupuesto del día (RF-10.9): sin presupuesto, 429 `presupuesto`."""
    try:
        tarea = servicio.puntuar_ahora(request.app.state.engine, usuaria_id, oferta_id)
    except servicio.SinPerfil as e:
        raise HTTPException(status_code=409, detail="Aún no tienes un perfil: sube un CV primero.") from e
    except servicio.OfertaNoExiste as e:
        raise HTTPException(status_code=404, detail="No existe esa oferta") from e
    except servicio.YaPuntuada as e:
        raise HTTPException(status_code=409, detail="Esa oferta ya tiene nota o se está puntuando.") from e
    return {"tarea_id": tarea}


@router.get("/api/recomendaciones")
def listar(request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Todo lo que pasa «Qué buscas», con su nota (o «sin puntuar»), su candidatura y si está descartada.
    Rango, orden y estado los aplica el navegador (RF-8.4c): aquí no hay parámetros de vista."""
    filas = servicio.listar(request.app.state.engine, usuaria_id)
    salida = [{**f, "salario": _salario(f), "sin_puntuar": f["nota"] is None,
               "aviso_auditor": _aviso_auditor(f) if f["propia"] else None} for f in filas]
    return {"total": len(salida), "sin_puntuar": sum(1 for f in salida if f["sin_puntuar"]),
            "recomendaciones": salida}


@router.put("/api/descartes/{oferta_id}", dependencies=[Depends(exigir_csrf)])
def descartar(oferta_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """Descarta una oferta: deja de puntuarse y sale de «Nuevas». No cabe con candidatura abierta (RF-8.6)."""
    try:
        servicio.descartar(request.app.state.engine, usuaria_id, oferta_id)
    except servicio.OfertaNoExiste as e:
        raise HTTPException(status_code=404, detail="No existe esa oferta") from e
    except servicio.CandidaturaAbierta as e:
        raise HTTPException(status_code=409,
                            detail="Esa oferta tiene una candidatura abierta: "
                                   "ciérrala antes de descartarla.") from e
    return {"oferta_id": oferta_id, "descartada": True}


@router.delete("/api/descartes/{oferta_id}", dependencies=[Depends(exigir_csrf)])
def recuperar(oferta_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    servicio.recuperar(request.app.state.engine, usuaria_id, oferta_id)
    return {"oferta_id": oferta_id, "descartada": False}


@router.post("/api/matches/{oferta_id}/correccion", dependencies=[Depends(exigir_csrf)])
def corregir(oferta_id: int, datos: Correccion, request: Request,
             usuaria_id: int = Depends(usuaria_actual)):
    """Se guarda junto al match. No entra en `evals/` hasta que Mar lo revise con un comando (P4)."""
    try:
        guardada = servicio.corregir(request.app.state.engine, usuaria_id, oferta_id, datos.model_dump())
    except servicio.SinNota as e:
        raise HTTPException(status_code=404, detail="Esa oferta aún no tiene nota.") from e
    return {"oferta_id": oferta_id, **guardada}


@router.delete("/api/matches/{oferta_id}/correccion", dependencies=[Depends(exigir_csrf)])
def quitar_correccion(oferta_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """«Quitar la mía» (spec 012, RF-12.26, D-118): borra la corrección entera. No llama al modelo."""
    try:
        servicio.quitar_correccion(request.app.state.engine, usuaria_id, oferta_id)
    except servicio.SinNota as e:
        raise HTTPException(status_code=404, detail="Esa oferta no tiene ninguna corrección.") from e
    return {"oferta_id": oferta_id, "correccion": None}


@router.post("/api/matches/{oferta_id}/informacion/perfil", status_code=201,
             dependencies=[Depends(exigir_csrf)])
def proponer_al_perfil(oferta_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """«Sí, revisarla» (RF-10.15c-d): la información de la corrección pasa a «Por resolver» de Perfil como
    propuesta. No crea versión ni llama al modelo: nada entra en el perfil hasta que ella la confirme."""
    try:
        servicio.proponer_al_perfil(request.app.state.engine, usuaria_id, oferta_id)
    except servicio.SinNota as e:
        raise HTTPException(status_code=404, detail="Esa oferta no tiene información nueva.") from e
    except servicio.SinPerfil as e:
        raise HTTPException(status_code=409, detail="Aún no tienes un perfil: sube un CV primero.") from e
    return {"oferta_id": oferta_id, "propuesta": True}


@router.get("/api/matches/{oferta_id}/exportar")
def exportar(oferta_id: int, request: Request, usuaria_id: int = Depends(usuaria_actual)):
    """El caso corregido, con el formato de `evals/recomendacion/casos/` (entrada y esperado)."""
    try:
        return servicio.exportar(request.app.state.engine, usuaria_id, oferta_id)
    except servicio.SinNota as e:
        raise HTTPException(status_code=404, detail="Esa oferta no tiene ninguna corrección.") from e


@router.get("/api/catalogo", dependencies=[Depends(solo_ingesta)])
def catalogo(request: Request):
    """Las ofertas recomendables y ya procesadas, comunes a todas las usuarias y sin ningún dato
    personal. Lo usa `horma recomendar` (clave de ingesta) para probar el matcher desde la consola."""
    return {"ofertas": servicio.catalogo_comun(request.app.state.engine)}
