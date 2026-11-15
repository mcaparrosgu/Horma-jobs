from pydantic import BaseModel, Field

from horma.schemas.candidatura import TrazaFrase  # noqa: F401  (movida a schemas; se reexporta)
from horma.schemas.perfil import Perfil
from horma.schemas.taxonomia import Familia, Sector


class Destino(BaseModel):
    sector: Sector
    familia: Familia


class EntradaGeneradorCvBase(BaseModel):
    cv_maestro: str = Field(description="CV maestro en Markdown: contenido no fiable.")
    perfil: Perfil
    destino: Destino
    errores_previos: list[str] = Field(default_factory=list)


class SalidaGeneradorCvBase(BaseModel):
    contenido: str = Field(min_length=1, description="CV base en Markdown compatible con ATS.")
    traza: list[TrazaFrase] = Field(default_factory=list)
