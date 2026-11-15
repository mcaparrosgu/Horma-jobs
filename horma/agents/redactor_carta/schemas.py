from pydantic import BaseModel, Field

from horma.schemas.candidatura import Problema, TrazaFrase
from horma.schemas.oferta import Oferta
from horma.schemas.taxonomia import Sector


class EntradaRedactorCarta(BaseModel):
    cv_maestro: str = Field(description="No fiable.")
    cv_adaptado: str = Field(description="CV adaptado a la oferta: no fiable.")
    oferta: Oferta
    sector: Sector
    errores_previos: list[str] = Field(default_factory=list)
    problemas_previos: list[Problema] = Field(default_factory=list)


class SalidaRedactorCarta(BaseModel):
    contenido: str = Field(min_length=1, description="Carta de presentación en texto plano.")
    traza: list[TrazaFrase] = Field(default_factory=list)
    instrucciones_embebidas: list[str] = Field(default_factory=list)
