from pydantic import BaseModel, Field, HttpUrl, model_validator


class Salario(BaseModel):
    minimo: float | None = Field(default=None, ge=0)
    maximo: float | None = Field(default=None, ge=0)
    moneda: str | None = None

    @model_validator(mode="after")
    def _rango_coherente(self):
        if self.minimo is not None and self.maximo is not None and self.minimo > self.maximo:
            raise ValueError("el salario mínimo no puede superar al máximo")
        return self


class OfertaExtraida(BaseModel):
    """Oferta sin auditoría ni taxonomía. Lo que no aparece en el texto queda vacío."""

    titulo: str = Field(min_length=1)
    empresa: str | None = None
    ubicacion: str | None = None
    remoto: bool | None = None
    contrato: str | None = None
    salario: Salario | None = None
    idiomas: list[str] = Field(default_factory=list)
    requisitos: list[str] = Field(default_factory=list)
    fecha_publicacion: str | None = None
    url: HttpUrl | None = None
    instrucciones_embebidas: list[str] = Field(default_factory=list)
