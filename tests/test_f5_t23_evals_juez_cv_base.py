"""Fase 5 · T23: evals del juez (`evals/cv/`) y del CV base (`evals/cv-base/`) con los casos nuevos de
longitud, fechas, resumen que no casa y muletillas (RF-5.4e, RF-5.7e). Solo en simulado: la medición con el
modelo real pide el OK de Mar antes de gastar."""
import json
from pathlib import Path

import pytest

from horma.evals import SETS, EsperadoCv, EsperadoCvBase, cargar_usuaria, correr_set
from horma.llm.simulado import ProveedorSimulado
from horma.tools.validar_cv import validar_cv

pytestmark = pytest.mark.usefixtures("limites_reales")

RAIZ = Path(__file__).resolve().parent.parent / "evals"


def _json(ruta):
    return json.loads(ruta.read_text(encoding="utf-8"))


def _casos(nombre):
    return {p.name: p for p in sorted((RAIZ / nombre / "casos").iterdir()) if p.is_dir()}


def test_el_eval_cv_pasa_en_simulado_con_los_casos_nuevos():
    r = correr_set("cv", raiz=RAIZ.parent / "evals", simulado=True)
    assert r["aprobado"] and r["casos"] >= 21 and all(x == 1.0 for x in r["campos"].values())


def test_el_eval_cv_base_pasa_en_simulado_con_los_casos_nuevos():
    r = correr_set("cv-base", raiz=RAIZ.parent / "evals", simulado=True)
    assert r["aprobado"] and r["casos"] >= 9 and all(x == 1.0 for x in r["campos"].values())


def test_el_eval_cv_tiene_los_casos_de_longitud_fechas_resumen_muletillas_y_frases_de_ia():
    esperados = {n: EsperadoCv.model_validate(_json(c / "esperado.json")) for n, c in _casos("cv").items()}
    errores = {e.error: e for e in esperados.values()}
    for error in ("cv_largo", "cv_corto", "fechas_incoherentes", "resumen_no_casa", "muletilla_ia",
                  "suena_a_ia"):
        assert error in errores, error
    assert errores["resumen_no_casa"].problema == "incoherente"
    assert errores["suena_a_ia"].problema == "suena_a_ia" and errores["suena_a_ia"].rechazado_por == "juez"
    assert errores["muletilla_ia"].rechazado_por == "verificador"  # la lista la busca el código


def test_el_eval_cv_base_tiene_los_casos_de_cv_corto_y_muletillas():
    entradas = {n: _json(c / "entrada.json") for n, c in _casos("cv-base").items()}
    esperados = {n: EsperadoCvBase.model_validate(_json(c / "esperado.json"))
                 for n, c in _casos("cv-base").items()}
    rechazados = [n for n, e in esperados.items() if e.rechazados]
    # Largo, fechas al revés y resumen que no casa solo van en `cv` y en los tests: el modelo real los
    # corrige o los condensa y el CV base sale bien (medido el 18-nov, T23).
    assert len(rechazados) == 2
    assert sum(1 for n in rechazados if validar_cv(entradas[n]["cv_maestro"])) == 1  # el corto


def test_los_formatos_los_decide_el_codigo_y_no_llaman_al_modelo():
    prov = ProveedorSimulado([])
    r = correr_set("cv", proveedor=prov, simulado=False,
                   raiz=_copiar_solo("formato"))
    assert r["aprobado"] and prov.llamadas == []


def _copiar_solo(prefijo):
    import shutil
    import tempfile
    destino = Path(tempfile.mkdtemp()) / "cv"
    shutil.copytree(RAIZ / "cv", destino, ignore=shutil.ignore_patterns("resultados"))
    for c in (destino / "casos").iterdir():
        if prefijo not in c.name:
            shutil.rmtree(c)
    return destino.parent


def test_los_cv_de_prueba_de_los_evals_tienen_un_tamano_realista():
    ana = cargar_usuaria(RAIZ / "cv" / "usuarias" / "ana")
    assert validar_cv(ana["cv_maestro"]) == []
    assert all(validar_cv(c["contenido"]) == [] for c in ana["cvs_base"])


def test_los_dos_sets_tienen_umbral_en_umbrales_json():
    umbrales = _json(RAIZ / "umbrales.json")
    assert umbrales["cv"]["campos"] >= 0.9 and umbrales["cv-base"]["campos"] >= 0.9
    assert "cv" in SETS and "cv-base" in SETS
