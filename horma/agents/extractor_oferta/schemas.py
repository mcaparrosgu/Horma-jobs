from pydantic import BaseModel, Field


class TextoOferta(BaseModel):
    texto: str = Field(min_length=1)
    fuente: str | None = None
    url: str | None = None
