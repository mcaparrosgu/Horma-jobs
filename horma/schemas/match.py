"""Resultado de puntuar una oferta para una usuaria (RF-2.12, RF-2.14).

La nota (0-100) mide solo experiencia y formación; `condiciones` mide solo las condiciones de
trabajo. La explicación tiene 2 o 3 frases de hechos que citan datos del perfil y de la oferta, y el código
le antepone la frase de su franja (RF-12.18). `marcas` y `relacion` dicen qué requisitos cubre y cuánto se
parece el puesto (RF-12.34). Una explicación retirada queda marcada: vacía si mencionaba un rasgo personal;
con el aviso `SIN_COMPROBAR` si sus citas no existen (spec 012, RF-12.19)."""
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.json_schema import SkipJsonSchema

SIN_COMPROBAR = "Sin explicación comprobada"

_FRASE = re.compile(r"[^.!?]+[.!?]+(?:\s|$)|[^.!?]+$")


# Siglas con puntos («RR. HH.», «EE. UU.») y abreviaturas («p. ej.», «etc.») no cierran frase.
_SIGLA = re.compile(r"\b([A-ZÁÉÍÓÚÑ]{1,3})\.(?=\s?[A-ZÁÉÍÓÚÑ]{1,3}\.)")
_PUNTO_ANTES_DE_MINUSCULA = re.compile(r"\.(?=\s+[a-záéíóúñ])")


def contar_frases(texto: str) -> int:
    texto = _PUNTO_ANTES_DE_MINUSCULA.sub("", _SIGLA.sub(r"\1", texto.strip()))
    return len([f for f in _FRASE.findall(texto) if f.strip(" .!?")])


# RF-12.18 (D-080): de mayor a menor, la nota mínima de cada franja y su frase.
FRANJAS = ((70, "Te la recomendamos por esto."), (50, "Tienes opciones por esto."),
           (30, "No te la recomendamos, aunque puedes intentarlo."), (0, "No te la recomendamos."))


def frase_de_franja(nota: int) -> str:
    return next(frase for minimo, frase in FRANJAS if nota >= minimo)


# RF-12.17 (F7-D5): el veredicto en palabras, con los mismos cortes que las franjas.
VEREDICTOS = ((70, "Muy compatible"), (50, "Compatible"), (30, "Poco compatible"),
              (0, "No te la recomendamos"))


def veredicto(nota: int) -> str:
    return next(texto for minimo, texto in VEREDICTOS if nota >= minimo)


def sin_frase_de_franja(explicacion: str) -> str:
    for _, frase in FRANJAS:
        if explicacion.startswith(frase):
            return explicacion[len(frase):].lstrip()
    return explicacion


class Marca(BaseModel):
    """Un requisito de la oferta, por su posición desde 1 (RF-12.34)."""

    model_config = ConfigDict(extra="forbid")

    requisito: int = Field(ge=1)
    tipo: Literal["exigido", "valorable", "no_aplica"]
    cubierto: Literal["si", "a_medias", "no"]


Relacion = Literal["mismo_puesto", "afin", "otro_oficio"]


class Match(BaseModel):
    model_config = ConfigDict(extra="forbid")

    oferta_id: int
    nota: int = Field(ge=0, le=100)
    condiciones: Literal["bajo", "medio", "alto"]
    explicacion: str = ""
    cita_perfil: str = ""
    cita_oferta: str = ""
    retirada: bool = False
    marcas: list[Marca] = Field(default_factory=list)
    relacion: Relacion | None = None
    # La pone el código antes de acotar (RF-12.35); no está en el esquema que ve el modelo.
    nota_modelo: SkipJsonSchema[int | None] = None

    @model_validator(mode="after")
    def _explicacion_de_2_o_3_frases(self):
        if not self.retirada and not 2 <= contar_frases(sin_frase_de_franja(self.explicacion)) <= 3:
            raise ValueError("la explicación debe tener 2 o 3 frases")
        return self
