"""Taxonomía compartida por ofertas y perfiles (fase 1 y fase 2). Lista cerrada: cambiarla es un
cambio de contrato."""
from typing import Literal, get_args

from pydantic import BaseModel, Field, field_validator

# Sector: a qué se dedica la empresa.
Sector = Literal[
    "hosteleria_turismo", "sanidad", "tecnologia", "administracion_publica", "comercio_retail",
    "logistica_transporte", "educacion", "industria", "construccion", "finanzas_seguros",
    "servicios_profesionales", "medios_marketing", "otros",
]
# Familia de puesto: qué hace la persona, sea cual sea el sector.
Familia = Literal[
    "administracion_oficina", "atencion_cliente", "ventas_comercial", "hosteleria_restauracion",
    "sanidad_cuidados", "educacion_formacion", "logistica_transporte", "produccion_operarios",
    "construccion_oficios", "desarrollo_software", "datos_ia", "sistemas_redes",
    "diseno_creatividad", "marketing_comunicacion", "finanzas_contabilidad", "recursos_humanos",
    "legal", "direccion_gestion", "otros",
]
Nivel = Literal["practicas", "junior", "intermedio", "senior", "direccion", "sin_especificar"]

SECTORES: tuple[str, ...] = get_args(Sector)
FAMILIAS: tuple[str, ...] = get_args(Familia)
NIVELES: tuple[str, ...] = get_args(Nivel)


class Taxonomia(BaseModel):
    sector: Sector
    familia: Familia
    nivel: Nivel
    stack: list[str] = Field(default_factory=list,
                             description="Herramientas, tecnologías o carnés que pide la oferta, "
                                         "en minúsculas y tal como aparecen en el texto.")

    @field_validator("stack")
    @classmethod
    def _normalizar(cls, v: list[str]) -> list[str]:
        vistos: list[str] = []
        for x in v:
            x = x.strip().casefold()
            if x and x not in vistos:
                vistos.append(x)
        return vistos
