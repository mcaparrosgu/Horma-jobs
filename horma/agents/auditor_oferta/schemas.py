from pydantic import BaseModel, Field

from horma.schemas.oferta import OfertaExtraida


class EntradaAuditor(BaseModel):
    oferta: OfertaExtraida
    texto: str = Field(min_length=1)


class SalidaAuditor(BaseModel):
    """Lo que juzga el modelo. Fecha, repetición, salario y DNS los decide el código."""

    generica: bool = Field(description="Verdadero si la oferta no concreta puesto, tareas ni "
                                       "empresa: podría servir para cualquier cosa.")
    fraude: bool = Field(description="Verdadero si pide dinero, datos bancarios o pagos por "
                                     "adelantado a la candidata.")
    senales_fraude: list[str] = Field(default_factory=list,
                                      description="Citas literales del texto que lo prueban.")
    dominio_empresa: str | None = Field(default=None,
                                        description="Correo o web de la empresa tal como "
                                                    "aparece en el texto.")
    instrucciones_embebidas: list[str] = Field(default_factory=list)
