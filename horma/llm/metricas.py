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
    senales_entrada: tuple[str, ...] = ()  # solo tipos de señal (RF-4.5), nunca texto


class TopeSuperado(Exception):
    """El coste acumulado en el bloque `capturar(tope=…)` ya supera el tope: no se hace otra llamada."""


_registro: deque[Llamada] = deque(maxlen=1000)
_destinos: list[Callable[[Llamada], None]] = []
_topes: list[tuple[list[Llamada], float]] = []


def registrar(llamada: Llamada) -> None:
    _registro.append(llamada)
    for destino in list(_destinos):
        destino(llamada)


@contextmanager
def capturar(tope: float | None = None) -> Iterator[list[Llamada]]:
    """Recoge las llamadas hechas dentro del bloque (el worker las guarda en `llm_llamadas`).
    Con `tope` (USD), `comprobar_tope()` corta antes de la llamada siguiente si lo acumulado ya lo supera."""
    recogidas: list[Llamada] = []
    destino = recogidas.append
    _destinos.append(destino)
    if tope is not None:
        _topes.append((recogidas, tope))
    try:
        yield recogidas
    finally:
        _destinos.remove(destino)
        if tope is not None:
            _topes.remove((recogidas, tope))


def comprobar_tope() -> None:
    """La puerta única lo llama antes de cada llamada al modelo (RF-3.11)."""
    for recogidas, tope in _topes:
        gastado = sum(ll.coste for ll in recogidas)
        if gastado > tope:
            raise TopeSuperado(f"tope de coste superado ({gastado:.6f} > {tope:.6f})")


def registradas() -> list[Llamada]:
    return list(_registro)


def vaciar() -> None:
    _registro.clear()
