"""Convierte un Markdown sencillo en PDF (RF-3.8b, RF-10.4d). Código puro: devuelve bytes, no toca el disco
salvo para leer las fuentes incluidas.

Dos diseños sobrios, con la tipografía de la marca (Familjen Grotesk y DM Mono, licencia OFL) y todo en
texto real, sin tablas ni imágenes (RF-10.4b):
- `tipo="cv"`: nombre grande, titular debajo en gris, secciones en mayúsculas con una línea fina,
  «puesto · empresa» en negrita con las fechas a la derecha, habilidades e idiomas en una línea.
- `tipo="carta"`: solo párrafos, sin negritas ni secciones.

Sin páginas sueltas (RF-10.14o): una sección no empieza al pie de una página ni deja una línea sola en la
siguiente; si la última página sale con menos de tres líneas, se vuelve a componer algo más apretado.

Usa `fpdf2` (Python puro). Si faltan las fuentes de la marca, cae a DejaVu Sans, que cubre Unicode."""
import io
import re
from pathlib import Path

from fpdf import FPDF
from pypdf import PdfReader

_FUENTES = Path(__file__).resolve().parent.parent / "assets" / "fuentes"
_MARCAS = re.compile(r"\*\*|__|`")
_ENCABEZADO = re.compile(r"^\s*(#{1,6})\s+(.*)$")
_VINETA = re.compile(r"^\s*[-*+•]\s+(.*)$")
_NEGRITA_ENTERA = re.compile(r"^\s*\*\*(.+)\*\*\s*$")
_MESES = re.compile(r"\b(ene|feb|mar|abr|may|jun|jul|ago|sep|sept|oct|nov|dic|"
                    r"enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|actualidad|presente|actual|hoy)\b\.?",
                    re.IGNORECASE)
_EN_UNA_LINEA = {"habilidades", "idiomas"}

_TINTA = (20, 20, 20)
_GRIS = (110, 110, 110)
_LINEA = (190, 190, 190)


def _limpio(texto: str) -> str:
    return _MARCAS.sub("", texto).strip()


def _es_fecha(parte: str) -> bool:
    """«2018-2020», «ene 2019 - actualidad», «2021»: solo años, meses y separadores."""
    resto = _MESES.sub("", parte)
    return bool(re.search(r"\b(19|20)\d{2}\b", resto)) and not re.search(r"[A-Za-zÁ-úñÑ]{2,}", resto) \
        and len(parte) <= 32


