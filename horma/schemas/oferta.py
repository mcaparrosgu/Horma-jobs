from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, computed_field, model_validator

from horma.schemas.taxonomia import Taxonomia


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


MotivoFantasma = Literal["sin_fecha", "repetida", "generica"]


class Auditoria(BaseModel):
    """Resultado de auditar una oferta (RF-1.5). Lo determinista lo decide el código."""

    fantasma: bool
    motivos_fantasma: list[MotivoFantasma] = Field(default_factory=list)
    fraude: bool
    senales_fraude: list[str] = Field(default_factory=list)  # citas literales del texto
    dominio_empresa: str | None = None
    empresa_validada: bool | None = None  # None: no había dominio o no se comprobó
    salario_publicado: bool
    salario_rango: str | None = None
    frase_pedir_salario: str | None = None


class Oferta(OfertaExtraida):
    """Oferta completa: extraída, auditada y clasificada."""

    auditoria: Auditoria
    taxonomia: Taxonomia

    @computed_field
    @property
    def recomendable(self) -> bool:
        """Las fantasma y las fraudulentas quedan fuera de la recomendación (RF-1.9)."""
        return not (self.auditoria.fantasma or self.auditoria.fraude)
