"""Fuentes de ofertas y su calificación (RF-1.1, RF-1.7)."""
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Variables que una fuente nunca puede leer: son los secretos de la propia Horma.
SECRETOS_DE_HORMA = {
    "ANTHROPIC_API_KEY", "DATABASE_URL", "DATABASE_URL_MIGRACIONES", "SESSION_SECRET",
    "GOOGLE_CLIENT_SECRET", "GOOGLE_CLIENT_ID", "POSTGRES_PASSWORD", "HORMA_APP_PASSWORD",
    "HORMA_MIGRADOR_PASSWORD", "HORMA_CLAVE_INGESTA",
}
_VARIABLE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class Fuente(BaseModel):
    nombre: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,40}$")
    web: str = Field(pattern=r"^https://", description="Portal (se califica su dominio).")
    url: str = Field(pattern=r"^https://", description="Endpoint de la API de ofertas.")
    metodo: Literal["GET", "POST"] = "GET"
    parametros: dict[str, str | int | float | bool] = Field(default_factory=dict)
    cabeceras: dict[str, str] = Field(default_factory=dict)
    variable_clave: str | None = Field(
        default=None, description="Variables de entorno con la clave, separadas por comas; se "
                                  "usan como ${VAR} en parámetros y cabeceras.")
    mapeo: dict[str, str] = Field(description="Campo de Horma → ruta en la respuesta (a.b.c).")
    activa: bool = False

    @field_validator("variable_clave")
    @classmethod
    def _variables_permitidas(cls, v: str | None) -> str | None:
        if not v:
            return None
        nombres = [n.strip() for n in v.split(",") if n.strip()]
        for n in nombres:
            if not _VARIABLE.match(n) or n in SECRETOS_DE_HORMA:
                raise ValueError(f"variable no permitida: {n}")
        return ",".join(nombres)

    def variables(self) -> list[str]:
        return self.variable_clave.split(",") if self.variable_clave else []


class CalificacionFuente(BaseModel):
    url: str
    apta: bool
    excluida_por_regla: bool = False
    permite_uso_automatizado: bool | None = None
    robots_permite: bool | None = None
    requiere_clave: bool = False
    motivos: list[str] = Field(default_factory=list)
    citas: list[str] = Field(default_factory=list)  # citas literales de las condiciones
    instrucciones_embebidas: list[str] = Field(default_factory=list)
