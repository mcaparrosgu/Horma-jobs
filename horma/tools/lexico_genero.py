"""Léxico cerrado de género (spec 012, RF-12.30c; D-043 y D-049). Código puro, sin reglas de sufijos al leer.

`a_copia` pasa cada palabra del léxico a la forma de la copia ciega («Camarero/a») y `en_genero` la
devuelve al femenino o al masculino. Una palabra que no está aquí no cambia.

Cuatro clases de palabra:
- persona: cambia siempre («camarera»);
- primera: solo si es la primera de un puesto, una titulación o una certificación («técnica», «química»);
- compartida con el inglés: la forma masculina cambia solo si es la primera o va tras un artículo
  («director», «editor»: «Marketing Director» no cambia);
- adjetivo: cambia si va justo detrás de una palabra de persona («Auxiliar administrativa»).
"""
import re
import unicodedata
from typing import NamedTuple


class Forma(NamedTuple):
    copia: str
    femenino: str
    masculino: str


def _o(masculino: str) -> list[Forma]:
    """camarero / camarera, con su plural."""
    raiz = masculino[:-1]
    return [Forma(f"{raiz}o/a", f"{raiz}a", masculino), Forma(f"{raiz}os/as", f"{raiz}as", f"{raiz}os")]


def _or(masculino: str, base: str | None = None) -> list[Forma]:
    """profesor / profesora. `base` es la raíz sin tilde de los agudos («matrón» → «matron»)."""
    raiz = base or masculino
    return [Forma(f"{masculino}/a", f"{raiz}a", masculino),
            Forma(f"{raiz}es/as", f"{raiz}as", f"{raiz}es")]


def _e(masculino: str) -> list[Forma]:
    """dependiente / dependienta."""
    raiz = masculino[:-1]
    return [Forma(f"{masculino}/a", f"{raiz}a", masculino),
            Forma(f"{masculino}s/as", f"{raiz}as", f"{masculino}s")]


_PERSONA = [
    *(f for m in (
        "abogado", "alumno", "arquitecto", "becario", "bibliotecario", "bombero", "cajero", "camarero",
        "camionero", "candidato", "carnicero", "carpintero", "carretillero", "cerrajero", "charcutero",
        "cocinero", "decorador", "empleado", "encargado", "enfermero", "farmacéutico", "fontanero",
        "fotógrafo", "funcionario", "ingeniero", "licenciado", "graduado", "diplomado", "maestro",
        "mensajero",
        "mozo", "operario", "panadero", "pastelero", "peluquero", "pescadero", "portero", "psicólogo",
        "secretario", "socorrista", "sociólogo", "tornero")
      if m.endswith("o") for f in _o(m)),
    *(f for m in (
        "administrador", "animador", "asesor", "comprador", "conductor", "consultor", "contador",
        "controlador", "coordinador", "cuidador", "desarrollador", "diseñador", "educador", "entrenador",
        "gerocultor", "gestor", "investigador", "limpiador", "manipulador", "maquetador", "operador",
        "pintor",
        "profesor", "programador", "promotor", "reclutador", "redactor", "repartidor", "reponedor",
        "retocador", "soldador", "teleoperador", "traductor", "trabajador", "vendedor") for f in _or(m)),
    *(f for m in ("dependiente", "gobernante", "presidente") for f in _e(m)),
    Forma("jefe/a", "jefa", "jefe"), Forma("jefes/as", "jefas", "jefes"),
    Forma("juez/a", "jueza", "juez"), Forma("jueces/zas", "juezas", "jueces"),
    Forma("matrón/a", "matrona", "matrón"), Forma("matrones/as", "matronas", "matrones"),
    Forma("aprendiz/a", "aprendiza", "aprendiz"),
    Forma("actor/actriz", "actriz", "actor"), Forma("actores/actrices", "actrices", "actores"),
    Forma("waiter/waitress", "waitress", "waiter"), Forma("waiters/waitresses", "waitresses", "waiters"),
    Forma("modista", "modista", "modista"), Forma("modistas", "modistas", "modistas"),
]
# También son nombres de campo o adjetivos: solo cambian como primera palabra.
_PRIMERA = [f for m in (
    "administrativo", "autónomo", "científico", "estadístico", "físico", "informático", "matemático",
    "mecánico", "médico", "químico", "segundo", "técnico", "titulado", "veterinario", "voluntario",
    "electrónico", "músico", "político") for f in _o(m)]
_COMPARTIDAS = [f for m in ("auditor", "director", "doctor", "editor", "inspector", "instructor", "mentor",
                            "monitor", "supervisor", "tutor") for f in _or(m)]
_ADJETIVOS = [f for m in (
    "administrativo", "autónomo", "científico", "clínico", "comunitario", "diplomado", "electrónico",
    "estadístico", "físico", "informático", "interno", "jurídico", "mecánico", "médico", "químico",
    "sanitario", "técnico", "titulado", "voluntario") for f in _o(m)]
# Valen igual para las dos: no cambian, pero llevan el artículo doble y admiten adjetivo detrás.
_EPICENOS = (
    "agente", "analista", "asistente", "auxiliar", "ayudante", "barista", "chófer", "comercial", "conserje",
    "contable", "dentista", "docente", "electricista", "especialista", "esteticista", "estudiante",
    "fisioterapeuta", "frigorista", "generalista", "gerente", "higienista", "intérprete", "laboralista",
    "nutricionista", "periodista", "recepcionista", "representante", "responsable", "taxista", "vigilante")
