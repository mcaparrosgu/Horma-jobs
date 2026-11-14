"""Detecta menciones de rasgos personales que Horma no debe usar ni guardar (RF-2.6, RF-2.14, RT-09).

Código puro con una lista cerrada de patrones por categoría: edad, nacionalidad, sexo, familia o
estado civil, salud, religión, origen étnico, orientación sexual y afiliación política o sindical.
Devuelve `«categoría: texto encontrado»` por cada coincidencia; vacío si no hay ninguna. Lo usan el
flujo `perfilar` (para descartar datos del CV) y `recomendar` (para retirar explicaciones), y los evals.

Es deliberadamente conservador con las palabras ambiguas: «tres años de experiencia» o «Centro de
Salud» no son rasgos personales. Lo que se escapa, lo detecta el juez de los evals."""
import re
import unicodedata

_PATRONES: dict[str, list[str]] = {
    "edad": [
        r"\bedad\b", r"\bfecha de nacimiento\b", r"\bnacid[oa] (?:en|el)\b", r"\bnacimiento\b",
        r"\b(?:tiene|tienes|cumple|cumplio|cumplir)\s+(?:\w+\s+)?\d{1,2}\s+anos\b",
        r"\b(?:mayor|menor)\s+de\s+\d{2}\s+anos\b", r"\bjoven(?:es)?\b", r"\bjuventud\b",
        r"\banciana?\b", r"\bveterana?\b",
    ],
    "nacionalidad": [
        r"\bnacionalidad\b", r"\bextranjer[oa]s?\b", r"\binmigrante", r"\bciudadan[oa] de\b",
        r"\bde origen (?:espanol|extranjero|marroqui|latino)",
    ],
    "sexo": [r"\b(?:mujer|mujeres|hombre|hombres|varon|varones|femenin[oa]s?|masculin[oa]s?)\b"],
    "familia": [
        r"\bcasad[oa]s?\b", r"\bsolter[oa]s?\b", r"\bdivorciad[oa]s?\b", r"\bviud[oa]s?\b",
        r"\bembaraz", r"\bmaternidad\b", r"\bpaternidad\b", r"\bhij[oa]s\b", r"\bfamilia numerosa\b",
        r"\bestado civil\b",
    ],
    "salud": [
        r"\bdiscapacidad\b", r"\bminusval", r"\benfermedad\b", r"\bpadece", r"\bdiagnostic",
        r"\bproblemas? de salud\b", r"\bestado de salud\b", r"\bbaja medica\b", r"\bcondicion medica\b",
    ],
    "religion": [
        r"\breligion\b", r"\breligios[oa]s?\b", r"\bcatolic[oa]s?\b", r"\bmusulman",
        r"\bjudi[oa]s?\b", r"\bcristian[oa]s?\b", r"\bateo\b", r"\bhijab\b",
    ],
    "origen_etnico": [r"\braza\b", r"\bracial", r"\betnic", r"\betnia\b", r"\bgitan[oa]s?\b"],
    "orientacion": [
        r"\borientacion sexual\b", r"\bhomosexual", r"\bgay\b", r"\blesbian", r"\btransexual",
        r"\btransgenero", r"\blgtb",
    ],
    "politica_sindical": [
        r"\bafiliacion (?:sindical|politica)\b", r"\bsindicad[oa]s?\b", r"\bideologia\b",
        r"\bmilitante\b",
    ],
}
_COMPILADOS = [(cat, re.compile(p)) for cat, lista in _PATRONES.items() for p in lista]


def _plano(texto: str) -> str:
    t = unicodedata.normalize("NFD", texto)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").casefold()
    return re.sub(r"\s+", " ", t)


def rasgos_personales(texto: str) -> list[str]:
    plano = _plano(texto)
    encontrados: list[str] = []
    for categoria, patron in _COMPILADOS:
        for m in patron.finditer(plano):
            marca = f"{categoria}: {m.group(0).strip()}"
            if marca not in encontrados:
                encontrados.append(marca)
    return encontrados
