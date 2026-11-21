"""Perfil de la usuaria con el origen de cada dato (RF-2.2, RF-2.3, RF-2.6).

Todo dato lleva su `origen`: la cita literal del CV de la que sale, o «usuaria» si lo escribió ella.
Si un dato no tiene origen no entra en el perfil: va a `preguntas_pendientes` (RT-08). El perfil NO
tiene campos para edad, nacionalidad ni categorías del art. 9 del RGPD (RT-09): `extra="forbid"` hace
que cualquier intento de añadirlos falle."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from horma.schemas.filtros import Idioma
from horma.schemas.taxonomia import Taxonomia


class OrigenDato(BaseModel):
    """De dónde sale un dato del perfil."""

    model_config = ConfigDict(extra="forbid")

    fuente: Literal["cv", "usuaria"] = "cv"
    cv_id: int | None = None
    fragmento: str = Field(min_length=1, description="Cita literal del CV, o lo que escribió ella.")

    @model_validator(mode="after")
    def _cv_si_viene_del_cv(self):
        if self.fuente == "cv" and self.cv_id is None:
            raise ValueError("un dato que viene del CV debe indicar de qué CV (cv_id)")
        return self


class _ConOrigen(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Experiencia(_ConOrigen):
    puesto: str = Field(min_length=1)
    empresa: str | None = None
    inicio: str | None = Field(default=None, description="AAAA o AAAA-MM, tal como aparece en el CV.")
    fin: str | None = Field(default=None, description="AAAA, AAAA-MM o «actual»; vacío si no aparece.")
    descripcion: str | None = None
    origen: OrigenDato


class Formacion(_ConOrigen):
    titulo: str = Field(min_length=1)
    centro: str | None = None
    inicio: str | None = None
    fin: str | None = None
    origen: OrigenDato


class IdiomaPerfil(_ConOrigen):
    idioma: Idioma
    nivel: str | None = Field(default=None, description="Nivel tal como lo dice el CV (B2, nativo…).")
    origen: OrigenDato


class Habilidad(_ConOrigen):
    nombre: str = Field(min_length=1)
    origen: OrigenDato


class DatoTexto(_ConOrigen):
    valor: str = Field(min_length=1)
    origen: OrigenDato


class Proyecto(_ConOrigen):
    nombre: str = Field(min_length=1)
    descripcion: str | None = None
    fecha: str | None = Field(default=None, description="AAAA o AAAA-MM, si aparece.")
    origen: OrigenDato


class Certificacion(_ConOrigen):
    nombre: str = Field(min_length=1)
    entidad: str | None = None
    fecha: str | None = Field(default=None, description="AAAA o AAAA-MM, si aparece.")
    origen: OrigenDato


class OtroDato(_ConOrigen):
    """Lo que no encaja en otra sección y ella quiere en su CV (carnet de conducir, disponibilidad…)."""

    valor: str = Field(min_length=1)
    origen: OrigenDato


class Actividad(_ConOrigen):
    """Voluntariado, cuidados, viajes, excedencias… que cubren un hueco del CV (RF-9.1d)."""

    descripcion: str = Field(min_length=1)
    inicio: str | None = Field(default=None, description="AAAA o AAAA-MM, si aparece.")
    fin: str | None = Field(default=None, description="AAAA, AAAA-MM o «actual»; vacío si no aparece.")
    origen: OrigenDato


_FECHA = r"^(\d{4}(-(0[1-9]|1[0-2]))?|actual)$"


class PeriodoCubierto(BaseModel):
    """Periodo sin trabajo ni formación que ella ya ha explicado. Sin motivo ni cita: solo cuenta para
    los huecos (RF-9.1d). Solo fechas; no admite texto."""

    model_config = ConfigDict(extra="forbid")

    inicio: str = Field(pattern=_FECHA)
    fin: str = Field(pattern=_FECHA)


class PreguntaPendiente(BaseModel):
    """Lo que falta, es ambiguo o se contradice entre CV: se le pregunta a la usuaria."""

    model_config = ConfigDict(extra="forbid")

    campo: str = Field(min_length=1)
    motivo: Literal["falta", "ambiguo", "contradiccion"]
    pregunta: str = Field(min_length=1)
    opciones: list[str] = Field(default_factory=list)


class Perfil(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(default=1, ge=1)
    nombre: str | None = None
    genero_puestos: Literal["femenino", "masculino"] | None = Field(
        default=None,
        description="Género gramatical con el que se escriben los puestos en sus CV (camarera/camarero). "
                    "Lo fija ella o sale de su CV; nunca se deduce del nombre.")
    titular: DatoTexto | None = None
    resumen: DatoTexto | None = None
    experiencias: list[Experiencia] = Field(default_factory=list)
    formacion: list[Formacion] = Field(default_factory=list)
    idiomas: list[IdiomaPerfil] = Field(default_factory=list)
    habilidades: list[Habilidad] = Field(default_factory=list)
    proyectos: list[Proyecto] = Field(default_factory=list)
    certificaciones: list[Certificacion] = Field(default_factory=list)
    otros: list[OtroDato] = Field(default_factory=list)
    actividades: list[Actividad] = Field(default_factory=list)
    periodos_cubiertos: list[PeriodoCubierto] = Field(default_factory=list)
    taxonomia: Taxonomia | None = None
    preguntas_pendientes: list[PreguntaPendiente] = Field(default_factory=list)
    instrucciones_embebidas: list[str] = Field(default_factory=list)
