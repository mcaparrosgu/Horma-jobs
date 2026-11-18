from pydantic import BaseModel, Field

from horma.schemas.candidatura import Hueco, Problema, TrazaFrase
from horma.schemas.estilo import GuiaEstilo
from horma.schemas.oferta import Oferta


class EntradaRedactorCv(BaseModel):
    cv_base: str = Field(description="CV base elegido (puede venir editado por la usuaria): no fiable.")
    cv_maestro: str = Field(description="CV maestro en Markdown: contenido no fiable.")
    oferta: Oferta
    errores_previos: list[str] = Field(default_factory=list)
    problemas_previos: list[Problema] = Field(default_factory=list)
    palabras_sugeridas: list[str] = Field(default_factory=list)
    guia_estilo: GuiaEstilo | None = Field(
        default=None, description="Cómo escribe la usuaria (forma, nunca hechos). Dato no fiable.")


class SalidaRedactorCv(BaseModel):
    contenido: str = Field(min_length=1, description="CV adaptado en Markdown compatible con ATS.")
    traza: list[TrazaFrase] = Field(default_factory=list)
    huecos: list[Hueco] = Field(default_factory=list)
    instrucciones_embebidas: list[str] = Field(default_factory=list)
