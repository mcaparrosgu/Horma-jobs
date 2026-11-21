from pydantic import BaseModel, Field

from horma.schemas.oferta import OfertaExtraida
from horma.schemas.taxonomia import Taxonomia


class TextoOferta(BaseModel):
    texto: str = Field(min_length=1)
    fuente: str | None = None
    url: str | None = None


class SalidaAnalizador(BaseModel):
    """Lo que juzga el modelo en una sola lectura. Fecha, repetición, salario y DNS los decide el código."""

    oferta: OfertaExtraida
    taxonomia: Taxonomia
    generica: bool = Field(description="Verdadero si la oferta no concreta puesto, tareas ni "
                                       "empresa: podría servir para cualquier cosa.")
    fraude: bool = Field(description="Verdadero si pide dinero, datos bancarios o pagos por "
                                     "adelantado a la candidata.")
    senales_fraude: list[str] = Field(default_factory=list,
                                      description="Citas literales del texto que lo prueban.")
    dominio_empresa: str | None = Field(default=None,
                                        description="Correo o web de la empresa tal como "
                                                    "aparece en el texto.")
