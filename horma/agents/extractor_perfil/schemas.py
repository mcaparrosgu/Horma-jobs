from pydantic import BaseModel, Field

from horma.schemas.perfil import Perfil


class CvEntrada(BaseModel):
    cv_id: int
    nombre: str
    texto: str = Field(description="Texto del CV: contenido no fiable.")


class EntradaExtractorPerfil(BaseModel):
    cvs: list[CvEntrada] = Field(min_length=1)


class SalidaExtractorPerfil(BaseModel):
    perfil: Perfil
    cv_maestro: str = Field(min_length=1,
                            description="CV maestro en Markdown, con todo lo que dicen los CV.")
