"""Spec 012, T04: el set `puestos` está etiquetado por tres etiquetadores y repasado por Mar (RF-12.1)."""
from pathlib import Path

from horma.evals import SETS, casos_de, correr_set
from horma.evals_puestos import _canonico

RAIZ = Path(__file__).resolve().parent.parent / "evals"


def _esperados():
    return {c.name: SETS["puestos"].esperado.model_validate_json(
        (c / "esperado.json").read_text(encoding="utf-8")) for c in casos_de(RAIZ, "puestos")}


def test_lo_que_no_tuvo_unanimidad_lo_ha_repasado_mar():
    for caso, e in _esperados().items():
        for titulo, x in e.etiquetas.items():
            unanime = len(set(x.votos)) == 1
            assert x.repaso_mar == (not unanime), (caso, titulo)
            assert not unanime or x.final == x.votos[0], (caso, titulo)


def test_cada_cv_con_datos_tiene_de_3_a_5_imprescindibles_distintos():
    for caso, e in _esperados().items():
        if caso == "10-sin-datos":  # sin ningún dato no hay nada que exigir
            assert e.imprescindibles == []
            continue
        assert 3 <= len(e.imprescindibles) <= 5, caso
        claves = [{_canonico(f) for f in formas} for formas in e.imprescindibles]
        assert not any(a & b for i, a in enumerate(claves) for b in claves[i + 1:]), caso


def test_d037_una_especialidad_es_el_mismo_puesto_y_otro_escalon_no():
    e = _esperados()
    assert e["01-camarera-hosteleria"].etiquetas["Camarero de barra"].final == "lo_ha_sido"
    assert e["27-nivel-alto-direccion-rrhh"].etiquetas["Jefa de Recursos Humanos"].final == "afin"


def test_el_set_mide_las_respuestas_guardadas_sin_gasto(tmp_path):
    import shutil

    shutil.copytree(RAIZ / "puestos", tmp_path / "puestos")
    r = correr_set("puestos", raiz=tmp_path, grabadas=True)
    assert r["coste"] == 0 and r["casos_ejecutados"] == 30 and r["metricas"]["kappa"] >= 0.61
