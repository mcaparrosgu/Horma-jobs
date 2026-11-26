"""Normaliza un título de puesto para compararlo por frase (RF-9.3c). Código puro.

Sin tildes, en minúsculas, guiones y signos como espacios y cada palabra en singular con reglas cortas.
Se aplica igual al título de la oferta y al puesto de la usuaria, así que basta con que sea coherente.
Las marcas de género («/a», «/as», «(a)», «/o») se quitan; `variantes_genero` da las formas masculina y
femenina de un puesto ya normalizado para buscarlas todas (RF-10.14p)."""
import re
import unicodedata


def _singular(palabra: str) -> str:
    if len(palabra) > 5 and palabra.endswith("es") and palabra[-3] not in "aeiou":
        return palabra[:-2]
    if len(palabra) > 3 and palabra.endswith("s") and not palabra.endswith(("ss", "is", "us")):
        return palabra[:-1]
    return palabra


_MARCA_GENERO = re.compile(
    r"(?<=[^\W\d_])(?:\s*/\s*(?:as|os|a|o)(?![^\W\d_])|"
    r"\((?:as|os|a|o)\))", re.IGNORECASE)


def _a_femenino(p: str) -> str | None:
    if p == "jefe":
        return "jefa"
    if len(p) > 4 and p.endswith("ente"):
        return p[:-1] + "a"
    if len(p) > 4 and p.endswith("or"):
        return p + "a"
    if len(p) > 4 and p.endswith("o"):
        return p[:-1] + "a"
    return None


def _a_masculino(p: str) -> str | None:
    if p == "jefa":
        return "jefe"
    if len(p) > 5 and p.endswith("enta"):
        return p[:-1] + "e"
    if len(p) > 5 and p.endswith("ora"):
        return p[:-1]
    if len(p) > 4 and p.endswith("a"):
        return p[:-1] + "o"
    return None


def variantes_genero(norm: str) -> list[str]:
    """El puesto ya normalizado más sus formas de género: todo en femenino, todo en masculino y cada palabra
    cambiada por separado («jefe de sala» → «jefa de sala»;
    «auxiliar administrativo» → «… administrativa»)."""
    palabras = norm.split()
    vistas = [norm] if norm else []

    def _anadir(ps: list[str]) -> None:
        v = " ".join(ps)
        if v and v not in vistas:
            vistas.append(v)

    for cambiar in (_a_femenino, _a_masculino):
        _anadir([cambiar(p) or p for p in palabras])
        for i, p in enumerate(palabras):
            if (nueva := cambiar(p)):
                _anadir(palabras[:i] + [nueva] + palabras[i + 1:])
    return vistas


def normalizar_titulo(titulo: str | None) -> str:
    if not titulo:
        return ""
    titulo = _MARCA_GENERO.sub("", titulo)
    t = unicodedata.normalize("NFKD", titulo)
    t = "".join(c for c in t if not unicodedata.combining(c)).casefold()
    palabras = re.sub(r"[^a-z0-9+#]+", " ", t).split()
    return " ".join(_singular(p) for p in palabras)


def canonico(titulo: str) -> str:
    """La misma clave para las formas de género de un puesto."""
    return min(variantes_genero(normalizar_titulo(titulo)), default="")


# RF-12.9: solos, dicen demasiado poco; casan únicamente con ofertas de la familia del perfil.
_GENERICOS = {normalizar_titulo(t) for t in (
    "Manager", "Técnico", "Técnica", "Responsable", "Especialista", "Consultor", "Consultora", "Consultant",
    "Engineer", "Developer", "Director", "Directora")}


def es_generico(puesto: str) -> bool:
    return normalizar_titulo(puesto) in _GENERICOS


# D-038: el nivel mínimo del perfil que pide cada palabra de un título.
_ESCALONES = {"practicas": 0, "junior": 1, "intermedio": 2, "senior": 3, "direccion": 4}
_PIDEN = {"senior": 3, "sr": 3, "lead": 3, "jefe": 3, "jefa": 3, "head": 4, "chief": 4, "director": 4,
          "directora": 4}


def supera_nivel(titulo: str, nivel: str) -> bool:
    """¿El título indica un nivel por encima del perfil (RF-12.8)? Sin nivel conocido, no."""
    tope = _ESCALONES.get(nivel)
    return tope is not None and any(_PIDEN.get(p, 0) > tope for p in normalizar_titulo(titulo).split())


def casa_con_puestos(titulo: str | None, puestos: list[str], *, familia_perfil: str | None = None,
                     familia_oferta: str | None = None) -> bool:
    """¿Algún puesto (o su forma de género) aparece como frase en el título? La misma regla que el filtro
    de `buscar_ofertas`, en Python: un genérico no cuenta si las dos familias se conocen y no coinciden."""
    t = f" {normalizar_titulo(titulo)} "
    otra_familia = bool(familia_perfil and familia_oferta and familia_perfil != familia_oferta)
    return any(f" {v} " in t for p in puestos if not (otra_familia and es_generico(p))
               for v in variantes_genero(normalizar_titulo(p)))
