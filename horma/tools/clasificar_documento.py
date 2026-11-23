"""Detecta con reglas si un documento subido es un CV o una carta (RF-10.14b). Código puro, sin modelo.

Un CV tiene secciones con título («Experiencia», «Formación»…) y periodos con fechas; una carta, saludo,
párrafos largos y despedida. Si las señales no bastan o se contradicen, devuelve «duda» y la app
lo pregunta."""
import re
import unicodedata
from typing import Literal

Clase = Literal["cv", "carta", "duda"]

_SECCIONES = (
    "experiencia", "formacion", "educacion", "estudios", "idiomas", "habilidades", "competencias", "perfil",
    "resumen", "cursos", "certificaciones", "proyectos", "datos personales", "otros datos", "referencias",
    "informacion adicional", "sobre mi", "objetivo profesional", "voluntariado", "tecnologias")
_SECCION = re.compile(r"^(?:" + "|".join(_SECCIONES) + r")\b")
_MES = r"(?:ene|feb|mar|abr|may|jun|jul|ago|sep|set|oct|nov|dic)[a-z]*\.?\s+"
_FECHA = rf"(?:{_MES}|\d{{1,2}}[/-])?(?:19|20)\d{{2}}"
_PERIODO = re.compile(rf"{_FECHA}\s*[–—\-]\s*(?:{_FECHA}|actualidad|actual|presente|hoy)\b", re.IGNORECASE)
_SALUDO = re.compile(r"^(?:hola|estimad[oa]s?|querid[oa]s?|buenos d[ií]as|buenas tardes|buenas|"
                     r"a la atenci[oó]n|apreciad[oa]s?|dear|hello)\b", re.IGNORECASE)
_DESPEDIDA = re.compile(r"^(?:un saludo|saludos|un cordial saludo|atentamente|cordialmente|un abrazo|"
                        r"muchas gracias|gracias|quedo a la espera|sincerely|"
                        r"best regards|kind regards|regards)\b",
                        re.IGNORECASE)
_APERTURA = re.compile(r"\b(?:os|les|te|le) escribo\b|\bme dirijo a\b|"
                       r"\bescribo (?:por|para|en relaci[oó]n)\b",
                       re.IGNORECASE)
_PARRAFO_LARGO = 120  # caracteres: una línea así es prosa, no un dato de CV


def _plano(linea: str) -> str:
    t = unicodedata.normalize("NFKD", linea)
    return "".join(c for c in t if not unicodedata.combining(c)).casefold().strip(" :•·-*#\t")


def es_titulo_de_seccion(linea: str) -> bool:
    """¿Es una línea corta que abre una sección de CV («Experiencia», «Formación»…)?"""
    return len(linea.strip()) <= 40 and bool(_SECCION.match(_plano(linea)))


def clasificar_documento(texto: str) -> Clase:
    lineas = [x.strip() for x in (texto or "").splitlines() if x.strip()]
    if len(lineas) < 3:
        return "duda"
    secciones = sum(1 for x in lineas if es_titulo_de_seccion(x))
    periodos = len(_PERIODO.findall(texto))
    saludo = any(_SALUDO.match(x) for x in lineas[:8])
    despedida = any(_DESPEDIDA.match(x) for x in lineas[-6:])
    parrafos = sum(1 for x in lineas
                   if len(x) >= _PARRAFO_LARGO and x.rstrip().endswith((".", ":", "!", "?")))
    apertura = bool(_APERTURA.search(texto))

    puntos_cv = min(secciones, 2) + min(periodos, 2)
    puntos_carta = 2 * saludo + 2 * despedida + (parrafos >= 2) + apertura
    if puntos_cv >= 3 and puntos_cv >= puntos_carta + 2:
        return "cv"
    if puntos_carta >= 3 and puntos_carta >= puntos_cv + 2:
        return "carta"
    return "duda"
