"""Mide un CV contra lo que pide una oferta (RF-3.5). Código puro, sin umbral (RF-4.4).

Dos cosas:
1. `errores_ats`: formato compatible con ATS (sin tablas, imágenes ni HTML; encabezados estándar).
2. `medir_ats`: cobertura de las palabras clave de la oferta (sus requisitos y su stack). Una palabra
   clave está presente si todas sus palabras significativas aparecen en el texto (sin tildes ni
   mayúsculas, comparando el comienzo de cada palabra para tolerar género y número). Las ausentes se
   separan en las que tienen origen en las fuentes (el redactor puede añadirlas) y las que no (van a
   `huecos`; nunca se insertan)."""
import re
import unicodedata
from collections.abc import Mapping, Sequence

_ENCABEZADOS_ATS = ("experiencia", "formacion", "educacion", "idiomas", "habilidades", "competencias",
                    "perfil", "resumen", "certificaciones", "cursos", "contacto")
_VACIAS = {"de", "del", "la", "el", "los", "las", "en", "y", "e", "o", "a", "al", "con", "para",
           "un", "una", "por", "se", "su"}
_RAIZ = 5  # letras que se comparan de cada palabra


def _sin_tildes(texto: str) -> str:
    t = unicodedata.normalize("NFD", texto)
    return "".join(c for c in t if unicodedata.category(c) != "Mn").casefold()


def errores_ats(contenido: str) -> list[str]:
    """Formato compatible con ATS: sin tablas, imágenes ni HTML y con encabezados de sección
    estándar. Devuelve los problemas (vacío si todo va bien)."""
    errores = []
    if re.search(r"^\s*\|", contenido, re.M) or re.search(r"\|\s*:?-{3,}", contenido):
        errores.append("lleva una tabla")
    if re.search(r"!\[[^\]]*\]\(", contenido):
        errores.append("lleva una imagen")
    if re.search(r"</?[a-zA-Z][^>]*>", contenido):
        errores.append("lleva etiquetas HTML")
    secciones = re.findall(r"^\s*##\s+(.+?)\s*$", contenido, re.M)
    if not secciones:
        errores.append("no tiene encabezados de sección (## Experiencia, ## Formación…)")
    errores += [f"encabezado no estándar: «{s}»" for s in secciones
                if not any(k in _sin_tildes(s) for k in _ENCABEZADOS_ATS)]
    return errores


def _palabras(texto: str) -> list[str]:
    return re.findall(r"[^\W_]+", _sin_tildes(texto))


def _esta(clave: str, texto: str) -> bool:
    significativas = [p for p in _palabras(clave) if p not in _VACIAS]
    if not significativas:
        return False
    en_texto = _palabras(texto)
    return all(any(w[:_RAIZ] == p[:_RAIZ] for w in en_texto) for p in significativas)


def _campo(obj, nombre: str, defecto=None):
    return obj.get(nombre, defecto) if isinstance(obj, Mapping) else getattr(obj, nombre, defecto)


def _palabras_clave(oferta) -> list[str]:
    claves = list(_campo(oferta, "requisitos", None) or [])
    taxonomia = _campo(oferta, "taxonomia")
    if taxonomia is not None:
        claves += list(_campo(taxonomia, "stack", None) or [])
    return list(dict.fromkeys(c for c in claves if c and c.strip()))


def medir_ats(contenido: str, oferta, fuentes: str | Sequence[str]) -> dict:
    fuentes_texto = fuentes if isinstance(fuentes, str) else "\n".join(fuentes)
    claves = _palabras_clave(oferta)
    presentes = [c for c in claves if _esta(c, contenido)]
    ausentes = [c for c in claves if c not in presentes]
    return {
        "errores_formato": errores_ats(contenido),
        "cobertura": len(presentes) / len(claves) if claves else 1.0,
        "presentes": presentes,
        "ausentes_con_origen": [c for c in ausentes if _esta(c, fuentes_texto)],
        "ausentes_sin_origen": [c for c in ausentes if not _esta(c, fuentes_texto)],
    }
