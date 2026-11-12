from pydantic import BaseModel, Field


class EntradaAuditorFuentes(BaseModel):
    url: str
    condiciones: str = Field(min_length=1, description="Texto de las condiciones de uso.")
    robots: str | None = None


class SalidaAuditorFuentes(BaseModel):
    permite_uso_automatizado: bool | None = Field(
        description="Verdadero si las condiciones permiten leer las ofertas de forma automática "
                    "(API o acceso automatizado); falso si lo prohíben; vacío si no lo dicen.")
    requiere_clave: bool = Field(description="Verdadero si el acceso exige registro o clave de API.")
    motivos: list[str] = Field(min_length=1, max_length=4,
                               description="De 1 a 4 frases cortas que expliquen la decisión.")
    citas: list[str] = Field(default_factory=list,
                             description="Frases literales de las condiciones que la respaldan.")
    instrucciones_embebidas: list[str] = Field(default_factory=list)
