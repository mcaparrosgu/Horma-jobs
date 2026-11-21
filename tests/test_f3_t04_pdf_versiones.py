"""Fase 3 · T04: generar_pdf y comparar_versiones (RF-3.8b, RF-3.8d)."""
import io

from pypdf import PdfReader

from horma.tools.comparar_versiones import comparar_versiones
from horma.tools.generar_pdf import generar_pdf

MD = """# Ana Inventada

## Educación
- FP Hostelería · IES Mar · 2018-2020
- Curso de **atención** al cliente

## Experiencia
Camarera en Bar Sol. Atendí a clientes en sala y gestioné pedidos con mucho cuidado durante
varios años seguidos, siempre con buena disposición.

Señora Directora:
Le escribo para presentarme.
"""


def _texto(pdf: bytes) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)


def test_el_pdf_es_valido_y_conserva_el_texto_con_acentos():
    pdf = generar_pdf(MD, "CV de Ana")
    assert pdf.startswith(b"%PDF")
    texto = " ".join(_texto(pdf).split())
    for esperado in ("Ana Inventada", "EDUCACIÓN", "FP Hostelería", "Señora Directora", "pedidos"):
        assert esperado in texto, esperado
    assert "**" not in texto and "##" not in texto  # el Markdown no se cuela


def test_el_titulo_va_en_los_metadatos():
    meta = PdfReader(io.BytesIO(generar_pdf(MD, "CV de Ana"))).metadata
    assert meta.title == "CV de Ana"


def test_un_texto_largo_ocupa_varias_paginas_y_uno_vacio_no_falla():
    largo = "\n".join(f"- Línea número {i} con ñ y tildes áéíóú" for i in range(200))
    assert len(PdfReader(io.BytesIO(generar_pdf(largo, "x"))).pages) > 1
    assert generar_pdf("", "vacío").startswith(b"%PDF")


def test_comparar_versiones_marca_añadidas_quitadas_e_iguales():
    antes = "## Experiencia\nCamarera · Bar Sol\n- Atención en sala\n"
    despues = "## Experiencia\nCamarera · Bar Sol\n- Atención en sala y barra\n- Manejo de TPV\n"
    r = comparar_versiones(antes, despues)
    assert {"linea": "## Experiencia", "marca": "igual"} in r
    assert {"linea": "Camarera · Bar Sol", "marca": "igual"} in r
    assert {"linea": "- Atención en sala", "marca": "quitada"} in r
    assert {"linea": "- Atención en sala y barra", "marca": "añadida"} in r
    assert {"linea": "- Manejo de TPV", "marca": "añadida"} in r
    assert len(r) == 5


def test_dos_textos_identicos_no_dan_cambios():
    r = comparar_versiones(MD, MD)
    assert r and all(x["marca"] == "igual" for x in r)
    assert comparar_versiones("", "") == []


def test_solo_quitar_o_solo_añadir():
    assert comparar_versiones("a\nb", "a") == [{"linea": "a", "marca": "igual"},
                                               {"linea": "b", "marca": "quitada"}]
    assert comparar_versiones("", "a") == [{"linea": "a", "marca": "añadida"}]
