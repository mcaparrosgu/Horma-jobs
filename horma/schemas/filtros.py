"""Listas cerradas para los filtros de búsqueda (fase 2): país, tipo de contrato e idioma.

Las usan las preferencias de la usuaria y la normalización de las ofertas. Cambiarlas es un cambio
de contrato (como la taxonomía)."""
from typing import Literal, get_args

from pydantic import BaseModel, Field

# País donde se trabaja (ISO 3166-1 alfa-2). `REMOTO`: sin país fijo. `OTRO`: fuera de la lista.
Pais = Literal[
    "ES", "PT", "FR", "DE", "IT", "NL", "BE", "LU", "IE", "GB", "AT", "CH", "DK", "SE", "NO", "FI", "IS",
    "PL", "CZ", "SK", "HU", "RO", "BG", "GR", "HR", "SI", "EE", "LV", "LT", "MT", "CY",
    "US", "CA", "MX", "AR", "CO", "CL", "PE", "UY", "BR", "REMOTO", "OTRO",
]
# Tipo de contrato o de jornada, tal como los muestra un portal de empleo.
Contrato = Literal[
    "indefinido", "temporal", "jornada_completa", "media_jornada", "practicas", "freelance", "otro",
]
# Idioma (ISO 639-1).
Idioma = Literal[
    "es", "en", "fr", "de", "it", "pt", "ca", "eu", "gl", "nl", "pl", "ru", "zh", "ar", "ro", "otro",
]

PAISES: tuple[str, ...] = get_args(Pais)
CONTRATOS: tuple[str, ...] = get_args(Contrato)
IDIOMAS: tuple[str, ...] = get_args(Idioma)


class NormalizacionOferta(BaseModel):
    """Lo que `normalizar_oferta` deduce de una oferta para poder filtrarla (P16, P17).

    `None` significa «sin dato» o «no comparable»: el filtro deja pasar esas ofertas (P2)."""

    pais: Pais | None = None
    tipo_contrato: Contrato | None = None
    idiomas: list[Idioma] = Field(default_factory=list)
    salario_anual_eur_min: float | None = None
    salario_anual_eur_max: float | None = None
