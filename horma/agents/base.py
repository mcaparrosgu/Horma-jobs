from pathlib import Path
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel

from horma.llm import completar
from horma.llm.proveedor import Proveedor

E = TypeVar("E", bound=BaseModel)
S = TypeVar("S", bound=BaseModel)


class Agente(Generic[E, S]):
    nombre: ClassVar[str]
    modelo: ClassVar[str]  # "pequeno" | "mayor"; la puerta lo traduce al modelo real
    entrada: ClassVar[type[BaseModel]]
    salida: ClassVar[type[BaseModel]]

    @classmethod
    def prompt(cls) -> str:
        return (Path(__file__).parent / cls.nombre.replace("-", "_") / "prompt.md").read_text(
            encoding="utf-8")

    @classmethod
    def run(cls, entrada: E, proveedor: Proveedor | None = None) -> S:
        """Sin estado, sin E/S de datos, sin llamar a otros agentes (RT-01, RT-13)."""
        return completar(agente=cls.nombre, prompt=cls.prompt(), entrada=entrada,
                         esquema_salida=cls.salida, modelo=cls.modelo, proveedor=proveedor)
