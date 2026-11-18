"""Comprobaciones de código sobre un CV generado (RF-5.4): longitud, secciones y fechas.

Código puro. Devuelve los errores en llano (vacío si no hay ninguno):
- entre `CV_PALABRAS_MIN` y `CV_PALABRAS_MAX` palabras (una o dos páginas);
- al menos un encabezado `## Experiencia` o `## Formación`;
- periodos `AAAA` o `AAAA-MM` con fin ≥ inicio (el fin puede ser «actual», «presente» u «hoy»);
  los meses van de 01 a 12."""
import re
import unicodedata

CV_PALABRAS_MIN = 250
CV_PALABRAS_MAX = 1000

_FECHA = r"(?:19|20)\d{2}(?:-\d{2})?"
_PERIODO = re.compile(rf"(?<![\d-])({_FECHA})\s*[-–—]\s*({_FECHA}|actual|presente|hoy)(?![\d-])",
                      re.IGNORECASE)
_SECCION = re.compile(r"^#{1,6}\s*(experiencia|formacion)\b", re.MULTILINE)


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)).lower()


def _clave(fecha: str) -> tuple[int, int]:
    anio, _, mes = fecha.partition("-")
    return int(anio), int(mes or 1)


def _mes_valido(fecha: str) -> bool:
    mes = fecha.partition("-")[2]
    return not mes or 1 <= int(mes) <= 12


def validar_cv(texto: str) -> list[str]:
    errores: list[str] = []
    palabras = len(texto.split())
    if palabras > CV_PALABRAS_MAX:
        maximo = f"{CV_PALABRAS_MAX:,}".replace(",", ".")
        errores.append(f"El CV es demasiado largo: {palabras} palabras (máximo {maximo}).")
    elif palabras < CV_PALABRAS_MIN:
        errores.append(f"El CV es demasiado corto: {palabras} palabras (mínimo {CV_PALABRAS_MIN}).")
    if not _SECCION.search(_sin_acentos(texto)):
        errores.append("Al CV le falta la sección Experiencia o la sección Formación.")
    for inicio, fin in dict.fromkeys(_PERIODO.findall(texto)):
        for f in (inicio, fin):
            if f[0].isdigit() and not _mes_valido(f):
                errores.append(f"Fecha con un mes que no existe: {f}.")
        if fin[0].isdigit() and _mes_valido(inicio) and _mes_valido(fin) and _clave(fin) < _clave(inicio):
            errores.append(f"El periodo {inicio}-{fin} acaba antes de empezar (fin anterior al inicio).")
    return errores
