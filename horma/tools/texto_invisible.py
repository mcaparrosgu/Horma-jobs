"""Quita de un CV el texto que no se ve (spec 012, RF-12.24): blanco sobre blanco, de tamaño 0 u oculto.

En un PDF no se miran los colores declarados sino el resultado: se dibuja la página y una letra cuyo
recuadro sale de un solo color no se ve (da igual si es por el color, el tamaño o el modo de dibujo). Así,
el texto blanco sobre una banda de color se conserva. En un DOCX se miran las marcas del texto."""
import threading

import pypdfium2

CERROJO = threading.Lock()  # PDFium no admite llamadas a la vez desde varios hilos
_ESCALA = 2
_MARGEN_PX = 2       # para que un guion o un punto dejen ver el fondo alrededor
_CONTRASTE = 16      # diferencia de gris (0-255) por debajo de la cual no se lee


def paginas_sin_invisible(contenido: bytes) -> dict[int, str]:
    """Texto visible de las páginas (desde 0) que tienen algo invisible. Las demás no salen."""
    limpias: dict[int, str] = {}
    with CERROJO:
        documento = pypdfium2.PdfDocument(contenido)
        try:
            for numero, pagina in enumerate(documento):
                imagen = pagina.render(scale=_ESCALA).to_pil().convert("L")
                alto = pagina.get_height()
                texto = pagina.get_textpage()
                letras, ocultas = [], False
                for i in range(texto.count_chars()):
                    letra = texto.get_text_range(i, 1)
                    if letra.strip() and not _se_ve(imagen, texto.get_charbox(i, loose=True), alto):
                        ocultas = True
                        continue
                    letras.append(letra)
                if ocultas:
                    limpias[numero] = "".join(letras).replace("\r\n", "\n")
        finally:
            documento.close()
    return limpias


def _se_ve(imagen, caja: tuple[float, float, float, float], alto: float) -> bool:
    izquierda, abajo, derecha, arriba = caja
    if derecha - izquierda < 0.5 or arriba - abajo < 0.5:  # tamaño 0
        return False
    x0, x1 = int(izquierda * _ESCALA) - _MARGEN_PX, int(derecha * _ESCALA) + _MARGEN_PX
    y0, y1 = int((alto - arriba) * _ESCALA) - _MARGEN_PX, int((alto - abajo) * _ESCALA) + _MARGEN_PX
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(imagen.width, x1), min(imagen.height, y1)
    if x1 <= x0 or y1 <= y0:  # fuera de la página
        return False
    minimo, maximo = imagen.crop((x0, y0, x1, y1)).getextrema()
    return maximo - minimo > _CONTRASTE


# --- DOCX ------------------------------------------------------------------------------------------
def _hereda(parrafo, run, propiedad: str):
    """El valor de la letra, o el de su estilo (de carácter o de párrafo) y los estilos base."""
    valor = getattr(run.font, propiedad)
    for estilo in (run.style, parrafo.style):
        while valor is None and estilo is not None:
            valor = getattr(estilo.font, propiedad)
            estilo = estilo.base_style
    return valor


def _con_fondo(elemento) -> bool:
    """¿Hay un sombreado que no sea blanco en este elemento o en lo que lo contiene (celda, tabla)?"""
    from docx.oxml.ns import qn

    while elemento is not None:
        for propiedades in ("w:rPr", "w:pPr", "w:tcPr", "w:tblPr"):
            nodo = elemento.find(qn(propiedades))
            if nodo is None:
                continue
            if nodo.find(qn("w:highlight")) is not None:
                return True
            sombra = nodo.find(qn("w:shd"))
            if sombra is not None and sombra.get(qn("w:fill"), "auto").upper() not in ("AUTO", "FFFFFF"):
                return True
        elemento = elemento.getparent()
    return False


def quitar_invisible_docx(documento) -> None:
    """Borra del documento en memoria las letras ocultas, de tamaño 0 o blancas sin fondo."""
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph
    from docx.text.run import Run

    for p in list(documento.element.body.iter(qn("w:p"))):
        parrafo = Paragraph(p, documento._body)
        for r in list(p.iter(qn("w:r"))):
            run = Run(r, parrafo)
            tamano = _hereda(parrafo, run, "size")
            color = run.font.color.rgb if run.font.color is not None else None
            oculto = bool(_hereda(parrafo, run, "hidden")) or (tamano is not None and tamano.pt < 1)
            if not oculto and color is not None and str(color) == "FFFFFF":
                oculto = not _con_fondo(r)
            if oculto:
                r.getparent().remove(r)
