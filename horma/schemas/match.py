"""Resultado de puntuar una oferta para una usuaria (RF-2.12, RF-2.14).

La nota (0-100) mide solo experiencia y formación; `condiciones` mide solo las condiciones de
trabajo. La explicación tiene 2 o 3 frases y cita datos del perfil y de la oferta. Una explicación
retirada (porque mencionaba un rasgo personal) queda vacía y marcada."""
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_FRASE = re.compile(r"[^.!?]+[.!?]+(?:\s|$)|[^.!?]+$")


def contar_frases(texto: str) -> int:
    return len([f for f in _FRASE.findall(texto.strip()) if f.strip(" .!?")])


class Match(BaseModel):
    model_config = ConfigDict(extra="forbid")

    oferta_id: int
    nota: int = Field(ge=0, le=100)
    condiciones: Literal["bajo", "medio", "alto"]
    explicacion: str = ""
    cita_perfil: str = ""
    cita_oferta: str = ""
    retirada: bool = False

    @model_validator(mode="after")
    def _explicacion_de_2_o_3_frases(self):
        if not self.retirada and not 2 <= contar_frases(self.explicacion) <= 3:
            raise ValueError("la explicación debe tener 2 o 3 frases")
        return self
