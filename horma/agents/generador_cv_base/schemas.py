from pydantic import BaseModel, Field

from horma.schemas.perfil import Perfil
from horma.schemas.taxonomia import Familia, Sector


class Destino(BaseModel):
    sector: Sector
    familia: Familia


class TrazaFrase(BaseModel):
    frase: str = Field(min_length=1, description="Línea del CV base, tal cual.")
    fragmento: str = Field(min_length=1, description="Cita literal del CV maestro de la que sale.")


class EntradaGeneradorCvBase(BaseModel):
    cv_maestro: str = Field(description="CV maestro en Markdown: contenido no fiable.")
    perfil: Perfil
    destino: Destino
    errores_previos: list[str] = Field(default_factory=list)


class SalidaGeneradorCvBase(BaseModel):
    contenido: str = Field(min_length=1, description="CV base en Markdown compatible con ATS.")
    traza: list[TrazaFrase] = Field(default_factory=list)
