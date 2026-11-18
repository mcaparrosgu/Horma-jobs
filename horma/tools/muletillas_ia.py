"""Busca muletillas y frases genéricas típicas de texto de IA en un CV o una carta (RF-5.7).

Código puro. La lista versionada está en `horma/assets/muletillas_ia.json`: expresiones en minúsculas,
sin acentos y con las variantes de género escritas aparte. El «…» dentro de una expresión admite unas
pocas palabras en medio («no solo… sino también»). Se compara sin acentos ni mayúsculas y por palabras
completas. Devuelve las expresiones halladas (las de la lista, sin repetir y en orden de aparición);
vacío si no hay ninguna. No usa detectores externos: no son fiables (RF-5.7d)."""
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

RUTA = Path(__file__).resolve().parent.parent / "assets" / "muletillas_ia.json"
_HUECO = r"[^.\n]{1,80}?"


def _normalizar(texto: str) -> str:
    sin_acentos = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return sin_acentos.lower()


@lru_cache(maxsize=1)
def _patrones() -> list[tuple[str, re.Pattern[str]]]:
    lista = json.loads(RUTA.read_text(encoding="utf-8"))

    def patron(x: str) -> re.Pattern[str]:
        cuerpo = _HUECO.join(re.escape(p) for p in x.split("…")).replace(r"\ ", r"\s+")
        return re.compile(r"\b" + cuerpo + r"\b")

    return [(x, patron(x)) for x in lista]


def muletillas_ia(texto: str) -> list[str]:
    limpio = _normalizar(texto)
    halladas = [(m.start(), x) for x, patron in _patrones() if (m := patron.search(limpio))]
    return [x for _, x in sorted(halladas)]


def errores_muletillas(documento: str, texto: str) -> list[str]:
    """Un error por muletilla, con la línea donde aparece, para `comprobar` y la verificación del CV base."""
    articulo = "el CV" if documento == "cv" else "la carta"
    errores = []
    for linea in (x.strip() for x in texto.splitlines() if x.strip()):
        errores += [f"Muletilla de IA en {articulo}: {m} (frase «{linea}»)" for m in muletillas_ia(linea)]
    return errores
