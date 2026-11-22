"""Saca el titular y el resumen de cada CV, tal como están escritos (RF-10.14d). Código puro, sin modelo.

El titular es la línea corta que sigue al nombre, antes de la primera sección; el resumen, el texto de la
sección «Resumen» o «Perfil». Si el CV no los tiene claros, no se inventan."""
import re
import unicodedata

from horma.tools.clasificar_documento import es_titulo_de_seccion

_TITULOS_RESUMEN = ("resumen", "perfil", "sobre mi", "objetivo profesional", "extracto")
_CONTACTO = re.compile(r"@|https?://|www\.|\+?\d[\d \-.]{6,}|nacimiento|nacionalidad|carnet|carn[eé]", re.IGNORECASE)
_MAX_TITULAR = 90
_MAX_RESUMEN = 1200


def _plano(linea: str) -> str:
    t = unicodedata.normalize("NFKD", linea)
    return "".join(c for c in t if not unicodedata.combining(c)).casefold().strip(" :•·-*#	")


_ANIO = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")


def titular_de(texto: str) -> str | None:
    """La primera línea tras el nombre que no sea de contacto, si parece un titular y no un dato de CV."""
    lineas = [x.strip() for x in texto.splitlines() if x.strip()]
    for linea in lineas[1:4]:   # la primera es el nombre
        if _CONTACTO.search(linea) and not _ANIO.search(linea):
            continue
        if (es_titulo_de_seccion(linea) or _ANIO.search(linea) or len(linea) > _MAX_TITULAR
                or linea.endswith(".")):
            return None
        return linea
    return None


def resumen_de(texto: str) -> str | None:
    lineas = [x.strip() for x in texto.splitlines() if x.strip()]
    for i, linea in enumerate(lineas):
        if es_titulo_de_seccion(linea) and _plano(linea).startswith(_TITULOS_RESUMEN):
            cuerpo = []
            for siguiente in lineas[i + 1:]:
                if es_titulo_de_seccion(siguiente):
                    break
                cuerpo.append(siguiente)
            resumen = " ".join(cuerpo).strip()
            return resumen if resumen and len(resumen) <= _MAX_RESUMEN else None
    return None
