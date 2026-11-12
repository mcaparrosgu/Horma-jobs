"""Interfaz de los flujos (RT-12). PlainFlow ahora; LangGraphFlow en la fase 4 con los mismos
pasos y aristas."""
from collections.abc import Callable
from typing import Protocol, runtime_checkable

Paso = Callable[[dict], dict]       # recibe el estado y lo devuelve
Decision = Callable[[dict], str]    # recibe el estado y devuelve el nombre del paso siguiente


class ErrorDePaso(Exception):
    """Un paso del flujo falló; lleva su nombre para dejarlo en el motivo del error (RF-1.4)."""

    def __init__(self, paso: str, causa: BaseException | str):
        self.paso = paso
        self.causa = causa
        detalle = causa if isinstance(causa, str) else f"{type(causa).__name__}: {causa}"
        super().__init__(f"paso {paso}: {detalle}")


@runtime_checkable
class Flow(Protocol):
    nombre: str
    inicio: str

    def run(self, estado: dict) -> dict: ...

    def run_step(self, paso: str, estado: dict) -> dict: ...

    def siguiente(self, paso: str, estado: dict) -> str | None: ...

    def pasos(self) -> list[str]: ...
