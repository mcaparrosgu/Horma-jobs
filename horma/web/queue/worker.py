"""Worker: ejecuta las tareas de la cola con tope de coste y de reintentos (RT-14).

Tipos de tarea (la carga es siempre un id, nunca texto):
- `procesar_oferta` / `extraer_oferta` (catálogo, modo sistema) y `calificar_fuente` (fase 1).
- `perfilar` (id de una versión nueva y pendiente del perfil), `clasificar_perfil` (id de una versión
  copiada y pendiente), `generar_cv_base` y `recomendar` (id de la versión del perfil con la que se
  trabaja). Las de una usuaria se ejecutan con su sesión (RLS); las demás, en modo sistema.
"""
import logging
import time
from dataclasses import dataclass

from sqlalchemy import Engine

from horma.flows import (
    calificar_fuente,
    clasificar_perfil,
    generar_cv_base,
    perfilar,
    procesar_oferta,
    recomendar,
)
from horma.llm import metricas
from horma.llm.proveedor import Proveedor
from horma.schemas.fuente import CalificacionFuente
from horma.schemas.oferta import Oferta
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias
from horma.tools import descargar, dominio
from horma.tools.buscar_ofertas import buscar_ofertas
from horma.web.db import motor, sesion_de, sesion_sistema
from horma.web.queue import cola
from horma.web.repositories import ingesta as repo_ingesta
from horma.web.repositories import matches as repo_matches
from horma.web.repositories import ofertas as repo_ofertas
from horma.web.repositories import perfiles as repo_perfiles
from horma.web.repositories import tareas as repo_tareas

log = logging.getLogger("horma.worker")


@dataclass
class Dependencias:
    proveedor: Proveedor | None
    resolver: dominio.Resolvedor | None
    descargador: descargar.Descargador


class _ProcesarOferta:
    def cargar(self, s, tarea: dict) -> dict:
        return repo_ofertas.para_procesar(s, tarea["entidad_id"])

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        return procesar_oferta.crear(proveedor=d.proveedor, resolver=d.resolver).run(estado)

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        repo_ofertas.guardar(s, tarea["entidad_id"], Oferta.model_validate(estado["oferta"]),
                             [tuple(o) for o in estado["origenes"]])

    def marcar_error(self, s, tarea: dict, motivo: str) -> None:
        repo_ofertas.marcar_error(s, tarea["entidad_id"], motivo)


class _CalificarFuente:
    def cargar(self, s, tarea: dict) -> dict:
        return {"url": repo_ingesta.calificacion(s, tarea["entidad_id"])["url"]}

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        return calificar_fuente.crear(proveedor=d.proveedor, descargador=d.descargador).run(estado)

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        repo_ingesta.guardar_calificacion(
            s, tarea["entidad_id"], CalificacionFuente.model_validate(estado["calificacion"]))

    def marcar_error(self, s, tarea: dict, motivo: str) -> None:
        repo_ingesta.marcar_error_calificacion(s, tarea["entidad_id"], motivo)


def _perfil_de_la_tarea(s, tarea: dict, *, hecha: bool = False) -> dict:
    fila = repo_perfiles.perfil_fila(s, tarea["entidad_id"])
    if fila is None:
        raise ValueError(f"no existe el perfil {tarea['entidad_id']} de esta usuaria")
    if hecha and fila["estado"] != "hecha":
        raise ValueError(f"el perfil {fila['version']} no está listo (estado: {fila['estado']})")
    return fila


class _Perfilar:
    """Lee todos los CV de la usuaria y rellena la versión reservada: perfil, orígenes y las
    preferencias que salen del CV."""

    def cargar(self, s, tarea: dict) -> dict:
        fila = _perfil_de_la_tarea(s, tarea)
        cvs = repo_perfiles.cvs_fuente(s)
        if not cvs:
            raise ValueError("la usuaria no tiene ningún CV para perfilar")
        return {"cvs": cvs, "_version": fila["version"]}

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        return {**perfilar.crear(proveedor=d.proveedor).run(estado), "_version": estado["_version"]}

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        perfil = Perfil.model_validate({**estado["perfil"], "version": estado["_version"]})
        repo_perfiles.guardar_perfil(s, tarea["usuaria_id"], tarea["entidad_id"], perfil,
                                     estado["cv_maestro"])
        repo_perfiles.aplicar_preferencias_del_cv(
            s, tarea["usuaria_id"], Preferencias.model_validate(estado["preferencias"]))

    def marcar_error(self, s, tarea: dict, motivo: str) -> None:
        repo_perfiles.marcar_error_perfil(s, tarea["entidad_id"], motivo)


class _ClasificarPerfil:
    """Vuelve a clasificar una versión copiada (tras una respuesta o corrección de la usuaria)."""

    def cargar(self, s, tarea: dict) -> dict:
        fila = _perfil_de_la_tarea(s, tarea)
        return {"perfil": repo_perfiles.perfil_modelo(fila).model_dump(mode="json")}

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        return clasificar_perfil.crear(proveedor=d.proveedor).run(estado)

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        perfil = Perfil.model_validate({**estado["perfil"], "taxonomia": estado["taxonomia"]})
        repo_perfiles.guardar_perfil(s, tarea["usuaria_id"], tarea["entidad_id"], perfil)

    def marcar_error(self, s, tarea: dict, motivo: str) -> None:
        repo_perfiles.marcar_error_perfil(s, tarea["entidad_id"], motivo)


