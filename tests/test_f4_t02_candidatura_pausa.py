"""Fase 4 · T02: `candidatura` con definición compartida, paso `entregar` y pausa (RF-4.1, RF-4.3c)."""
import io

import pytest
from pypdf import PdfReader
from test_f3_t08_t09_flujos import APROBADO, CARTA, PASOS, _correr, _cv, _estado

from horma.flows import candidatura
from horma.flows.base import ErrorDePaso
from horma.llm.simulado import ProveedorSimulado


def _texto(pdf: bytes) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)


def test_la_definicion_se_comparte_y_entregar_es_pausa_y_final():
    d = candidatura.definicion(ProveedorSimulado([]))
    assert list(d.pasos) == [*PASOS, "entregar"]
    assert d.aristas["componer"] == "entregar" and d.inicio == "elegir_cv_base"
    assert d.pausas == {"entregar"} and d.finales == {"entregar"}
    esperadas = {"errores_cv", "cv_maestro", "oferta", "en_pausa", "cv_pdf", "carta_pdf"}
    assert esperadas <= candidatura.CLAVES_INTERNAS


def test_run_se_para_tras_componer_con_las_mismas_llamadas_que_antes():
    e, prov = _correr([_cv(), CARTA, APROBADO])
    assert e["en_pausa"] == "entregar" and len(prov.llamadas) == 3
    assert e["preparacion"] == "lista" and "cv_pdf" not in e


def test_reanudar_con_un_cv_editado_da_dos_pdf_con_el_texto_editado():
    prov = ProveedorSimulado([_cv(), CARTA, APROBADO])
    flujo = candidatura.crear(proveedor=prov)
    pausado = flujo.run(_estado())
    cambios = {"cv_contenido": "## Experiencia\nCamarera editada en Bar Sol",
               "carta_contenido": "Hola equipo,\nCarta editada por la usuaria.\nUn saludo"}
    e = flujo.reanudar("candidatura-1", cambios, estado=pausado)
    assert e["en_pausa"] is None
    assert "Camarera editada en Bar Sol" in _texto(e["cv_pdf"])
    assert "Carta editada por la usuaria" in _texto(e["carta_pdf"])
    assert len(prov.llamadas) == 3  # entregar no llama al modelo


def test_entregar_no_llama_al_modelo_ni_cambia_el_estado_de_la_candidatura():
    prov = ProveedorSimulado([])
    flujo = candidatura.crear(proveedor=prov)
    e = {"oferta": _estado()["oferta"], "cv_contenido": "## A\nuno", "carta_contenido": "Hola\nUn saludo",
         "preparacion": "lista", "en_pausa": "entregar"}
    e = flujo.reanudar("h", {}, estado=e)
    assert prov.llamadas == [] and e["preparacion"] == "lista" and "estado" not in e
    assert e["cv_pdf"][:4] == b"%PDF" and e["carta_pdf"][:4] == b"%PDF"


def test_reanudar_sin_pausa_pendiente_da_error():
    flujo = candidatura.crear(proveedor=ProveedorSimulado([]))
    with pytest.raises(ErrorDePaso):
        flujo.reanudar("h", {}, estado=_estado())
