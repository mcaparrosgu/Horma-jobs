"""Visibilidad de las experiencias en un CV base (RF-5.1g). Código puro.

Cada experiencia de un CV base puede estar `completa` (con su descripción), `condensada` (una sola
línea: puesto · empresa · fechas) u `oculta` (no sale). La clave de una experiencia es
`puesto|empresa|inicio` normalizada: los índices del perfil cambian entre versiones, esa clave no.
`verificar_visibilidad` devuelve los errores en español (vacía si se respeta lo marcado); el flujo
se los pasa al generador para que corrija, como con la trazabilidad."""
import re
import unicodedata
from collections.abc import Mapping

from horma.schemas.perfil import Experiencia, Perfil

VALORES = ("completa", "condensada", "oculta")


def normalizar(texto: str | None) -> str:
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().casefold()


def clave_experiencia(x: Experiencia) -> str:
    return "|".join((normalizar(x.puesto), normalizar(x.empresa), normalizar(x.inicio)))


def nombre_experiencia(x: Experiencia) -> str:
    return " · ".join(p for p in (x.puesto, x.empresa) if p)


def verificar_visibilidad(contenido: str, perfil: Perfil, visibilidad: Mapping[str, str]) -> list[str]:
    lineas = [normalizar(linea) for linea in contenido.splitlines()]
    texto = normalizar(contenido)
    errores = []
    for x in perfil.experiencias:
        valor = visibilidad.get(clave_experiencia(x))
        if valor not in VALORES:
            continue
        sale = any(normalizar(x.puesto) in linea and (not x.empresa or normalizar(x.empresa) in linea)
                   for linea in lineas)
        nombre = f"«{nombre_experiencia(x)}»"
        if valor == "oculta" and sale:
            errores.append(f"La experiencia {nombre} está marcada como oculta: quítala del CV base")
        elif valor != "oculta" and not sale:
            errores.append(f"La experiencia {nombre} está marcada como {valor}: debe salir en el CV base")
        elif valor == "condensada" and x.descripcion and normalizar(x.descripcion) in texto:
            errores.append(f"La experiencia {nombre} está marcada como condensada: déjala en una sola "
                           "línea, sin su descripción")
    return errores
