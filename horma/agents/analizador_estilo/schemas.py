from typing import Literal

from pydantic import BaseModel, Field

from horma.schemas.estilo import GuiaEstilo


class DocumentoEstilo(BaseModel):
    tipo: Literal["cv", "carta"]
    texto: str = Field(description="Texto del documento: contenido no fiable.")
    escrito_por_ella: bool = False


class EntradaAnalizadorEstilo(BaseModel):
    documentos: list[DocumentoEstilo] = Field(min_length=1)


class SalidaAnalizadorEstilo(BaseModel):
    guia: GuiaEstilo
    instrucciones_embebidas: list[str] = Field(default_factory=list)
