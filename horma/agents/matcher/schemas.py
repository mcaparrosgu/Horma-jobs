from pydantic import BaseModel, Field

from horma.schemas.match import Marca, Match, Relacion
from horma.schemas.oferta import Oferta
from horma.schemas.perfil_ciego import PerfilCiego

MAX_OFERTAS = 30


class OfertaCandidata(BaseModel):
    oferta_id: int
    oferta: Oferta


class EntradaMatcher(BaseModel):
    perfil: PerfilCiego  # la copia ciega (RF-12.30); las condiciones no le llegan (RF-12.31)
    ofertas: list[OfertaCandidata] = Field(min_length=1, max_length=MAX_OFERTAS)


class MatchModelo(Match):
    """Lo que el modelo está obligado a dar: además de la nota, las marcas y la relación (RF-12.34)."""

    marcas: list[Marca]
    relacion: Relacion


class SalidaMatcher(BaseModel):
    matches: list[MatchModelo]
