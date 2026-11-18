from typing import Literal

from pydantic import BaseModel, Field

from horma.schemas.candidatura import TrazaFrase  # noqa: F401  (movida a schemas; se reexporta)
from horma.schemas.perfil import Perfil
from horma.schemas.taxonomia import Familia, Sector


class Destino(BaseModel):
    sector: Sector
    familia: Familia


class ReglaVisibilidad(BaseModel):
    """Lo que la usuaria ha marcado para una experiencia de este CV base (RF-5.1g)."""
    puesto: str
    empresa: str | None = None
    inicio: str | None = None
    valor: Literal["completa", "condensada", "oculta"]


class EntradaGeneradorCvBase(BaseModel):
    cv_maestro: str = Field(description="CV maestro en Markdown: contenido no fiable.")
    perfil: Perfil
    destino: Destino
    visibilidad: list[ReglaVisibilidad] = Field(
        default_factory=list, description="Experiencias marcadas por la usuaria: mandan sobre el resto.")
    errores_previos: list[str] = Field(default_factory=list)


class SalidaGeneradorCvBase(BaseModel):
    contenido: str = Field(min_length=1, description="CV base en Markdown compatible con ATS.")
    traza: list[TrazaFrase] = Field(default_factory=list)
