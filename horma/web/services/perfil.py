"""Servicio de perfil: cualquier cambio de la usuaria crea una versión nueva y conserva la anterior
(RF-2.4). El dato que escribe ella lleva como origen «usuaria»; la taxonomía se recalcula en segundo
plano con `clasificar_perfil` y los CV base y matches de versiones anteriores quedan desfasados, sin
regenerarse solos."""
from collections.abc import Callable

from pydantic import ValidationError
from sqlalchemy import Engine

from horma.config import ajustes
from horma.schemas.perfil import Perfil
from horma.web.db import sesion_de
from horma.web.repositories import perfiles, tareas

LISTAS = ("experiencias", "formacion", "idiomas", "habilidades")
UNICOS = ("titular", "resumen")


class SinPerfil(Exception):
    """La usuaria aún no tiene un perfil construido."""


class DatoNoValido(Exception):
    """El cambio pedido no es posible o el dato no cumple el esquema."""


def _origen_usuaria(dato: dict) -> dict:
    texto = " · ".join(str(v) for k, v in dato.items() if k != "origen" and v not in (None, "", []))
    return {"fuente": "usuaria", "fragmento": texto or "usuaria"}


def _con_origen(dato: dict) -> dict:
    return {**{k: v for k, v in dato.items() if k != "origen"}, "origen": _origen_usuaria(dato)}


def _nueva_version(engine: Engine, usuaria_id: int, cambio: Callable[[dict], None]) -> dict:
    a = ajustes()
    with sesion_de(engine, usuaria_id) as s:
        fila = perfiles.vigente(s)
        if fila is None:
            raise SinPerfil
        datos = perfiles.perfil_modelo(fila).model_dump(mode="json")
        cambio(datos)
        try:
            perfil = Perfil.model_validate(datos)
        except ValidationError as e:
            raise DatoNoValido("El dato no es válido: " + "; ".join(
                f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()[:3])) from e
        perfil_id, version = perfiles.nueva_version(s, usuaria_id)
        perfiles.guardar_perfil(s, usuaria_id, perfil_id, perfil.model_copy(update={"version": version}),
                                fila["cv_maestro"])
        tareas.encolar(s, usuaria_id, "clasificar_perfil", perfil_id, a.tope_coste_perfilar,
                       a.tope_reintentos_tarea)
    return {"id": perfil_id, "version": version}


def responder(engine: Engine, usuaria_id: int, indice: int, dato: dict | None) -> dict:
    """Responde una pregunta pendiente: la quita y, si trae un dato, lo añade con origen «usuaria»."""
    def cambio(p: dict) -> None:
        pendientes = p["preguntas_pendientes"]
        if not 0 <= indice < len(pendientes):
            raise DatoNoValido("Esa pregunta pendiente no existe.")
        campo = pendientes.pop(indice)["campo"]
        if dato is None:
            return
        if campo in LISTAS:
            p[campo].append(_con_origen(dato))
        elif campo in UNICOS:
            p[campo] = _con_origen(dato)
        else:
            raise DatoNoValido(f"La pregunta sobre «{campo}» no admite un dato: respóndela sin dato.")
    return _nueva_version(engine, usuaria_id, cambio)


def corregir(engine: Engine, usuaria_id: int, campo: str, indice: int | None,
             dato: dict | None) -> dict:
    """Cambia o quita un dato del perfil (en una lista, el que está en `indice`)."""
    def cambio(p: dict) -> None:
        if campo in LISTAS:
            if indice is None or not 0 <= indice < len(p[campo]):
                raise DatoNoValido("Ese dato no existe.")
            if dato is None:
                p[campo].pop(indice)
            else:
                p[campo][indice] = _con_origen(dato)
        elif campo in UNICOS:
            p[campo] = None if dato is None else _con_origen(dato)
        else:
            raise DatoNoValido(f"El campo «{campo}» no se puede corregir.")
    return _nueva_version(engine, usuaria_id, cambio)
