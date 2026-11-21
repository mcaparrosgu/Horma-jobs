"""Preferencias de búsqueda: los filtros de la usuaria (RF-2.8, RF-2.8b).

Puestos, países, idiomas y sector llegan marcados desde el CV; contrato, remoto, nivel, sueldo mínimo
y salario publicado los marca ella. Un grupo vacío no filtra (P1). `origen` dice, por grupo, quién lo
rellenó. El sueldo mínimo es en euros brutos al año (P17)."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from horma.schemas.filtros import Contrato, Idioma, Pais
from horma.schemas.taxonomia import Familia, Nivel, Sector

MAX_TERMINOS = 50
MAX_LARGO_TERMINO = 80
OrigenGrupo = Literal["cv", "usuaria"]
# Grupos de casillas y campos que cuentan como «escritos por ella» al cambiarlos.
GRUPOS_CON_ORIGEN = ("familias", "puestos", "sectores", "contratos", "niveles", "paises", "idiomas",
                     "solo_remoto", "solo_salario", "sueldo_minimo")


def _sin_duplicados(v: list) -> list:
    return list(dict.fromkeys(v))


class PuestoSugerido(BaseModel):
    """Un puesto propuesto desde el CV con el dato del perfil que lo justifica (RF-9.3)."""

    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=1)
    dato: str = Field(min_length=1)


class Preferencias(BaseModel):
    model_config = ConfigDict(extra="forbid")

    familias: list[Familia] = Field(default_factory=list, description="Puestos (familias de la taxonomía).")
    puestos: list[str] = Field(default_factory=list, description="Títulos de puesto marcados (RF-9.3b).")
    puestos_sugeridos: list[PuestoSugerido] = Field(default_factory=list)
    excluidos: list[str] = Field(default_factory=list, description="Términos que sacan una oferta.")
    sectores: list[Sector] = Field(default_factory=list)
    contratos: list[Contrato] = Field(default_factory=list)
    niveles: list[Nivel] = Field(default_factory=list)
    paises: list[Pais] = Field(default_factory=list)
    idiomas: list[Idioma] = Field(default_factory=list)
    solo_remoto: bool = False
    solo_salario: bool = False
    sueldo_minimo: float | None = Field(default=None, ge=0, description="Euros brutos al año.")
    orden: Literal["recientes", "compatibles"] = "compatibles"
    rango_min: int = Field(default=40, ge=0, le=100)
    rango_max: int = Field(default=100, ge=0, le=100)
    origen: dict[str, OrigenGrupo] = Field(default_factory=dict)

    @field_validator("puestos", "excluidos")
    @classmethod
    def _terminos(cls, v: list[str]) -> list[str]:
        limpios = list(dict.fromkeys(" ".join(t.split()) for t in v if t and t.strip()))
        if len(limpios) > MAX_TERMINOS or any(len(t) > MAX_LARGO_TERMINO for t in limpios):
            raise ValueError(f"como mucho {MAX_TERMINOS} términos de {MAX_LARGO_TERMINO} caracteres")
        return limpios

    @field_validator("familias", "puestos", "excluidos", "sectores", "contratos", "niveles", "paises",
                     "idiomas")
    @classmethod
    def _unicos(cls, v: list) -> list:
        return _sin_duplicados(v)

    @model_validator(mode="after")
    def _rango_coherente(self):
        if self.rango_min > self.rango_max:
            raise ValueError("el rango mínimo no puede superar al máximo")
        return self
