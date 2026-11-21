"""Servicio de perfil: cualquier cambio de la usuaria crea una versión nueva y conserva la anterior
(RF-2.4). El dato que escribe ella lleva como origen «usuaria»; la taxonomía se recalcula en segundo
plano con `clasificar_perfil` y los CV base y matches de versiones anteriores quedan desfasados, sin
regenerarse solos."""
from collections.abc import Callable

from pydantic import ValidationError
from sqlalchemy import Engine

from horma.config import ajustes
from horma.schemas.perfil import Perfil, PeriodoCubierto
from horma.tools.componer_cv_maestro import componer_cv_maestro
from horma.tools.rasgos_personales import rasgos_personales
from horma.web.db import sesion_de
from horma.web.repositories import perfiles, tareas

LISTAS = ("experiencias", "formacion", "idiomas", "habilidades", "proyectos", "certificaciones",
          "actividades", "otros")
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


AVISO_DATO_PERSONAL = "Hemos quitado un dato personal que Horma no guarda."


def _periodo_de(dato: dict) -> dict:
    try:
        p = PeriodoCubierto(inicio=dato.get("inicio") or "", fin=dato.get("fin") or dato.get("inicio") or "")
    except ValidationError as e:
        raise DatoNoValido("Pon al menos la fecha de inicio (AAAA o AAAA-MM).") from e
    return p.model_dump(mode="json")


def _actividad_nueva(p: dict, dato: dict, antigua: int | None = None) -> str | None:
    """Una actividad suya con un rasgo personal se guarda solo como periodo cubierto (RF-9.1d, RT-09)."""
    sensible = rasgos_personales(str(dato.get("descripcion") or ""))
    if antigua is not None:
        p["actividades"].pop(antigua)
    if sensible:
        p["periodos_cubiertos"].append(_periodo_de(dato))
        return AVISO_DATO_PERSONAL
    nuevo = _con_origen(dato)
    if antigua is None:
        p["actividades"].append(nuevo)
    else:
        p["actividades"].insert(antigua, nuevo)
    return None


def _nueva_version(engine: Engine, usuaria_id: int, cambio: Callable[[dict], str | None]) -> dict:
    a = ajustes()
    with sesion_de(engine, usuaria_id) as s:
        fila = perfiles.vigente(s)
        if fila is None:
            raise SinPerfil
        datos = perfiles.perfil_modelo(fila).model_dump(mode="json")
        aviso = cambio(datos)
        try:
            perfil = Perfil.model_validate(datos)
        except ValidationError as e:
            raise DatoNoValido("El dato no es válido: " + "; ".join(
                f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()[:3])) from e
        perfil_id, version = perfiles.nueva_version(s, usuaria_id)
        perfiles.guardar_perfil(s, usuaria_id, perfil_id, perfil.model_copy(update={"version": version}),
                                componer_cv_maestro(perfil))
        tareas.encolar(s, usuaria_id, "clasificar_perfil", perfil_id, a.tope_coste_perfilar,
                       a.tope_reintentos_tarea)
    return {"id": perfil_id, "version": version, **({"aviso": aviso} if aviso else {})}


def _buscar(elementos: list[dict], clave: str) -> int | None:
    """Posición del dato al que se refiere la pregunta (por empresa, centro, idioma…), si lo hay."""
    clave = clave.strip().lower()
    for i, x in enumerate(elementos):
        if any(isinstance(v, str) and v.strip().lower() == clave
               for k, v in x.items() if k != "origen"):
            return i
    return None


def responder(engine: Engine, usuaria_id: int, indice: int, dato: dict | None) -> dict:
    """Responde una pregunta pendiente: la quita y, si trae un dato, lo añade con origen «usuaria»."""
    def cambio(p: dict) -> str | None:
        pendientes = p["preguntas_pendientes"]
        if not 0 <= indice < len(pendientes):
            raise DatoNoValido("Esa pregunta pendiente no existe.")
        campo = pendientes.pop(indice)["campo"]
        if dato is None:
            return
        # El modelo a veces pregunta por un dato concreto: «experiencias.Hotel Marina.fechas».
        seccion, _, resto = campo.partition(".")
        clave = resto.partition(".")[0]
        nuevo = {k: v for k, v in dato.items() if v not in (None, "")}
        if seccion == "actividades":
            return _actividad_nueva(p, nuevo)
        if seccion in LISTAS:
            existente = _buscar(p[seccion], clave) if clave else None
            if existente is None:
                p[seccion].append(_con_origen(nuevo))
            else:
                p[seccion][existente] = _con_origen({**p[seccion][existente], **nuevo})
        elif seccion in UNICOS:
            p[seccion] = _con_origen(nuevo)
        elif seccion == "genero_puestos":
            if nuevo.get("valor") not in ("femenino", "masculino"):
                raise DatoNoValido("Elige «femenino» o «masculino».")
            p["genero_puestos"] = nuevo["valor"]
        elif seccion == "nombre" and nuevo.get("valor"):
            p["nombre"] = str(nuevo["valor"]).strip()
        else:
            raise DatoNoValido(f"La pregunta sobre «{campo}» no admite un dato: respóndela sin dato.")
    return _nueva_version(engine, usuaria_id, cambio)


def corregir(engine: Engine, usuaria_id: int, campo: str, indice: int | None,
             dato: dict | None) -> dict:
    """Cambia o quita un dato del perfil (en una lista, el que está en `indice`)."""
    def cambio(p: dict) -> str | None:
        if campo == "actividades" and dato is not None:
            if indice is not None and not 0 <= indice < len(p[campo]):
                raise DatoNoValido("Ese dato no existe.")
            return _actividad_nueva(p, dato, indice)
        if campo in LISTAS:
            if indice is None and dato is not None:  # sin índice: dato nuevo al final de la lista
                p[campo].append(_con_origen(dato))
                return None
            if indice is None or not 0 <= indice < len(p[campo]):
                raise DatoNoValido("Ese dato no existe.")
            if dato is None:
                p[campo].pop(indice)
            else:
                p[campo][indice] = _con_origen(dato)
        elif campo in UNICOS:
            p[campo] = None if dato is None else _con_origen(dato)
        elif campo == "genero_puestos":
            valor = (dato or {}).get("valor")
            if valor not in ("femenino", "masculino"):
                raise DatoNoValido("Elige «femenino» o «masculino».")
            p["genero_puestos"] = valor
        else:
            raise DatoNoValido(f"El campo «{campo}» no se puede corregir.")
    return _nueva_version(engine, usuaria_id, cambio)
