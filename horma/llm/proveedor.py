from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Respuesta:
    texto: str  # JSON de la salida estructurada
    tokens_entrada: int
    tokens_salida: int


class Proveedor(Protocol):
    def generar(self, *, modelo: str, sistema: str, usuario: str, esquema: dict,
                timeout: float) -> Respuesta: ...
