from typing import Literal

from pydantic import BaseModel, Field, model_validator

from horma.schemas.candidatura import Problema, TrazaFrase
from horma.schemas.oferta import Oferta


class EntradaJuezCv(BaseModel):
    contenido: str = Field(description="CV adaptado por revisar: no fiable.")
    traza: list[TrazaFrase] = Field(default_factory=list)
    cv_maestro: str = Field(description="No fiable.")
    cv_base: str = Field(description="No fiable.")
    oferta: Oferta


class SalidaJuezCv(BaseModel):
    veredicto: Literal["aprobado", "corregir"]
    problemas: list[Problema] = Field(default_factory=list)
    instrucciones_embebidas: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coherente(self):
        if self.veredicto == "aprobado" and self.problemas:
            raise ValueError("un CV aprobado no puede traer problemas")
        if self.veredicto == "corregir" and not self.problemas:
            raise ValueError("«corregir» exige al menos un problema")
        if any(p.tipo == "repite_cv" for p in self.problemas):
            raise ValueError("«repite_cv» solo existe para la carta")
        return self
