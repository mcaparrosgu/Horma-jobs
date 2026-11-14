"""Fase 2 · T02: convertir_cv (PDF, DOCX y Markdown a texto; rechazo por los bytes, no por la extensión)."""
import io

import pytest
from docx import Document

from horma.tools.convertir_cv import ArchivoNoValido, convertir_cv


def _pdf(texto: str) -> bytes:
    """PDF mínimo válido de una página con `texto` (solo ASCII), para no depender de ficheros."""
    flujo = f"BT /F1 12 Tf 72 720 Td ({texto}) Tj ET".encode("latin-1")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(flujo)).encode() + b" >>\nstream\n" + flujo + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    salida = bytearray(b"%PDF-1.4\n")
    posiciones = []
    for i, cuerpo in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += f"{i} 0 obj\n".encode() + cuerpo + b"\nendobj\n"
    inicio_xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n".encode() + b"0000000000 65535 f \n"
    for p in posiciones:
        salida += f"{p:010d} 00000 n \n".encode()
    salida += (f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n"
               .encode())
    return bytes(salida)


def _docx(*parrafos: str) -> bytes:
    d = Document()
    for p in parrafos:
        d.add_paragraph(p)
    b = io.BytesIO()
    d.save(b)
    return b.getvalue()


def test_markdown_sale_como_texto():
    md = "# Ana Inventada\n\nCamarera en Bar Sol (2020-2022)\n".encode()
    assert "Camarera en Bar Sol" in convertir_cv(md, "md")


def test_markdown_acepta_utf8_con_tildes():
    assert "Máster" in convertir_cv("Máster en Marketing".encode("utf-8"), "md")


def test_pdf_sale_como_texto():
    assert "Camarera en Bar Sol" in convertir_cv(_pdf("Camarera en Bar Sol"), "pdf")


def test_docx_sale_como_texto_con_parrafos():
    t = convertir_cv(_docx("Ana Inventada", "Camarera en Bar Sol"), "docx")
    assert "Ana Inventada" in t and "Camarera en Bar Sol" in t
    assert t.index("Ana Inventada") < t.index("Camarera en Bar Sol")


def test_un_pdf_falso_se_rechaza_por_sus_bytes():
    with pytest.raises(ArchivoNoValido):
        convertir_cv(b"esto no es un pdf, solo lo parece", "pdf")


def test_un_docx_falso_se_rechaza():
    with pytest.raises(ArchivoNoValido):
        convertir_cv(b"texto plano", "docx")
    with pytest.raises(ArchivoNoValido):  # un zip que no es un docx
        import zipfile

        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("hola.txt", "hola")
        convertir_cv(b.getvalue(), "docx")


def test_un_ejecutable_con_extension_md_se_rechaza():
    with pytest.raises(ArchivoNoValido):
        convertir_cv(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff", "md")
    with pytest.raises(ArchivoNoValido):  # NUL: no es texto
        convertir_cv(b"hola\x00mundo", "md")


def test_archivo_vacio_o_sin_texto_se_rechaza():
    with pytest.raises(ArchivoNoValido):
        convertir_cv(b"", "md")
    with pytest.raises(ArchivoNoValido):
        convertir_cv(b"   \n  ", "md")
    with pytest.raises(ArchivoNoValido):  # PDF escaneado: sin capa de texto
        convertir_cv(_pdf(""), "pdf")


def test_tipo_no_admitido():
    with pytest.raises(ArchivoNoValido):
        convertir_cv(b"hola", "exe")
