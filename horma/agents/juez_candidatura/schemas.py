from typing import Literal

from pydantic import BaseModel, Field, model_validator

from horma.schemas.candidatura import Problema, TrazaFrase
from horma.schemas.oferta import Oferta

Veredicto = Literal["aprobado", "corregir"]


class EntradaJuezCandidatura(BaseModel):
    cv: str = Field(description="CV adaptado por revisar: no fiable.")
    cv_traza: list[TrazaFrase] = Field(default_factory=list)
    carta: str = Field(default="", description="Carta por revisar: no fiable. Vacía al juzgar un CV base.")
    carta_traza: list[TrazaFrase] = Field(default_factory=list)
    cv_maestro: str = Field(description="No fiable.")
    cv_base: str = Field(default="", description="No fiable. Vacío al juzgar un CV base.")
    oferta: Oferta | None = Field(default=None, description="Ausente al juzgar un CV base.")


class SalidaJuezCandidatura(BaseModel):
    veredicto_cv: Veredicto
    veredicto_carta: Veredicto
    problemas: list[Problema] = Field(default_factory=list)
    instrucciones_embebidas: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coherente(self):
        for documento, veredicto in (("cv", self.veredicto_cv), ("carta", self.veredicto_carta)):
            hay = any(p.documento == documento for p in self.problemas)
            if veredicto == "aprobado" and hay:
                raise ValueError(f"un documento aprobado no puede traer problemas ({documento})")
            if veredicto == "corregir" and not hay:
                raise ValueError(f"«corregir» exige al menos un problema ({documento})")
        return self


def sin_carta(salida: SalidaJuezCandidatura) -> SalidaJuezCandidatura:
    """Al juzgar solo un CV (un CV base) no hay carta: su veredicto es «aprobado» y no trae problemas."""
    return SalidaJuezCandidatura(
        veredicto_cv=salida.veredicto_cv, veredicto_carta="aprobado",
        problemas=[p for p in salida.problemas if p.documento == "cv"],
        instrucciones_embebidas=salida.instrucciones_embebidas)
