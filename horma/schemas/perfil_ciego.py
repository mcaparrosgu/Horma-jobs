"""La copia ciega del perfil (spec 012, RF-12.30a; S12): lo único que leen el clasificador y el `matcher`.

Es una lista blanca por esquema: un campo nuevo del perfil no llega al modelo hasta que se añade aquí."""
from pydantic import BaseModel, ConfigDict, Field

from horma.schemas.filtros import Idioma
from horma.schemas.taxonomia import Taxonomia


class _Ciego(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExperienciaCiega(_Ciego):
    puesto: str
    empresa: str | None = None
    inicio: str | None = None
    fin: str | None = None
    descripcion: str | None = None


class FormacionCiega(_Ciego):
    titulo: str
    inicio: str | None = None
    fin: str | None = None


class IdiomaCiego(_Ciego):
    idioma: Idioma
    nivel: str | None = None


class HabilidadCiega(_Ciego):
    nombre: str


class ProyectoCiego(_Ciego):
    nombre: str
    descripcion: str | None = None
    fecha: str | None = None


class CertificacionCiega(_Ciego):
    nombre: str
    entidad: str | None = None
    fecha: str | None = None


class OtroCiego(_Ciego):
    valor: str


class PerfilCiego(_Ciego):
    experiencias: list[ExperienciaCiega] = Field(default_factory=list)
    formacion: list[FormacionCiega] = Field(default_factory=list)
    idiomas: list[IdiomaCiego] = Field(default_factory=list)
    habilidades: list[HabilidadCiega] = Field(default_factory=list)
    proyectos: list[ProyectoCiego] = Field(default_factory=list)
    certificaciones: list[CertificacionCiega] = Field(default_factory=list)
    otros: list[OtroCiego] = Field(default_factory=list)
    taxonomia: Taxonomia | None = Field(default=None, description="Solo para el `matcher`.")