# Formas que se leen pero no se escriben (la copia las lleva a otra): forma leída → forma de la copia.
_ALIAS = {"modisto": "modista", "modistos": "modistas", "ayudanta": "ayudante",
          "asistenta": "empleado/a de hogar", "asistentas": "empleados/as de hogar"}
_ARTICULOS = {  # forma doble → (femenino, masculino)
    "el/la": ("la", "el"), "los/las": ("las", "los"), "un/una": ("una", "un"), "unos/unas": ("unas", "unos"),
    "del/de la": ("de la", "del"), "de los/de las": ("de las", "de los"),
    "al/a la": ("a la", "al"), "a los/a las": ("a las", "a los"),
}


def _sin_tildes(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c))


def _indice(formas: list[Forma], *, solo_masculino: bool = False) -> dict[str, str]:
    """Palabra leída (con y sin tilde) → forma de la copia."""
    salida: dict[str, str] = {}
    for f in formas:
        leidas = (f.masculino,) if solo_masculino else (f.femenino, f.masculino, f.copia.split("/")[0])
        for palabra in leidas:
            salida[palabra] = salida[_sin_tildes(palabra)] = f.copia
    return salida


_I_PERSONA = _indice(_PERSONA) | _ALIAS
# «Personas dependientes» no es un oficio: ese plural cambia solo si es la primera o va tras un artículo.
_I_PLURAL_AMBIGUO = {"dependientes": _I_PERSONA.pop("dependientes")}
_I_PRIMERA = _indice(_PRIMERA)
_I_COMPARTIDAS = _indice(_COMPARTIDAS, solo_masculino=True) | _I_PLURAL_AMBIGUO
_I_PERSONA |= {f.femenino: f.copia for f in _COMPARTIDAS}
_I_ADJETIVOS = _indice(_ADJETIVOS)
_I_EPICENOS = {x for e in _EPICENOS for p in (e, e + ("es" if e[-1] not in "aeiou" else "s"))
               for x in (p, _sin_tildes(p))}

_PALABRA = re.compile(
    r"(?<![\w/])([^\W\d_]+)((?:\s?/\s?(?:actrices|actriz|waitresses|waitress|zas|as|os|a|o)(?![^\W\d_]))|"
    r"\((?:as|os|a|o)\))?", re.IGNORECASE)
_ANTES = re.compile(
    r"(?<![\w/])(" + "|".join(sorted(
        {a for doble, par in _ARTICULOS.items() for a in (doble, *par)}, key=len, reverse=True))
    + r")(\s+)$", re.IGNORECASE)
_DOBLE_DE = {a: doble for doble, par in _ARTICULOS.items() for a in (doble, *par)}


def _como(original: str, nueva: str) -> str:
    """La forma nueva con las mayúsculas de la original."""
    if len(original) > 1 and original.isupper():
        return nueva.upper()
    return nueva[0].upper() + nueva[1:] if original[0].isupper() else nueva


def a_copia(texto: str, *, titulo: bool = False) -> str:
    """El texto con el léxico en la forma de la copia. `titulo`: es un puesto, una titulación o una
    certificación, y su primera palabra cuenta también si es ambigua."""
    salida = ""
    fin = 0
    tras_persona = False  # la palabra anterior, pegada, es de persona
    for m in _PALABRA.finditer(texto):
        palabra, entre = m.group(1), texto[fin:m.start()]
        clave = palabra.casefold()
        primera = titulo and not (salida + entre).strip()
        articulo = _ANTES.search(salida + entre)
        copia = _I_PERSONA.get(clave)
        if copia is None and primera:
            copia = _I_PRIMERA.get(clave)
        if copia is None and (primera or articulo):
            copia = _I_COMPARTIDAS.get(clave)
        if copia is None and tras_persona and not entre.strip():
            copia = _I_ADJETIVOS.get(clave)
        persona = copia is not None or clave in _I_EPICENOS
        salida += entre
        if persona and (articulo := _ANTES.search(salida)):
            doble = _como(articulo.group(1), _DOBLE_DE[articulo.group(1).casefold()])
            salida = salida[:articulo.start()] + doble + articulo.group(2)
        salida += _como(palabra, copia) if copia else m.group(0)
        tras_persona = persona
        fin = m.end()
    return salida + texto[fin:]


_VUELTA = {f.copia: (f.femenino, f.masculino)
           for f in (*_PERSONA, *_PRIMERA, *_COMPARTIDAS, *_ADJETIVOS)} | _ARTICULOS
_COPIAS = re.compile(
    r"(?<![\w/])(" + "|".join(re.escape(c) for c in sorted(_VUELTA, key=len, reverse=True) if "/" in c)
    + r")(?![\w/])", re.IGNORECASE)


def en_genero(texto: str, genero: str | None) -> str:
    """Las formas de la copia, en femenino o en masculino. Sin género, se quedan en «/a» (RF-12.30f)."""
    if genero not in ("femenino", "masculino"):
        return texto
    i = 0 if genero == "femenino" else 1
    return _COPIAS.sub(lambda m: _como(m.group(1), _VUELTA[m.group(1).casefold()][i]), texto)