def _fuentes(pdf: FPDF) -> tuple[str, str]:
    """Registra las fuentes y devuelve (familia del texto, familia de las etiquetas)."""
    marca = [_FUENTES / n for n in ("FamiljenGrotesk-Regular.ttf", "FamiljenGrotesk-Bold.ttf",
                                    "DMMono-Regular.ttf", "DMMono-Medium.ttf")]
    if all(p.exists() for p in marca):
        pdf.add_font("Texto", "", str(marca[0]))
        pdf.add_font("Texto", "B", str(marca[1]))
        pdf.add_font("Etiqueta", "", str(marca[2]))
        pdf.add_font("Etiqueta", "B", str(marca[3]))   # «B» = el peso medio de DM Mono
        return "Texto", "Etiqueta"
    pdf.add_font("DejaVu", "", str(_FUENTES / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(_FUENTES / "DejaVuSans-Bold.ttf"))
    return "DejaVu", "DejaVu"


_ESCALAS = (1.0, 0.97, 0.94, 0.91, 0.88)   # tamaños y espacios, de lo normal a lo más apretado
_MIN_LINEAS_ULTIMA = 3


def _lineas_de_la_ultima(contenido: bytes) -> tuple[int, int]:
    """(páginas, líneas de texto de la última)."""
    paginas = PdfReader(io.BytesIO(contenido)).pages
    texto = paginas[-1].extract_text() or ""
    return len(paginas), len([x for x in texto.splitlines() if x.strip()])


def generar_pdf(markdown: str, titulo: str, tipo: str = "cv") -> bytes:
    """Compone el PDF; si deja una última página con menos de tres líneas, lo recompone más apretado."""
    resultado = b""
    for escala in _ESCALAS:
        resultado = _componer(markdown, titulo, tipo, escala)
        paginas, lineas = _lineas_de_la_ultima(resultado)
        if paginas == 1 or lineas >= _MIN_LINEAS_ULTIMA:
            break
    return resultado


def _componer(markdown: str, titulo: str, tipo: str, k: float) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_title(titulo)
    pdf.set_margins(22, 20, 22)
    pdf.set_auto_page_break(True, margin=20)
    texto, etiqueta = _fuentes(pdf)
    pdf.add_page()
    ancho = pdf.w - pdf.l_margin - pdf.r_margin

    def escribir(contenido: str, familia: str, estilo: str, tamano: float, color=_TINTA,
                 interlineado: float = 1.45, sangria: float = 0, antes: float = 0, despues: float = 0,
                 alinear: str = "L") -> None:
        tamano, antes, despues = tamano * k, antes * k, despues * k
        pdf.set_font(familia, estilo, tamano)
        alto = tamano * 0.3528 * interlineado
        lineas = len(pdf.multi_cell(ancho - sangria, alto, contenido, align=alinear, dry_run=True,
                                    output="LINES"))
        queda = int((pdf.page_break_trigger - pdf.get_y() - antes) // alto)
        if lineas > 1 and queda < lineas and (queda < 2 or lineas - queda < 2):
            pdf.add_page()   # ni una línea suelta al pie ni la última sola en la página siguiente
            antes = 0
        pdf.ln(antes)
        pdf.set_text_color(*color)
        pdf.set_x(pdf.l_margin + sangria)
        pdf.multi_cell(ancho - sangria, alto, contenido, align=alinear, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(despues)

    def reservar(alto_mm: float) -> bool:
        """Si no caben `alto_mm` en la página, abre otra; así un título nunca queda solo al pie."""
        if pdf.page_break_trigger - pdf.get_y() < alto_mm * k:
            pdf.add_page()
            return True
        return False

    if tipo == "carta":
        _carta(markdown, texto, escribir)
    else:
        _cv(markdown, pdf, ancho, texto, etiqueta, escribir, reservar, k)
    return bytes(pdf.output())


def _carta(markdown: str, texto: str, escribir) -> None:
    """Párrafos: cada línea se respeta (saludo, despedida) y una línea en blanco abre un espacio mayor."""
    previa_en_blanco = False
    for linea in markdown.splitlines():
        if not linea.strip():
            previa_en_blanco = True
            continue
        m = _ENCABEZADO.match(linea) or _VINETA.match(linea)
        escribir(_limpio(m.group(m.lastindex) if m else linea), texto, "", 10.5, interlineado=1.6,
                 antes=3.5 if previa_en_blanco else 0)
        previa_en_blanco = False


def _cv(markdown: str, pdf: FPDF, ancho: float, texto: str, etiqueta: str, escribir, reservar,
        k: float) -> None:
    seccion = ""
    pendiente: list[str] = []   # habilidades e idiomas: todo en una línea
    nombre_visto = False
    titular_visto = False

    def volcar() -> None:
        if pendiente:
            escribir(" · ".join(pendiente), texto, "", 10, color=_TINTA, despues=1)
            pendiente.clear()

    for linea in markdown.splitlines():
        if not linea.strip():
            continue
        if m := _ENCABEZADO.match(linea):
            volcar()
            contenido = _limpio(m.group(2))
            if len(m.group(1)) == 1 and not nombre_visto:
                nombre_visto = True
                escribir(contenido, texto, "B", 24, interlineado=1.2, despues=1)
                continue
            seccion = contenido.casefold()
            if not reservar(32):   # el título y al menos dos líneas de lo que sigue
                pdf.ln(5 * k)
            escribir(contenido.upper(), etiqueta, "B", 8.5, color=_TINTA, interlineado=1.2, despues=0.6)
            y = pdf.get_y()
            pdf.set_draw_color(*_LINEA)
            pdf.set_line_width(0.2)
            pdf.line(pdf.l_margin, y, pdf.l_margin + ancho, y)
            pdf.ln(2.2 * k)
            continue
        if seccion in _EN_UNA_LINEA:
            m = _VINETA.match(linea)
            trozos = re.split(r"\s·\s|,\s", _limpio(m.group(1) if m else linea))
            pendiente.extend(p for p in (x.strip() for x in trozos) if p)
            continue
        if nombre_visto and not seccion and not titular_visto:   # el titular, bajo el nombre y en gris
            titular_visto = True
            escribir(_limpio(linea), texto, "", 12, color=_GRIS, despues=1)
            continue
        if m := _VINETA.match(linea):
            escribir("–  " + _limpio(m.group(1)), texto, "", 10, sangria=3, despues=0.6)
            continue
        entera = _NEGRITA_ENTERA.match(linea)
        partes = [p.strip() for p in _limpio(linea).split(" · ")]
        if entera or len(partes) > 1:   # «puesto · empresa · fechas»: negrita y fechas a la derecha
            fecha = partes.pop() if len(partes) > 1 and _es_fecha(partes[-1]) else ""
            reservar(22)   # la cabecera de un puesto no se queda sola sin sus primeras viñetas
            _cabecera(pdf, ancho, " · ".join(partes), fecha, texto, etiqueta, k)
        else:
            escribir(_limpio(linea), texto, "", 10, color=_TINTA, despues=1.2)
    volcar()


def _cabecera(pdf: FPDF, ancho: float, izquierda: str, fecha: str, texto: str, etiqueta: str,
              k: float = 1.0) -> None:
    pdf.ln(1.8 * k)
    y0 = pdf.get_y()
    pdf.set_font(etiqueta, "", 8.5 * k)
    ancho_fecha = pdf.get_string_width(fecha) + 1 if fecha else 0
    pdf.set_font(texto, "B", 10.5 * k)
    pdf.set_text_color(*_TINTA)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(ancho - ancho_fecha - 3, 5 * k, izquierda, new_x="LMARGIN", new_y="NEXT")
    y1 = pdf.get_y()
    if fecha:
        pdf.set_font(etiqueta, "", 8.5 * k)
        pdf.set_text_color(*_GRIS)
        pdf.set_xy(pdf.l_margin + ancho - ancho_fecha, y0)
        pdf.cell(ancho_fecha, 5 * k, fecha, align="R")
        pdf.set_y(y1)
    pdf.ln(0.6)
