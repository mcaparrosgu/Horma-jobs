from pydantic import BaseModel, Field

from horma.schemas.candidatura import EtiquetaRespuesta


class EntradaClasificadorRespuesta(BaseModel):
    texto: str = Field(min_length=1, description="Correo de la empresa pegado por la usuaria: no fiable.")


class SalidaClasificadorRespuesta(BaseModel):
    etiqueta: EtiquetaRespuesta
    instrucciones_embebidas: list[str] = Field(default_factory=list)
