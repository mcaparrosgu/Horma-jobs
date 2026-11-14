"""Comprueba que un CV base no contiene nada que el CV maestro no tenga (RF-2.9, RT-08).

Código puro. Devuelve la lista de errores en español (vacía si todo va bien); el flujo se la pasa
al generador para que corrija en el intento siguiente. Qué se comprueba:

1. Cada frase del CV tiene su entrada en la traza (títulos de sección, como «## Experiencia», no).
2. El fragmento de cada entrada está de verdad en el CV maestro.
3. Ninguna fecha del CV base falta en el maestro.
4. Cada frase no añade nada a su fragmento:
   - todas las cifras y fechas de la frase están en el fragmento;
   - los nombres propios (palabras con mayúscula dentro de la frase) están en el fragmento;
   - en las líneas de cabecera (puesto · empresa · fechas, titulación · centro…), que son las que
     llevan cargos, empresas y titulaciones, TODAS las palabras están en el fragmento. Una línea de
     cabecera es la que lleva un separador («·», «|», «—», « - ») o tiene 4 palabras o menos.

La coherencia semántica fina (p. ej. «lideré» frente a «participé») la juzga el juez-cv (fase 3);
aquí solo lo que se puede decidir con reglas."""
import re
import unicodedata
from collections.abc import Mapping, Sequence

_SEPARADOR = re.compile(r"[·|—–]| - ")
_TITULO = re.compile(r"^\s*#{1,6}\s")
_VINETA = re.compile(r"^\s*(?:[-*+•>]+|\d+[.)])\s+")
_PALABRA = re.compile(r"[^\W_]+(?:[.,][^\W_]+)*", re.UNICODE)
_FECHA = re.compile(r"\b(?:\d{1,2}/)?(?:19|20)\d{2}\b")
_CORTAS = 3  # las palabras de menos de 4 letras (de, en, la, un…) no cuentan en las cabeceras


def _limpiar(texto: str) -> str:
    t = unicodedata.normalize("NFKC", texto).replace("*", "").replace("`", "")
    t = re.sub(r"(?<!\w)_|_(?!\w)", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _clave(texto: str) -> str:
    return _limpiar(texto).casefold().strip(" .,;:!?¡¿")


def _palabras(texto: str) -> list[str]:
    return _PALABRA.findall(_limpiar(texto))


def _campo(item, nombre: str) -> str:
    return str(item[nombre] if isinstance(item, Mapping) else getattr(item, nombre))


def frases(contenido: str) -> list[str]:
    """Líneas del CV que necesitan traza: todas menos títulos de sección y separadores."""
    salida = []
    for linea in contenido.splitlines():
        if not linea.strip() or _TITULO.match(linea):
            continue
        texto = _VINETA.sub("", linea).strip()
        if re.search(r"\w", texto):
            salida.append(texto)
    return salida


def _es_cabecera(frase: str) -> bool:
    return bool(_SEPARADOR.search(frase)) or len(_palabras(frase)) <= 4


def _terminos_a_comprobar(frase: str) -> list[str]:
    """Palabras de la frase que deben estar en su fragmento (en minúsculas)."""
    palabras = _palabras(frase)
    if _es_cabecera(frase):
        return [p.casefold() for p in palabras if len(p) > _CORTAS or p[0].isdigit()]
    terminos = []
    for i, p in enumerate(palabras):
        es_cifra = any(c.isdigit() for c in p)
        es_propio = i > 0 and p[0].isupper() and len(p) > 1
        if es_cifra or es_propio:
            terminos.append(p.casefold())
    return terminos


def verificar_trazabilidad(contenido: str, traza: Sequence, maestro: str) -> list[str]:
    errores: list[str] = []
    maestro_clave = _clave(maestro)
    por_frase = {_clave(_campo(t, "frase")): _campo(t, "fragmento") for t in traza}

    # 3. fechas: ninguna puede faltar en el maestro
    fechas_maestro = set(_FECHA.findall(_limpiar(maestro)))
    for fecha in dict.fromkeys(_FECHA.findall(_limpiar(contenido))):
        if fecha not in fechas_maestro:
            errores.append(f"Fecha que no está en el CV maestro: {fecha}")

    for frase in frases(contenido):
        fragmento = por_frase.get(_clave(frase))
        # 1. toda frase tiene traza
        if fragmento is None:
            errores.append(f"Frase sin origen en la traza: «{frase}»")
            continue
        # 2. el fragmento está en el maestro
        if _clave(fragmento) not in maestro_clave:
            errores.append(f"El fragmento no está en el CV maestro: «{fragmento}» (frase «{frase}»)")
            continue
        # 4. la frase no añade datos a su fragmento
        en_fragmento = {p.casefold() for p in _palabras(fragmento)}
        for termino in _terminos_a_comprobar(frase):
            if termino not in en_fragmento:
                errores.append(f"«{termino}» no aparece en el fragmento de origen de la frase «{frase}»")
    return errores
