"""T09 (RF-4.4, RF-4.4b): umbrales en evals/umbrales.json, con el mínimo de cobertura ATS de `cv`."""
import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from horma.cli import app
from horma.evals import SETS, cargar_umbrales, cobertura_suficiente, correr_set

RAIZ = Path(__file__).resolve().parent.parent / "evals"


def test_hay_una_entrada_por_cada_set_y_cv_exige_ats_075():
    for nombre in SETS:
        assert cargar_umbrales(nombre)["campos"] == 0.9
    assert cargar_umbrales("cv")["cobertura_ats_media"] == 0.75


def test_la_cobertura_074_suspende_y_la_075_aprueba():
    assert cobertura_suficiente(0.74, 0.75) is False
    assert cobertura_suficiente(0.75, 0.75) is True
    assert cobertura_suficiente(None, 0.75) is True  # nada medido (p. ej. un solo caso de selección)


def test_un_set_sin_entrada_en_el_archivo_da_error(tmp_path):
    ruta = tmp_path / "umbrales.json"
    ruta.write_text(json.dumps({"ofertas": {"campos": 0.9}}), encoding="utf-8")
    with pytest.raises(LookupError, match="fuentes"):
        correr_set("fuentes", raiz=RAIZ, simulado=True, ruta_umbrales=ruta)


@pytest.mark.usefixtures("limites_reales")
def test_cv_suspende_si_el_minimo_de_cobertura_supera_la_media(tmp_path):
    raiz = tmp_path / "evals"
    shutil.copytree(RAIZ / "cv", raiz / "cv", ignore=shutil.ignore_patterns("resultados"))
    base = correr_set("cv", raiz=raiz, simulado=True)
    assert base["aprobado"] is True and base["cobertura_ats_media"] is not None
    ruta = tmp_path / "umbrales.json"
    exigente = {"cv": {"campos": 0.9, "cobertura_ats_media": base["cobertura_ats_media"] + 0.01}}
    ruta.write_text(json.dumps(exigente), encoding="utf-8")
    assert correr_set("cv", raiz=raiz, simulado=True, ruta_umbrales=ruta)["aprobado"] is False
    exacto = {"cv": {"campos": 0.9, "cobertura_ats_media": base["cobertura_ats_media"]}}
    ruta.write_text(json.dumps(exacto), encoding="utf-8")
    assert correr_set("cv", raiz=raiz, simulado=True, ruta_umbrales=ruta)["aprobado"] is True


def test_eval_correr_ya_no_tiene_umbral():
    r = CliRunner().invoke(app, ["eval", "correr", "ofertas", "--simulado", "--umbral", "0.5"])
    assert r.exit_code != 0
