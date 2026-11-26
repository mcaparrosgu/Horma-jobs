"""Construye la copia ciega de un perfil (spec 012, RF-12.30; D-043 a D-051). Código puro, sin modelo.

En todo texto se borran los correos, las URL, los teléfonos y el nombre de la usuaria, y las palabras del
léxico pasan a la forma de la copia. Las fechas no cambian (D-044) y el perfil no se toca."""
import re
import unicodedata

from horma.schemas.perfil import Perfil
from horma.schemas.perfil_ciego import PerfilCiego
from horma.tools.lexico_genero import a_copia

_CONTACTO = re.compile(
    r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"                                  # correo
    r"|\b(?:https?://|www\.)[^\s,;)]+"                               # URL
    r"|\b(?:[\w-]+\.)+[a-z]{2,}/[^\s,;)]*"                           # dominio con ruta
    r"|\b(?:[a-z0-9-]+\.)+(?:com|es|org|cat|eu)\b"                   # dominio suelto
    r"|(?<![\w.,-])(?:\+\d{1,3}[\s.-]?\d(?:[\s.-]?\d){7,11}"         # teléfono con prefijo
    r"|[6789]\d{2}(?:[\s.-]?\d){6})(?![\w-])")                       # teléfono de nueve cifras
_NUNCA = {"del", "las", "los", "van", "von", "san"}  # D-051
# (sección, campo) → es un oficio o un estudio: ahí no se borra el nombre y cuenta la primera palabra.
_TITULOS = {("experiencias", "puesto"), ("formacion", "titulo"), ("certificaciones", "nombre")}
_SIN_TOCAR = {"inicio", "fin", "fecha", "idioma"}


def _sin_tildes(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c))


def _patron_del_nombre(nombre: str | None) -> re.Pattern | None:
    palabras = {p for p in re.findall(r"[^\W\d_]+", nombre or "")
                if len(p) >= 3 and p.casefold() not in _NUNCA}
    formas = sorted(palabras | {_sin_tildes(p) for p in palabras}, key=len, reverse=True)
    if not formas:
        return None
    return re.compile(r"\b(?:" + "|".join(map(re.escape, formas)) + r")\b", re.IGNORECASE)


def _texto(valor: str, nombre: re.Pattern | None, titulo: bool) -> str:
    limpio = _CONTACTO.sub("", valor)
    if nombre and not titulo:
        limpio = nombre.sub("", limpio)
    if limpio != valor:  # lo borrado no deja huecos que distingan a dos gemelas
        limpio = re.sub(r"\(\s*[,;\s]*\)", "", limpio)
        limpio = re.sub(r"\s+([,;:.)])", r"\1", re.sub(r"\s{2,}", " ", limpio))
        limpio = re.sub(r"^[\s,;:.-]+", "", limpio).strip()
    return a_copia(limpio, titulo=titulo)


def copia_ciega(perfil: Perfil, *, con_taxonomia: bool = False) -> PerfilCiego:
    nombre = _patron_del_nombre(perfil.nombre)
    datos = perfil.model_dump(mode="json")
    copia: dict = {}
    for seccion, definicion in PerfilCiego.model_fields.items():
        if seccion == "taxonomia":
            continue
        modelo = definicion.annotation.__args__[0]
        copia[seccion] = [{
            campo: x[campo] if x[campo] is None or campo in _SIN_TOCAR
            else _texto(x[campo], nombre, (seccion, campo) in _TITULOS)
            for campo in modelo.model_fields
        } for x in datos[seccion]]
    if con_taxonomia:
        copia["taxonomia"] = datos["taxonomia"]
    return PerfilCiego.model_validate(copia)
