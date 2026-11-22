"""S7 · T36: ajustes tras la revisión en el navegador (nombre en el CV completo, nombre de las descargas,
formatos admitidos, avisos y barras)."""
import re
from pathlib import Path

from horma.web.services.candidaturas import _slug

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"


def leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


def test_el_nombre_de_la_descarga_lleva_tipo_puesto_y_empresa():
    assert _slug("Data Analyst (Híbrido)") == "data-analyst-hibrido"
    assert _slug("Veeva Systems, Inc.") == "veeva-systems-inc"
    assert _slug(None) == "" and len(_slug("x" * 200)) <= 40


def test_subir_archivo_dice_los_formatos_y_el_peso():
    html = leer("perfil.html")
    assert "PDF, DOCX o Markdown (.md)" in html and "5 MB" in html


def test_ofertas_sin_el_parrafo_largo_de_que_buscas():
    assert "Marca lo que buscas" not in leer("ofertas.html")


def test_barras_en_verde_lima_en_todos_los_temas():
    tokens = leer("tokens.css")
    assert re.findall(r"--bar-fill:\s*([^;]+);", tokens) == ["#c8f031"] * 3


def test_candidatura_sin_preparando_sobre_la_barra_y_con_frase_clara():
    js = leer("candidatura.js")
    assert 'estado !== "Preparando"' in js
    assert "no te bloquean" not in js and "Puedes aprobar aunque queden avisos" in js


def test_perfil_deja_anadir_o_modificar_el_nombre():
    js = leer("perfil.js")
    assert "function filaNombre" in js and 'campo: "nombre"' in js
