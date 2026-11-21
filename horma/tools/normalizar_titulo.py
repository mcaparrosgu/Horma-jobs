"""Normaliza un título de puesto para compararlo por frase (RF-9.3c). Código puro.

Sin tildes, en minúsculas, guiones y signos como espacios y cada palabra en singular con reglas cortas.
Se aplica igual al título de la oferta y al puesto de la usuaria, así que basta con que sea coherente."""
import re
import unicodedata


def _singular(palabra: str) -> str:
    if len(palabra) > 5 and palabra.endswith("es") and palabra[-3] not in "aeiou":
        return palabra[:-2]
    if len(palabra) > 3 and palabra.endswith("s") and not palabra.endswith(("ss", "is", "us")):
        return palabra[:-1]
    return palabra


def normalizar_titulo(titulo: str | None) -> str:
    if not titulo:
        return ""
    t = unicodedata.normalize("NFKD", titulo)
    t = "".join(c for c in t if not unicodedata.combining(c)).casefold()
    palabras = re.sub(r"[^a-z0-9+#]+", " ", t).split()
    return " ".join(_singular(p) for p in palabras)
