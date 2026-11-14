from pydantic import BaseModel, Field

from horma.schemas.match import Match
from horma.schemas.oferta import Oferta
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias

MAX_OFERTAS = 30


class OfertaCandidata(BaseModel):
    oferta_id: int
    oferta: Oferta


class EntradaMatcher(BaseModel):
    perfil: Perfil
    condiciones: Preferencias
    ofertas: list[OfertaCandidata] = Field(min_length=1, max_length=MAX_OFERTAS)


class SalidaMatcher(BaseModel):
    matches: list[Match]
