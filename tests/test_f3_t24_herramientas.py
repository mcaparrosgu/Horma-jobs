"""Fase 3 · T24: herramientas `elegir_cv_base` y `avisos_vigentes` (RF-3.1b, RF-3.6c, RF-3.8)."""
from datetime import datetime, timezone

import pytest

from horma.schemas.candidatura import Aviso, Problema
from horma.schemas.oferta import Auditoria, Oferta
from horma.schemas.taxonomia import Taxonomia
from horma.tools.avisos_vigentes import avisos_vigentes
from horma.tools.elegir_cv_base import MOTIVOS, elegir_cv_base

OFERTA = Oferta(titulo="Camarera", requisitos=["sala"],
                auditoria=Auditoria(fantasma=False, fraude=False, salario_publicado=False),
                taxonomia=Taxonomia(sector="hosteleria_turismo", familia="hosteleria_restauracion",
                                    nivel="junior", stack=[]))


def _cv(id, sector="comercio_retail", familia="ventas_comercial", dia=1, estado="hecho", usuaria_id=7):
    return {"id": id, "usuaria_id": usuaria_id, "nombre": f"CV {id}", "sector": sector, "familia": familia,
            "estado": estado, "contenido": "x", "creado_en": datetime(2026, 11, dia, tzinfo=timezone.utc)}


SECTOR, FAMILIA = "hosteleria_turismo", "hosteleria_restauracion"


def _id(cvs, oferta=OFERTA):
    return elegir_cv_base(oferta, cvs, 7)[0]["id"]


# --- elegir_cv_base ----------------------------------------------------------------------------
def test_gana_el_que_coincide_en_familia_y_sector():
    cvs = [_cv(1, sector=SECTOR, dia=9), _cv(2, familia=FAMILIA, dia=9), _cv(3, SECTOR, FAMILIA, dia=1)]
    elegido, motivo = elegir_cv_base(OFERTA, cvs, 7)
    assert elegido["id"] == 3 and motivo == "Coincide en puesto y sector con la oferta"


def test_despues_gana_la_familia_y_despues_el_sector():
    assert elegir_cv_base(OFERTA, [_cv(1, sector=SECTOR, dia=9), _cv(2, familia=FAMILIA, dia=1)], 7) == (
        _cv(2, familia=FAMILIA, dia=1), "Coincide en el puesto")
    elegido, motivo = elegir_cv_base(OFERTA, [_cv(1), _cv(2, sector=SECTOR, dia=1)], 7)
    assert elegido["id"] == 2 and motivo == "Coincide en el sector"


def test_si_no_coincide_ninguno_gana_el_mas_reciente():
    elegido, motivo = elegir_cv_base(OFERTA, [_cv(1, dia=3), _cv(2, dia=5), _cv(3, dia=4)], 7)
    assert elegido["id"] == 2 and motivo == "Ninguno coincide; es el más reciente"


def test_a_igualdad_gana_el_mas_reciente_y_luego_el_id_mayor():
    assert _id([_cv(1, SECTOR, FAMILIA, dia=2), _cv(2, SECTOR, FAMILIA, dia=6)]) == 2
    sin_fecha = [{**_cv(i, SECTOR, FAMILIA), "creado_en": None} for i in (1, 2)]
    assert _id(sin_fecha) == 2


def test_ignora_rechazados_y_ajenos():
    cvs = [_cv(1, SECTOR, FAMILIA, estado="rechazado"), _cv(2, SECTOR, FAMILIA, usuaria_id=99), _cv(3)]
    assert _id(cvs) == 3


@pytest.mark.parametrize("cvs", [[], [_cv(1, estado="rechazado")], [_cv(1, usuaria_id=99)]])
def test_sin_ningun_cv_base_valido_es_un_error(cvs):
    with pytest.raises(ValueError, match="CV base válido"):
        elegir_cv_base(OFERTA, cvs, 7)


def test_cada_caso_da_su_motivo_en_llano_y_admite_la_oferta_como_dict():
    assert len(set(MOTIVOS)) == 4 and not any("(" in m or "_" in m for m in MOTIVOS)
    assert elegir_cv_base(OFERTA.model_dump(mode="json"), [_cv(1, SECTOR, FAMILIA)], 7)[1] == MOTIVOS[0]


def test_no_llama_al_modelo_ni_toca_la_entrada():
    import horma.tools.elegir_cv_base as modulo
    assert "horma.llm" not in open(modulo.__file__, encoding="utf-8").read()
    cvs = [_cv(1), _cv(2, SECTOR, FAMILIA)]
    copia = [dict(c) for c in cvs]
    elegir_cv_base(OFERTA, cvs, 7)
    assert cvs == copia


# --- avisos_vigentes ---------------------------------------------------------------------------
def _p(documento, frase, tipo="inflado"):
    return Problema(documento=documento, tipo=tipo, frase=frase, motivo="m")


def test_conserva_solo_los_problemas_cuya_frase_sigue_literal():
    cv = "## Experiencia\nLíder de sala en Bar Sol\nManejo de TPV"
    problemas = [_p("cv", "Líder de sala en Bar Sol"), _p("cv", "Frase que ya se reescribió")]
    avisos = avisos_vigentes("cv", cv, problemas)
    assert [a.frase for a in avisos] == ["Líder de sala en Bar Sol"] and isinstance(avisos[0], Aviso)
    assert avisos[0].documento == "cv" and "inflado" not in avisos[0].mensaje


def test_solo_cuenta_los_problemas_de_su_documento():
    problemas = [_p("cv", "frase uno"), _p("carta", "frase uno")]
    assert [a.documento for a in avisos_vigentes("carta", "frase uno", problemas)] == ["carta"]
    assert [a.documento for a in avisos_vigentes("cv", "frase uno", problemas)] == ["cv"]


def test_acepta_dicts_y_no_repite_avisos():
    d = {"documento": "carta", "tipo": "repite_cv", "frase": "Copia", "motivo": "m"}
    assert len(avisos_vigentes("carta", "Copia del CV", [d, d])) == 1


def test_un_documento_editado_sin_la_frase_ya_no_tiene_aviso():
    assert avisos_vigentes("cv", "Texto nuevo", [_p("cv", "Texto viejo")]) == []
    assert avisos_vigentes("cv", "", [_p("cv", "")]) == []
