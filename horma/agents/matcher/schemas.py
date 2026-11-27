from pydantic import BaseModel, Field

from horma.schemas.match import Match
from horma.schemas.oferta import Oferta
from horma.schemas.perfil_ciego import PerfilCiego

MAX_OFERTAS = 30


class OfertaCandidata(BaseModel):
    oferta_id: int
    oferta: Oferta


class EntradaMatcher(BaseModel):
    perfil: PerfilCiego  # la copia ciega (RF-12.30); las condiciones no le llegan (RF-12.31)
    ofertas: list[OfertaCandidata] = Field(min_length=1, max_length=MAX_OFERTAS)


class SalidaMatcher(BaseModel):
    matches: list[Match]
