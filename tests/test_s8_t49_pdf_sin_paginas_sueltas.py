"""S8, T49: el PDF no deja páginas sueltas (RF-10.14o) y Perfil no enseña dos mensajes a la vez
(RF-10.14n)."""
import io
from pathlib import Path

import pytest
from pypdf import PdfReader

from horma.tools.generar_pdf import generar_pdf

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"


def _maestro(n_puestos: int, viñetas: int = 4) -> str:
    partes = ["# Irene Navarro Soler", "", "Jefa de sala · Hostelería", "", "## Resumen",
              "Profesional de sala con nueve años de experiencia en restaurantes, hoteles y cafeterías de la "
              "Comunidad Valenciana, con equipos de hasta ocho personas.", "", "## Experiencia"]
    for i in range(n_puestos):
        partes.append(f"Jefa de sala · Restaurante {i} · {2000 + i}-{2001 + i}")
        partes += [f"Coordiné un equipo de {i + 3} personas y organicé los turnos de cada semana."
                   for _ in range(viñetas)]
    partes += ["", "## Formación", "Grado Superior en Administración · IES Valencia · 2021-2023", "",
               "## Idiomas", "Inglés B2", "Francés A2"]
    return "\n".join(partes)


def _lineas_por_pagina(pdf: bytes) -> list[int]:
    return [len([x for x in (p.extract_text() or "").splitlines() if x.strip()])
            for p in PdfReader(io.BytesIO(pdf)).pages]


@pytest.mark.parametrize("puestos", range(3, 15))
def test_ninguna_pagina_con_menos_de_tres_lineas(puestos):
    lineas = _lineas_por_pagina(generar_pdf(_maestro(puestos), "CV completo"))
    assert all(n >= 3 for n in lineas), lineas


def test_un_titulo_de_seccion_nunca_queda_solo_al_pie():
    for puestos in range(3, 15):
        pdf = PdfReader(io.BytesIO(generar_pdf(_maestro(puestos), "CV completo")))
        for pagina in pdf.pages:
            lineas = [x for x in (pagina.extract_text() or "").splitlines() if x.strip()]
            assert lineas[-1].upper() not in {"EXPERIENCIA", "FORMACIÓN", "IDIOMAS", "RESUMEN"}, puestos


def test_el_cv_de_la_pasada_si_esta_disponible():
    base = Path(__file__).resolve().parent.parent / "pruebas-manuales" / "pasada-22nov"
    if not base.exists():
        pytest.skip("documentos de prueba locales no disponibles")
    from horma.tools.convertir_cv import convertir_cv
    texto = convertir_cv((base / "CV-Irene-Navarro-Hosteleria.pdf").read_bytes(), "pdf")
    md = "\n".join(f"## {x}" if x.isupper() and len(x) < 40 else x for x in texto.splitlines())
    assert all(n >= 3 for n in _lineas_por_pagina(generar_pdf(md, "CV completo")))


def test_perfil_no_enseña_la_barra_y_cv_subido_a_la_vez():
    js = (ESTATICOS / "perfil.js").read_text(encoding="utf-8")
    assert "CV subido; se está construyendo tu perfil." not in js
    assert "Listo: tu perfil está construido." in js and "leyendo" in js
