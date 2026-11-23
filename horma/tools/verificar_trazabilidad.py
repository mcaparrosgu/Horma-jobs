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

La coherencia semántica fina (p. ej. «lideré» frente a «participé») la juzga el juez-candidatura (fase 3);
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


def _raiz(palabra: str) -> str:
    """Quita la marca de género/número final, para que camarero/camarera cuenten como la misma palabra
    (el CV base escribe todos los puestos en el género de la candidata)."""
    p = palabra.casefold()
    for fin in ("os", "as", "o", "a", "e"):
        if p.endswith(fin) and len(p) > len(fin) + 3:
            return p[: -len(fin)]
    return p


def _terminos_a_comprobar(frase: str, cabeceras: bool = True) -> list[str]:
    """Palabras de la frase que deben estar en su fragmento (en minúsculas)."""
    palabras = _palabras(frase)
    if cabeceras and _es_cabecera(frase):
        return [p.casefold() for p in palabras if len(p) > _CORTAS or p[0].isdigit()]
    terminos = []
    for i, p in enumerate(palabras):
        es_cifra = any(c.isdigit() for c in p)
        es_propio = i > 0 and p[0].isupper() and len(p) > 1
        if es_cifra or es_propio:
            terminos.append(p.casefold())
    return terminos


_IDIOMAS = {"es": "español|castellano", "en": "inglés|english", "fr": "francés|french",
            "de": "alemán|german", "it": "italiano", "pt": "portugués", "ca": "catalán|valenciano|català",
            "eu": "euskera|vasco", "gl": "gallego", "ar": "árabe", "zh": "chino", "ru": "ruso",
            "ro": "rumano", "nl": "neerlandés|holandés", "pl": "polaco", "ja": "japonés"}


def verificar_idiomas(contenido: str, perfil) -> list[str]:
    """Todo idioma del perfil debe salir en el CV base: omitirlo deja a la candidata fuera de ofertas."""
    texto = _limpiar(contenido).casefold()
    errores = []
    for i in perfil.idiomas:
        nombres = _IDIOMAS.get(i.idioma)
        if nombres and not re.search(nombres, texto):
            errores.append(f"Falta el idioma «{i.idioma}» del perfil en el CV base")
    return errores


FORMULAS_ANTIGUAS: tuple[str, ...] = (   # ya no se piden al modelo, pero valen en cartas guardadas (T66)
    "Estimado equipo de selección,", "Estimados señores,", "Hola equipo,", "Buenos días,",
)
FORMULAS_CORTESIA: tuple[str, ...] = (
    "Hola, equipo:", "Estimado equipo de selección:", "Estimados señores:", "Buenos días:",
    *FORMULAS_ANTIGUAS,
    "Un saludo", "Saludos cordiales", "Cordialmente", "Atentamente", "Muchas gracias por su tiempo",
    "Gracias por su tiempo", "Gracias por tu tiempo",
)  # lista cerrada de saludos y despedidas de la carta (RF-3.6): no piden traza


_FIN_DE_FRASE = re.compile(r"(?<=[.!?])\s+")


def _unidades(contenido: str, por_frase: bool) -> list[str]:
    """Lo que necesita traza: las líneas del documento o, en la carta, cada frase de cada párrafo."""
    lineas = frases(contenido)
    if not por_frase:
        return lineas
    return [f for linea in lineas for f in _FIN_DE_FRASE.split(linea) if f.strip()]


def verificar_trazabilidad(contenido: str, traza: Sequence, fuentes: str | Sequence[str],
                           formulas_cortesia: Sequence[str] = (), por_frase: bool = False) -> list[str]:
    """`fuentes`: un texto (el CV maestro, como en la fase 2) o una lista de textos (CV maestro, CV base
    editado y, solo para la carta, la oferta). Un fragmento vale si está en alguna; una fecha, si está
    en alguna. `formulas_cortesia`: líneas que quedan exentas de traza (saludo y despedida de la carta).
    `por_frase`: la traza es por frase y no por línea (la carta escribe párrafos de varias frases)."""
    unica = isinstance(fuentes, str)
    lista = [fuentes] if unica else list(fuentes)
    nombre = "el CV maestro" if unica else "ninguna de las fuentes"
    errores: list[str] = []
    claves_fuentes = [_clave(f) for f in lista]
    traza_por_frase = {_clave(_campo(t, "frase")): _campo(t, "fragmento") for t in traza}
    exentas = {_clave(f) for f in formulas_cortesia}

    # 3. fechas: ninguna puede faltar en las fuentes
    fechas_fuentes = {f for fuente in lista for f in _FECHA.findall(_limpiar(fuente))}
    for fecha in dict.fromkeys(_FECHA.findall(_limpiar(contenido))):
        if fecha not in fechas_fuentes:
            errores.append(f"Fecha que no está en {nombre}: {fecha}")

    for frase in _unidades(contenido, por_frase):
        if _clave(frase) in exentas:
            continue
        fragmento = traza_por_frase.get(_clave(frase))
        # 1. toda frase tiene traza
        if fragmento is None:
            errores.append(f"Frase sin origen en la traza: «{frase}»")
            continue
        # 2. el fragmento está en alguna fuente
        if not any(_clave(fragmento) in c for c in claves_fuentes):
            errores.append(f"El fragmento no está en {nombre}: «{fragmento}» (frase «{frase}»)")
            continue
        # 4. la frase no añade datos a su fragmento. En la carta, una frase puede juntar datos de varias
        # líneas del CV: vale cualquier palabra que esté en alguna fuente (lo inventado sigue sin valer).
        en_fragmento = {p.casefold() for p in _palabras(fragmento)}
        if por_frase:
            en_fragmento |= {p.casefold() for f in lista for p in _palabras(f)}
        raices = {_raiz(p) for p in en_fragmento}
        for termino in _terminos_a_comprobar(frase, cabeceras=not por_frase):
            if termino not in en_fragmento and _raiz(termino) not in raices:
                errores.append(f"«{termino}» no aparece en el fragmento de origen de la frase «{frase}»")
    return errores
