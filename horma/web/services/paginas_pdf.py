"""Páginas de un PDF como imagen, para verlo en el móvil, donde el navegador no pinta un PDF (RF-2.1c)."""
import io
import threading
from pathlib import Path

import pypdfium2

MAX_PAGINAS = 20
ANCHO_PX = 1000   # nítida a 390 px en pantallas densas sin pesar demasiado
_CERROJO = threading.Lock()   # PDFium no admite llamadas a la vez desde varios hilos


def contar(ruta: Path) -> int:
    with _CERROJO:
        documento = pypdfium2.PdfDocument(ruta)
        try:
            return min(len(documento), MAX_PAGINAS)
        finally:
            documento.close()


def png(ruta: Path, numero: int) -> bytes | None:
    """La página `numero` (desde 1), o None si no existe."""
    with _CERROJO:
        documento = pypdfium2.PdfDocument(ruta)
        try:
            if not 1 <= numero <= min(len(documento), MAX_PAGINAS):
                return None
            pagina = documento[numero - 1]
            imagen = pagina.render(scale=ANCHO_PX / pagina.get_width()).to_pil()
        finally:
            documento.close()
    salida = io.BytesIO()
    imagen.save(salida, "PNG", optimize=True)
    return salida.getvalue()
