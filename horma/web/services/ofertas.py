"""Servicio de ofertas: alta en el catálogo y encolado del flujo procesar_oferta (RF-1.3, RF-1.4)."""
import re
from datetime import datetime

from sqlalchemy import Engine

from horma.config import ajustes
from horma.web.db import sesion_sistema
from horma.web.repositories import ingesta as repo_ingesta
from horma.web.repositories import ofertas as repo
from horma.web.repositories import tareas

TIPO_TAREA = "procesar_oferta"


class FuenteNoValida(Exception):
    """La fuente indicada no existe o no está activa."""


class NoPareceOferta(ValueError):
    """El texto pegado por una usuaria no tiene pinta de oferta de trabajo."""


MIN_PALABRAS_OFERTA = 5
MIN_LETRAS_OFERTA = 25
MOTIVO_NO_OFERTA = ("Ese texto no parece una oferta de trabajo. Pega la oferta completa: puesto, empresa y "
                    "lo que piden u ofrecen.")


def parece_oferta(texto: str) -> bool:
    """Filtro barato y sin modelo (RF-5.3g): sin etiquetas ni enlaces, ¿quedan 5 palabras y 25 letras?
    No decide si es buena oferta; solo deja fuera lo que claramente no es texto de una oferta."""
    limpio = re.sub(r"<[^>]*>|https?://\S+", " ", texto or "")
    palabras = re.findall(r"[^\W\d_]{2,}", limpio)
    return len(palabras) >= MIN_PALABRAS_OFERTA and sum(len(p) for p in palabras) >= MIN_LETRAS_OFERTA


def recibir(engine: Engine, texto: str, *, fuente: str | None = None, clave_id: int | None = None,
            id_externo: str | None = None, url: str | None = None,
            usuaria_id: int | None = None, caduca_en: datetime | None = None,
            tope_coste: float | None = None,
            tope_reintentos: int | None = None) -> dict:
    """Guarda la oferta cruda y, si es nueva, encola su procesado. La carga de la cola es el id.
    Con `usuaria_id` la oferta es privada de esa usuaria (RF-5.3c)."""
    a = ajustes()
    if usuaria_id is not None and not parece_oferta(texto):
        raise NoPareceOferta(MOTIVO_NO_OFERTA)
    with sesion_sistema(engine) as s:
        fuente_id = atribucion = None
        if fuente:
            f = repo_ingesta.fuente(s, nombre=fuente)
            if not f or not f["activa"]:
                raise FuenteNoValida(fuente)
            fuente_id, atribucion = f["id"], f["atribucion"]
        oferta_id, estado, nueva = repo.crear(s, texto, fuente_id=fuente_id, clave_id=clave_id,
                                              id_externo=id_externo, url=url, usuaria_id=usuaria_id,
                                              caduca_en=caduca_en, atribucion=atribucion)
        if nueva:
            tareas.encolar(s, None, TIPO_TAREA, oferta_id,
                           a.tope_coste_tarea if tope_coste is None else tope_coste,
                           a.tope_reintentos_tarea if tope_reintentos is None else tope_reintentos)
    return {"id": oferta_id, "estado": estado, "nueva": nueva}
