"""Convierte un Markdown sencillo en PDF (RF-3.8b). Código puro: devuelve bytes, no toca el disco
salvo para leer la fuente incluida.

Admite encabezados (#, ##, ###), listas con viñeta, párrafos y negrita inline (`**x**`, que se muestra
como texto normal); sin imágenes ni tablas. Usa `fpdf2` (Python puro, sin dependencias del sistema) y
la fuente libre DejaVu Sans, incluida en el paquete, porque las fuentes básicas del PDF no cubren
todo Unicode (acentos, «ñ», «¿»)."""
import re
from pathlib import Path

from fpdf import FPDF

_FUENTES = Path(__file__).resolve().parent.parent / "assets" / "fuentes"
_MARCAS = re.compile(r"\*\*|__|`")
_ENCABEZADO = re.compile(r"^\s*(#{1,6})\s+(.*)$")
_VINETA = re.compile(r"^\s*[-*+•]\s+(.*)$")
_TAMANOS = {1: 18, 2: 14, 3: 12}


def _limpio(texto: str) -> str:
    return _MARCAS.sub("", texto).strip()


def generar_pdf(markdown: str, titulo: str) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_title(titulo)
    pdf.set_margins(20, 18, 20)
    pdf.set_auto_page_break(True, margin=18)
    pdf.add_font("DejaVu", "", str(_FUENTES / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(_FUENTES / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    ancho = pdf.w - pdf.l_margin - pdf.r_margin

    def escribir(texto: str, estilo: str, tamano: int, sangria: float = 0, antes: float = 0,
                 despues: float = 1.5) -> None:
        pdf.ln(antes)
        pdf.set_font("DejaVu", estilo, tamano)
        pdf.set_x(pdf.l_margin + sangria)
        pdf.multi_cell(ancho - sangria, tamano * 0.5, texto, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(despues)

    for linea in markdown.splitlines():
        if not linea.strip():
            continue
        if m := _ENCABEZADO.match(linea):
            nivel = len(m.group(1))
            escribir(_limpio(m.group(2)), "B", _TAMANOS.get(nivel, 11),
                     antes=3 if nivel > 1 else 0, despues=1.5)
        elif m := _VINETA.match(linea):
            escribir("•  " + _limpio(m.group(1)), "", 10.5, sangria=4, despues=0.8)
        else:
            escribir(_limpio(linea), "", 10.5)
    return bytes(pdf.output())
