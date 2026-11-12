from pydantic import BaseModel, Field


class Origen(BaseModel):
    """De dónde sale un dato: cita literal del texto de partida."""

    entidad: str
    entidad_id: int
    campo: str
    fragmento: str = Field(min_length=1)