class _GenerarCvBase:
    def cargar(self, s, tarea: dict) -> dict:
        fila = _perfil_de_la_tarea(s, tarea, hecha=True)
        return {"perfil": repo_perfiles.perfil_modelo(fila).model_dump(mode="json"),
                "cv_maestro": fila["cv_maestro"],
                "preferencias": repo_perfiles.preferencias(s).model_dump(mode="json"),
                "_version": fila["version"]}

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        return generar_cv_base.crear(proveedor=d.proveedor).run(estado)

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        repo_perfiles.guardar_cv_base(s, tarea["usuaria_id"], estado["_version"], estado["cv_base"])

    def marcar_error(self, s, tarea: dict, motivo: str) -> None:
        fila = repo_perfiles.perfil_fila(s, tarea["entidad_id"])
        if fila:
            repo_perfiles.marcar_error_cv_base(s, tarea["usuaria_id"], fila["version"], motivo)


class _Recomendar:
    """Puntúa las ofertas que pasan el filtro y aún no tienen nota para esta versión del perfil."""

    def cargar(self, s, tarea: dict) -> dict:
        fila = _perfil_de_la_tarea(s, tarea, hecha=True)
        perfil = repo_perfiles.perfil_modelo(fila)
        prefs = repo_perfiles.preferencias(s)
        ya = repo_matches.puntuadas(s, fila["version"])
        consulta = buscar_ofertas(prefs, perfil.taxonomia, excluir_ids=ya,
                                  limite=recomendar.MAX_TANDAS * recomendar.TANDA)
        ids = repo_matches.ids_candidatas(s, consulta)
        ofertas = repo_ofertas.completas(s, ids)
        return {"perfil": perfil.model_dump(mode="json"), "preferencias": prefs.model_dump(mode="json"),
                "candidatas": [{"oferta_id": i, "oferta": ofertas[i].model_dump(mode="json")}
                               for i in ids if i in ofertas],
                "ya_puntuadas": ya, "_version": fila["version"]}

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        return recomendar.crear(proveedor=d.proveedor).run(estado)

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        repo_matches.guardar(s, tarea["usuaria_id"], estado["_version"], estado["recomendaciones"])

    def marcar_error(self, s, tarea: dict, motivo: str) -> None:
        """Sin fila propia: el motivo queda en la tarea."""


MANEJADORES = {"procesar_oferta": _ProcesarOferta(), "extraer_oferta": _ProcesarOferta(),
               "calificar_fuente": _CalificarFuente(), "perfilar": _Perfilar(),
               "clasificar_perfil": _ClasificarPerfil(), "generar_cv_base": _GenerarCvBase(),
               "recomendar": _Recomendar()}


def procesar_una(engine: Engine, proveedor: Proveedor | None = None, *,
                 resolver: dominio.Resolvedor | None = dominio.resuelve,
                 descargador: descargar.Descargador = descargar.descargar_http) -> str | None:
    """Procesa una tarea. Devuelve el estado final de la tarea o None si no había ninguna."""
    tarea = cola.reclamar(engine)
    if tarea is None:
        return None
    usuaria = tarea["usuaria_id"]

    def sesion():
        return sesion_de(engine, usuaria) if usuaria else sesion_sistema(engine)

    manejador = MANEJADORES.get(tarea["tipo"])
    error: Exception | None = None
    estado = None
    with metricas.capturar() as llamadas:
        try:
            if manejador is None:
                raise ValueError(f"tipo de tarea desconocido: {tarea['tipo']}")
            with sesion() as s:
                entrada = manejador.cargar(s, tarea)
            estado = manejador.ejecutar(entrada, Dependencias(proveedor, resolver, descargador))
        except Exception as e:  # noqa: BLE001 - cualquier fallo cuenta como intento fallido
            error = e
    coste = float(sum(ll.coste for ll in llamadas))
    acumulado = float(tarea["coste_acumulado"]) + coste

    with sesion() as s:
        repo_tareas.registrar_llamadas(s, tarea["id"], llamadas)
        if error is None:
            manejador.guardar(s, tarea, estado)
            repo_tareas.actualizar(s, tarea["id"], "hecha", coste)
            return "hecha"
        motivo = None
        if acumulado > float(tarea["tope_coste"]):
            motivo = f"tope de coste superado ({acumulado:.6f} > {float(tarea['tope_coste']):.6f})"
        elif tarea["intentos"] >= tarea["tope_reintentos"] or manejador is None:
            motivo = f"reintentos agotados ({tarea['intentos']}): {error}"
        if motivo:
            motivo = motivo[:500]
            if manejador:
                manejador.marcar_error(s, tarea, motivo)
            repo_tareas.actualizar(s, tarea["id"], "error", coste, motivo)
            log.warning("tarea %s detenida: %s", tarea["id"], motivo)
            return "error"
        repo_tareas.actualizar(s, tarea["id"], "pendiente", coste)
        return "pendiente"


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    engine = motor()
    log.info("worker en marcha")
    while True:
        if procesar_una(engine) is None:
            time.sleep(1.0)


if __name__ == "__main__":
    main()
