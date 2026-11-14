"""Convierte un CV (PDF, DOCX o Markdown) a texto (RF-2.1).

Código puro: recibe bytes y devuelve texto; no toca disco. Comprueba los bytes del archivo y no se
fía de la extensión: un ejecutable renombrado a .pdf se rechaza."""
import io
import zipfile

TIPOS = ("pdf", "docx", "md")


class ArchivoNoValido(ValueError):
    """El archivo no es del tipo que dice ser, está vacío o no tiene texto."""


def _pdf(contenido: bytes) -> str:
    if not contenido.lstrip()[:5] == b"%PDF-":
        raise ArchivoNoValido("el archivo no es un PDF válido")
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        lector = PdfReader(io.BytesIO(contenido))
        return "\n".join((pagina.extract_text() or "") for pagina in lector.pages)
    except (PyPdfError, ValueError, KeyError, OSError) as e:
        raise ArchivoNoValido("no se ha podido leer el PDF") from e


def _docx(contenido: bytes) -> str:
    if contenido[:4] != b"PK\x03\x04":
        raise ArchivoNoValido("el archivo no es un DOCX válido")
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            if "word/document.xml" not in z.namelist():
                raise ArchivoNoValido("el archivo no es un DOCX válido")
        from docx import Document

        d = Document(io.BytesIO(contenido))
        partes = [p.text for p in d.paragraphs]
        for tabla in d.tables:
            for fila in tabla.rows:
                partes.extend(c.text for c in fila.cells)
        return "\n".join(partes)
    except ArchivoNoValido:
        raise
    except Exception as e:  # docx lanza excepciones de varios tipos con archivos corruptos
        raise ArchivoNoValido("no se ha podido leer el DOCX") from e


def _markdown(contenido: bytes) -> str:
    if b"\x00" in contenido:
        raise ArchivoNoValido("el archivo no es texto")
    try:
        return contenido.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ArchivoNoValido("el archivo no está en UTF-8") from e


def convertir_cv(contenido: bytes, tipo: str) -> str:
    """Devuelve el texto del CV. `tipo`: «pdf», «docx» o «md». Lanza `ArchivoNoValido`."""
    if tipo not in TIPOS:
        raise ArchivoNoValido(f"tipo no admitido: {tipo}")
    if not contenido:
        raise ArchivoNoValido("el archivo está vacío")
    texto = {"pdf": _pdf, "docx": _docx, "md": _markdown}[tipo](contenido).strip()
    if not texto:
        raise ArchivoNoValido("el archivo no tiene texto (¿es un escaneo?)")
    return texto
