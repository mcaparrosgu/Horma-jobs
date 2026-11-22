"""Comprobaciones de código sobre un CV generado (RF-5.4): longitud, secciones y fechas.

Código puro. Devuelve los errores en llano (vacío si no hay ninguno):
- entre `CV_PALABRAS_MIN` y `CV_PALABRAS_MAX` palabras (una o dos páginas). Si se pasa el CV maestro, el
  mínimo baja a `FRACCION_MAESTRO` (60 %) de sus palabras cuando el maestro es corto: un CV no puede
  tener más contenido que el perfil del que sale, y una usuaria con poca experiencia no queda bloqueada;
- al menos un encabezado `## Experiencia` o `## Formación`;
- periodos `AAAA`, `AAAA-MM` o `MM-AAAA` con fin ≥ inicio (el fin puede ser «actual», «presente» u «hoy»);
  los meses van de 01 a 12."""
import re
import unicodedata

CV_PALABRAS_MIN = 250
CV_PALABRAS_MAX = 1000
FRACCION_MAESTRO = 0.6

_FECHA = r"(?:\d{2}-(?:19|20)\d{2}|(?:19|20)\d{2}(?:-\d{2})?)"
_PERIODO = re.compile(rf"(?<![\d-])({_FECHA})\s*[-–—]\s*({_FECHA}|actual|presente|hoy)(?![\d-])",
                      re.IGNORECASE)
_SECCION = re.compile(r"^#{1,6}\s*(experiencia|formacion)\b", re.MULTILINE)


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)).lower()


def _clave(fecha: str) -> tuple[int, int]:
    a, _, b = fecha.partition("-")
    if len(a) == 2:   # MM-AAAA
        return int(b), int(a)
    return int(a), int(b or 1)


def _mes_valido(fecha: str) -> bool:
    a, _, b = fecha.partition("-")
    mes = a if len(a) == 2 else b
    return not mes or 1 <= int(mes) <= 12


def palabras_minimas(maestro: str | None = None) -> int:
    """Mínimo de palabras de un CV: `CV_PALABRAS_MIN`, o el 60 % del maestro si este es más corto."""
    if maestro is None:
        return CV_PALABRAS_MIN
    return min(CV_PALABRAS_MIN, int(len(maestro.split()) * FRACCION_MAESTRO))


def validar_cv(texto: str, maestro: str | None = None) -> list[str]:
    errores: list[str] = []
    palabras = len(texto.split())
    minimo = palabras_minimas(maestro)
    if palabras > CV_PALABRAS_MAX:
        maximo = f"{CV_PALABRAS_MAX:,}".replace(",", ".")
        errores.append(f"El CV es demasiado largo: {palabras} palabras (máximo {maximo}).")
    elif palabras < minimo:
        errores.append(f"El CV es demasiado corto: {palabras} palabras (mínimo {minimo}).")
    if not _SECCION.search(_sin_acentos(texto)):
        errores.append("Al CV le falta la sección Experiencia o la sección Formación.")
    for inicio, fin in dict.fromkeys(_PERIODO.findall(texto)):
        for f in (inicio, fin):
            if f[0].isdigit() and not _mes_valido(f):
                errores.append(f"Fecha con un mes que no existe: {f}.")
        if fin[0].isdigit() and _mes_valido(inicio) and _mes_valido(fin) and _clave(fin) < _clave(inicio):
            errores.append(f"El periodo {inicio}-{fin} acaba antes de empezar (fin anterior al inicio).")
    return errores
