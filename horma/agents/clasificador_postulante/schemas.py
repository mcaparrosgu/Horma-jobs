from typing import Literal

from pydantic import BaseModel, Field

from horma.schemas.perfil import Perfil
from horma.schemas.taxonomia import Taxonomia


class EntradaClasificadorPostulante(BaseModel):
    perfil: Perfil


class PuestoCandidato(BaseModel):
    titulo: str = Field(min_length=1, description="Título de puesto tal como se anuncia.")
    idioma: Literal["es", "en"]
    dato: str = Field(min_length=1, description="Puesto de una experiencia, titulación o certificación "
                                                "que lo justifica, copiado entero y tal cual.")
    relacion: Literal["mismo", "afin"] = Field(
        default="mismo", description="«mismo»: es ese puesto (traducido, otro género, sinónimo o "
                                     "especialidad); «afin»: un puesto distinto.")


class ClasificacionPostulante(Taxonomia):
    """La taxonomía de siempre más los puestos con los que buscar ofertas (RF-9.3)."""

    puestos: list[PuestoCandidato] = Field(default_factory=list, description="De 8 a 15 puestos.")
