"""S8, T44: un resumen y un titular por CV (RF-10.14d). Simulado: sin llamar al modelo."""
from pathlib import Path

import pytest

from horma.agents.redactor_cv.schemas import EntradaRedactorCv
from horma.flows.perfilar import crear as crear_perfilar
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.perfil import Perfil
from horma.tools.avisos_perfil import avisos_perfil
from horma.tools.convertir_cv import convertir_cv
from horma.tools.resumenes_cv import resumen_de, titular_de
from horma.web.queue import worker

pytestmark = pytest.mark.usefixtures("juez_automatico")

TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior", "stack": []}
CV_A = ("Irene Navarro\nJefa de sala · Hostelería\nirene@example.com\nPERFIL\nSé organizar equipos en sala.\n"
        "EXPERIENCIA\nJefa de sala en Hotel Mar, 2019-2023\n")
CV_B = ("Irene Navarro\nAuxiliar administrativa · Facturación\nRESUMEN PROFESIONAL\nDos años facturando.\n"
        "Cuadro la caja a diario.\nEXPERIENCIA\nAuxiliar en Levante Frío, 2023-2024\n")
CV_C = "Irene Navarro\nEXPERIENCIA\nCamarera en Bar Sol, 2015-2018\n"


def _correr(*cvs):
    textos = [{"cv_id": i + 1, "nombre": f"CV{i}", "texto": t} for i, t in enumerate(cvs)]
    flujo = crear_perfilar(proveedor=ProveedorSimulado([{"perfil": {}}, TAX]))
    return Perfil.model_validate(flujo.run({"cvs": textos})["perfil"])


def test_titular_y_resumen_de_un_cv():
    assert titular_de(CV_A) == "Jefa de sala · Hostelería"
    assert resumen_de(CV_A) == "Sé organizar equipos en sala."
    assert resumen_de(CV_B) == "Dos años facturando. Cuadro la caja a diario."
    assert titular_de(CV_C) is None and resumen_de(CV_C) is None


def test_el_perfil_guarda_los_dos_resumenes_con_su_origen():
    p = _correr(CV_A, CV_B)
    assert [(r.origen.cv_id, r.valor) for r in p.resumenes] == [
        (1, "Sé organizar equipos en sala."), (2, "Dos años facturando. Cuadro la caja a diario.")]
    assert [t.origen.cv_id for t in p.titulares] == [1, 2]
    # el más reciente
    assert p.resumen.origen.cv_id == 2 and p.titular.valor == "Auxiliar administrativa · Facturación"


def test_sin_resumen_solo_sale_si_ninguno_lo_tiene():
    sin = _correr(CV_C)
    assert any(a.clave == "sin_resumen" for a in avisos_perfil(sin))
    con = _correr(CV_C, CV_A)
    assert not any(a.clave == "sin_resumen" for a in avisos_perfil(con))
    assert con.resumen.origen.cv_id == 2   # el único que lo tiene, aunque no sea el último CV subido


def test_tu_cv_completo_usa_el_del_cv_mas_reciente():
    from horma.tools.componer_cv_maestro import componer_cv_maestro
    maestro = componer_cv_maestro(_correr(CV_A, CV_B))
    assert "Dos años facturando." in maestro and "organizar equipos en sala" not in maestro


def test_el_redactor_recibe_los_otros_resumenes(monkeypatch):
    p = _correr(CV_A, CV_B)
    monkeypatch.setattr(worker.repo_perfiles, "perfil_modelo", lambda fila: p)
    assert worker._otros_resumenes({}) == ["Sé organizar equipos en sala."]
    assert EntradaRedactorCv.model_fields["otros_resumenes"].default_factory() == []


def test_los_cv_de_la_pasada():
    base = Path(__file__).resolve().parent.parent / "pruebas-manuales" / "pasada-22nov"
    if not base.exists():
        pytest.skip("documentos de prueba locales no disponibles")
    a = convertir_cv((base / "CV-Irene-Navarro-Administracion.docx").read_bytes(), "docx")
    h = convertir_cv((base / "CV-Irene-Navarro-Hosteleria.pdf").read_bytes(), "pdf")
    p = _correr(h, a)
    assert len(p.resumenes) == 2 and len(p.titulares) == 2
    assert p.resumen.valor.startswith("Auxiliar administrativa con dos años")
