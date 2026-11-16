"""Checkpointer de Postgres para el flujo `candidatura` (RF-4.3). Vive en la web porque `horma.flows` no
puede importar psycopg: aquí se crea el `PostgresSaver` y se inyecta en `LangGraphFlow`. Las tablas las crea
la migración 0008 (con el rol migrador); `horma_app` solo lee y escribe.

El hilo de una candidatura es `candidatura-<id>`: existe desde que se prepara hasta que se aprueba
o se cierra."""
import logging

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection
from psycopg.rows import dict_row
from sqlalchemy import Engine
from sqlalchemy.engine import make_url

from horma.config import ajustes
from horma.flows import registry

log = logging.getLogger("horma.checkpointer")


def hilo_de(candidatura_id: int) -> str:
    return f"candidatura-{candidatura_id}"


def conninfo(url: str) -> str:
    """URL de SQLAlchemy (`postgresql+psycopg://…`) → la que entiende psycopg."""
    return make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)


def crear(url: str) -> PostgresSaver:
    """Un `PostgresSaver` con su propia conexión (autocommit y filas como diccionarios, como pide)."""
    conexion = Connection.connect(conninfo(url), autocommit=True, prepare_threshold=0, row_factory=dict_row)
    return PostgresSaver(conexion)


_cache: dict[str, PostgresSaver] = {}


def obtener(engine: Engine) -> PostgresSaver:
    """El checkpointer del proceso para la BD de `engine` (API o worker). Si se cae la conexión, abre otra."""
    url = engine.url.render_as_string(hide_password=False)
    saver = _cache.get(url)
    if saver is None or saver.conn.closed:
        saver = _cache[url] = crear(url)
    return saver


def con_langgraph() -> bool:
    return ajustes().horma_flow_impl == "langgraph"


def flujo_candidatura(engine: Engine, proveedor=None):
    """El flujo `candidatura` con la implementación configurada. Con `langgraph` lleva el checkpointer de
    Postgres; con `plain` no guarda nada."""
    if con_langgraph():
        return registry.crear_flujo("candidatura", proveedor=proveedor, checkpointer=obtener(engine))
    return registry.crear_flujo("candidatura", proveedor=proveedor)


def borrar_hilo(engine: Engine, candidatura_id: int) -> None:
    """Borra el hilo si existe. Sin `langgraph` no hace nada. Un fallo no debe romper quien llama."""
    if not con_langgraph():
        return
    try:
        obtener(engine).delete_thread(hilo_de(candidatura_id))
    except Exception as e:  # noqa: BLE001 - el hilo es un efecto secundario: se registra y se sigue
        log.warning("no se pudo borrar el hilo de la candidatura %s: %s", candidatura_id, type(e).__name__)
