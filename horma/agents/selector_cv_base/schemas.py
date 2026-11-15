from pydantic import BaseModel, Field

from horma.schemas.oferta import Oferta
from horma.schemas.taxonomia import Familia, Sector


class CvBaseOpcion(BaseModel):
    id: int
    nombre: str
    sector: Sector
    familia: Familia
    contenido: str = Field(description="CV base en Markdown: contenido no fiable.")


class EntradaSelectorCvBase(BaseModel):
    oferta: Oferta
    cvs_base: list[CvBaseOpcion] = Field(min_length=1)


class SalidaSelectorCvBase(BaseModel):
    cv_base_id: int
    motivo: str = Field(min_length=1, max_length=300, description="Una frase.")
    instrucciones_embebidas: list[str] = Field(default_factory=list)
