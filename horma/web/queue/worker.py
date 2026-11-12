"""Worker: ejecuta las tareas de la cola con tope de coste y de reintentos (RT-14).

Tipos de tarea: `procesar_oferta` (flujo procesar_oferta) y `calificar_fuente` (flujo
calificar_fuente). Las tareas sin usuaria se ejecutan en modo sistema.
"""
import logging
import time
from dataclasses import dataclass

from sqlalchemy import Engine

from horma.flows import calificar_fuente, procesar_oferta
from horma.llm import metricas
from horma.llm.proveedor import Proveedor
from horma.schemas.fuente import CalificacionFuente
from horma.schemas.oferta import Oferta
from horma.tools import descargar, dominio
from horma.web.db import motor, sesion_de, sesion_sistema
from horma.web.queue import cola
from horma.web.repositories import ingesta as repo_ingesta
from horma.web.repositories import ofertas as repo_ofertas
from horma.web.repositories import tareas as repo_tareas

log = logging.getLogger("horma.worker")


@dataclass
class Dependencias:
    proveedor: Proveedor | None
    resolver: dominio.Resolvedor | None
    descargador: descargar.Descargador


class _ProcesarOferta:
    def cargar(self, s, entidad_id: int) -> dict:
        return repo_ofertas.para_procesar(s, entidad_id)

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        return procesar_oferta.crear(proveedor=d.proveedor, resolver=d.resolver).run(estado)

    def guardar(self, s, entidad_id: int, estado: dict) -> None:
        repo_ofertas.guardar(s, entidad_id, Oferta.model_validate(estado["oferta"]),
                             [tuple(o) for o in estado["origenes"]])

    def marcar_error(self, s, entidad_id: int, motivo: str) -> None:
        repo_ofertas.marcar_error(s, entidad_id, motivo)


class _CalificarFuente:
    def cargar(self, s, entidad_id: int) -> dict:
        return {"url": repo_ingesta.calificacion(s, entidad_id)["url"]}

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        return calificar_fuente.crear(proveedor=d.proveedor, descargador=d.descargador).run(estado)

    def guardar(self, s, entidad_id: int, estado: dict) -> None:
        repo_ingesta.guardar_calificacion(
            s, entidad_id, CalificacionFuente.model_validate(estado["calificacion"]))

    def marcar_error(self, s, entidad_id: int, motivo: str) -> None:
        repo_ingesta.marcar_error_calificacion(s, entidad_id, motivo)


MANEJADORES = {"procesar_oferta": _ProcesarOferta(), "extraer_oferta": _ProcesarOferta(),
               "calificar_fuente": _CalificarFuente()}


def procesar_una(engine: Engine, proveedor: Proveedor | None = None, *,
                 resolver: dominio.Resolvedor | None = dominio.resuelve,
                 descargador: descargar.Descargador = descargar.descargar_http) -> str | None:
    """Procesa una tarea. Devuelve el estado final de la tarea o None si no había ninguna."""
    tarea = cola.reclamar(engine)
    if tarea is None:
        return None
    usuaria, entidad_id = tarea["usuaria_id"], tarea["entidad_id"]

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
                entrada = manejador.cargar(s, entidad_id)
            estado = manejador.ejecutar(entrada, Dependencias(proveedor, resolver, descargador))
        except Exception as e:  # noqa: BLE001 - cualquier fallo cuenta como intento fallido
            error = e
    coste = float(sum(ll.coste for ll in llamadas))
    acumulado = float(tarea["coste_acumulado"]) + coste

    with sesion() as s:
        repo_tareas.registrar_llamadas(s, tarea["id"], llamadas)
        if error is None:
            manejador.guardar(s, entidad_id, estado)
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
                manejador.marcar_error(s, entidad_id, motivo)
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
