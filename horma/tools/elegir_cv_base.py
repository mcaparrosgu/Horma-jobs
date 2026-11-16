"""Elige con código el CV base más adecuado para una oferta (RF-3.1b, P14). Sin modelo, sin disco.

Entre los CV base de la usuaria que no están rechazados gana el que coincide en familia y sector con la
oferta; después, en familia; después, en sector; si no coincide ninguno, el más reciente. A igualdad,
el más reciente (`creado_en`; si falta, el `id` mayor). Devuelve el CV base y el motivo en llano."""
from collections.abc import Mapping, Sequence
from datetime import datetime

MOTIVOS = ("Coincide en puesto y sector con la oferta", "Coincide en el puesto",
           "Coincide en el sector", "Ninguno coincide; es el más reciente")


def _campo(obj, nombre: str):
    return obj.get(nombre) if isinstance(obj, Mapping) else getattr(obj, nombre, None)


def _instante(cv: Mapping) -> float:
    creado = cv.get("creado_en")
    return creado.timestamp() if isinstance(creado, datetime) else 0.0


def elegir_cv_base(oferta, cvs_base: Sequence[Mapping], usuaria_id: int) -> tuple[Mapping, str]:
    """`oferta`: una `Oferta` o su dict. Lanza `ValueError` si la usuaria no tiene ningún CV base válido."""
    candidatos = [c for c in cvs_base if c.get("estado") == "hecho" and c.get("usuaria_id") == usuaria_id]
    if not candidatos:
        raise ValueError("la usuaria no tiene ningún CV base válido: hay que generarlo primero")
    taxonomia = _campo(oferta, "taxonomia")
    familia, sector = _campo(taxonomia, "familia"), _campo(taxonomia, "sector")

    def rango(c: Mapping) -> int:
        igual_familia, igual_sector = c.get("familia") == familia, c.get("sector") == sector
        return 0 if igual_familia and igual_sector else 1 if igual_familia else 2 if igual_sector else 3

    elegido = min(candidatos, key=lambda c: (rango(c), -_instante(c), -(c.get("id") or 0)))
    return elegido, MOTIVOS[rango(elegido)]
