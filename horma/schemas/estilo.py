"""Guía de estilo de la usuaria (fase 5, RF-5.6): cómo escribe, nunca cómo es."""
from typing import Literal

from pydantic import BaseModel, Field


class RasgoEstilo(BaseModel):
    rasgo: str = Field(min_length=1, max_length=200, description="Verbo, expresión o hábito de escritura.")
    cita: str = Field(default="", max_length=300,
                      description="Cita LITERAL del documento (RT-08); vacía si la editó ella.")


class GuiaEstilo(BaseModel):
    registro: Literal["formal", "cercano", "neutro"]
    persona: Literal["primera", "impersonal"]
    longitud_frase: Literal["corta", "media", "larga"]
    vinetas: str = Field(default="", max_length=200, description="Forma de sus viñetas.")
    expresiones: list[RasgoEstilo] = Field(default_factory=list, max_length=12,
                                           description="Verbos y expresiones que usa.")
    evita: list[RasgoEstilo] = Field(default_factory=list, max_length=12, description="Lo que evita.")
