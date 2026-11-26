from pydantic import BaseModel, Field


class EntradaSinonimos(BaseModel):
    puestos: list[str]


class OtrasFormas(BaseModel):
    puesto: str
    otras: list[str] = Field(default_factory=list, description="Hasta 8 formas de anunciar ese mismo puesto.")


class SalidaSinonimos(BaseModel):
    puestos: list[OtrasFormas] = Field(default_factory=list)
