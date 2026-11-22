"""S7, T34: PDF sobrio del CV y de la carta; la carta como párrafos en «Ver» (RF-10.4b, RF-10.4d)."""
import io
import re
from pathlib import Path

from pypdf import PdfReader

from horma.tools.generar_pdf import generar_pdf

ESTATICOS = Path(__file__).parent.parent / "horma" / "web" / "static"
CV = """# Ana Pérez García

Camarera y atención al cliente

## Experiencia

Camarera · Hotel Mar · 2018-2022
Atendía a 40 clientes al día.
**Jefa de sala · Bar Sol · ene 2022 - actualidad**
- Coordiné a un equipo de 5 personas

## Formación

FP Hostelería · IES Mar · 2016-2018

## Habilidades

TPV
Atención al cliente
"""
CARTA = ("# Hola equipo de Hotel Sol\n\nMe interesa el puesto porque llevo seis años en sala.\n\n"
         "Un saludo\nAna\n")


def texto(pdf: bytes) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)


def test_el_cv_sale_con_nombre_secciones_y_fechas_en_orden():
    t = texto(generar_pdf(CV, "CV"))
    esperado = ("Ana Pérez García", "Camarera y atención", "EXPERIENCIA", "Camarera · Hotel Mar", "2018-2022",
                "ene 2022 - actualidad", "FORMACIÓN", "2016-2018", "HABILIDADES")
    orden = [t.index(x) for x in esperado]
    assert orden == sorted(orden)
    assert "TPV · Atención al cliente" in t          # habilidades en una línea
    assert "**" not in t and "##" not in t


def test_la_carta_es_texto_plano_sin_secciones_ni_marcas():
    t = texto(generar_pdf(CARTA, "Carta", "carta"))
    assert "Hola equipo de Hotel Sol" in t and "Un saludo" in t and "Ana" in t
    assert not re.search(r"\*\*|##|[A-ZÁÉÍÓÚ]{6,}", t)     # sin secciones en mayúsculas


def test_usa_la_tipografia_de_la_marca_y_no_lleva_imagenes():
    pdf = generar_pdf(CV, "CV")
    nombres = {f.get("/BaseFont", "") for p in PdfReader(io.BytesIO(pdf)).pages
               for f in (r.get_object() for r in p["/Resources"]["/Font"].values())}
    assert any("Familjen" in n for n in nombres) and any("DMMono" in n or "DM" in n for n in nombres)
    assert b"/Subtype /Image" not in pdf


def test_ver_pinta_la_carta_como_parrafos():
    comun = (ESTATICOS / "comun.js").read_text(encoding="utf-8")
    assert "function cartaBonita" in comun and "innerHTML" not in comun
    candidatura = (ESTATICOS / "candidatura.js").read_text(encoding="utf-8")
    assert 'clave === "carta_contenido" ? cartaBonita' in candidatura


def test_las_fuentes_de_la_marca_estan_con_su_licencia():
    f = Path(__file__).parent.parent / "horma" / "assets" / "fuentes"
    for n in ("FamiljenGrotesk-Regular.ttf", "FamiljenGrotesk-Bold.ttf", "DMMono-Regular.ttf",
              "DMMono-Medium.ttf", "OFL.txt"):
        assert (f / n).exists(), n


def test_todos_los_js_de_la_web_tienen_sintaxis_valida():
    import subprocess
    for js in sorted(ESTATICOS.glob("*.js")):
        r = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
        assert r.returncode == 0, f"{js.name}: {r.stderr[:200]}"
