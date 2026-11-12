"""Worker: ejecuta las tareas de la cola con tope de coste y de reintentos (RT-14)."""
import logging
import time

from sqlalchemy import Engine

from horma.llm import metricas
from horma.llm.proveedor import Proveedor
from horma.web.db import motor, sesion_de
from horma.web.queue import cola
from horma.web.repositories import ofertas as repo_ofertas
from horma.web.repositories import tareas as repo_tareas
from horma.web.services import ofertas as servicio

log = logging.getLogger("horma.worker")


def procesar_una(engine: Engine, proveedor: Proveedor | None = None) -> str | None:
    """Procesa una tarea. Devuelve el estado final de la tarea o None si no había ninguna."""
    tarea = cola.reclamar(engine)
    if tarea is None:
        return None
    usuaria, oferta_id = tarea["usuaria_id"], tarea["entidad_id"]
    error: Exception | None = None
    resultado = None
    with metricas.capturar() as llamadas:
        try:
            with sesion_de(engine, usuaria) as s:
                texto = repo_ofertas.texto_de(s, oferta_id)
            resultado = servicio.extraer(texto, proveedor)
        except Exception as e:  # noqa: BLE001 - cualquier fallo cuenta como intento fallido
            error = e
    coste = float(sum(ll.coste for ll in llamadas))
    acumulado = float(tarea["coste_acumulado"]) + coste

    with sesion_de(engine, usuaria) as s:
        repo_tareas.registrar_llamadas(s, tarea["id"], llamadas)
        if error is None:
            oferta, origenes = resultado
            repo_ofertas.guardar_extraccion(s, oferta_id, usuaria, oferta, origenes)
            repo_tareas.actualizar(s, tarea["id"], "hecha", coste)
            return "hecha"
        motivo = None
        if acumulado > float(tarea["tope_coste"]):
            motivo = f"tope de coste superado ({acumulado:.6f} > {float(tarea['tope_coste']):.6f})"
        elif tarea["intentos"] >= tarea["tope_reintentos"]:
            motivo = f"reintentos agotados ({tarea['intentos']}): {type(error).__name__}"
        if motivo:
            repo_ofertas.marcar_error(s, oferta_id, motivo)
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
