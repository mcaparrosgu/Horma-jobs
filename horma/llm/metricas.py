"""RT-06: una fila por llamada al modelo, sin el texto de la usuaria."""
from collections import deque
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass(frozen=True)
class Llamada:
    agente: str
    modelo: str
    tokens_entrada: int
    tokens_salida: int
    coste: float
    latencia_ms: int
    resultado: str  # ok | salida_invalida | error


_registro: deque[Llamada] = deque(maxlen=1000)
_destinos: list[Callable[[Llamada], None]] = []


def registrar(llamada: Llamada) -> None:
    _registro.append(llamada)
    for destino in list(_destinos):
        destino(llamada)


@contextmanager
def capturar() -> Iterator[list[Llamada]]:
    """Recoge las llamadas hechas dentro del bloque (el worker las guarda en `llm_llamadas`)."""
    recogidas: list[Llamada] = []
    _destinos.append(recogidas.append)
    try:
        yield recogidas
    finally:
        _destinos.remove(recogidas.append)


def registradas() -> list[Llamada]:
    return list(_registro)


def vaciar() -> None:
    _registro.clear()
