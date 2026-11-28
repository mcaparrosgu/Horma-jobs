"""Spec 012 · T14i (RF-12.21, D-098): el revisor del eval confirma cada rechazo con dos juicios más y guarda
el motivo de cada uno; la métrica es, por pasada, la parte de explicaciones sin rechazo confirmado."""
import shutil
from pathlib import Path

import pytest
from test_s12_t11_harness_nota import APOYADA, NO_APOYADA, UNA, _matches

from horma.evals import _cumple_recomendacion, _medir_recomendacion, cargar_umbrales, correr_set
from horma.llm.simulado import ProveedorSimulado

RAIZ = Path(__file__).resolve().parent.parent / "evals"
INVENTADA = _matches(UNA, explicacion="Hablas francés. La oferta pide francés.")


def _correr(tmp_path, *juicios):
    shutil.copytree(RAIZ / "recomendacion" / "casos" / UNA, tmp_path / "recomendacion" / "casos" / UNA)
    prov = ProveedorSimulado([INVENTADA, *juicios])
    return correr_set("recomendacion", raiz=tmp_path, proveedor=prov), prov


def test_un_rechazo_que_confirma_uno_de_los_dos_juicios_nuevos_suspende(tmp_path):
    r, _ = _correr(tmp_path, NO_APOYADA, APOYADA, NO_APOYADA)
    assert r["metricas"]["revisor"] == 0.0 and not r["aprobado"]
    [confirmado] = r["metricas"]["revisor_confirmados"]
    assert confirmado["caso"] == UNA and confirmado["pasada"] == 1
    assert confirmado["motivos"] == [NO_APOYADA["motivo"], APOYADA["motivo"], NO_APOYADA["motivo"]]


def test_un_rechazo_que_no_confirma_ninguno_no_cuenta(tmp_path):
    r, _ = _correr(tmp_path, NO_APOYADA, APOYADA, APOYADA)
    assert r["metricas"]["revisor"] == 1.0 and r["metricas"]["revisor_confirmados"] == []
    assert r["aprobado"]


def test_los_tres_juicios_quedan_en_la_salida_con_su_motivo(tmp_path):
    r, _ = _correr(tmp_path, NO_APOYADA, APOYADA, NO_APOYADA)
    [salida] = r["detalle"][0]["salidas"]
    assert salida["revisor"] == [NO_APOYADA, APOYADA, NO_APOYADA] and salida["sin_apoyo"]


def test_una_explicacion_apoyada_se_juzga_una_sola_vez(tmp_path):
    r, prov = _correr(tmp_path, APOYADA)
    assert len(prov.llamadas) == 2  # el `matcher` y un juicio
    assert r["detalle"][0]["salidas"][0]["revisor"] == [APOYADA]


def _medibles(por_pasada: list[list[bool]]) -> list[tuple[str, dict, dict]]:
    """Un caso por explicación; `por_pasada[i][j]`: la j tiene un rechazo confirmado en la pasada i."""
    casos = len(por_pasada[0])
    return [(f"caso-{j:02}", {"pasadas": [{"oferta_id": 1, "explicacion": "x", "sin_apoyo": p[j],
                                            "revisor": [NO_APOYADA] * 2 if p[j] else [APOYADA]}
                                           for p in por_pasada]}, {"nota": 50})
            for j in range(casos)]


@pytest.mark.parametrize("confirmados, cumple", [(1, True), (2, False)])
def test_el_umbral_es_el_95_por_ciento_en_cada_pasada(confirmados, cumple):
    umbrales = cargar_umbrales("recomendacion")["metricas"]
    buena = [False] * 20
    mala = [True] * confirmados + [False] * (20 - confirmados)
    medidas = _medir_recomendacion(_medibles([buena, mala, buena]))
    assert medidas["revisor_pasadas"] == [1.0, round(1 - confirmados / 20, 4), 1.0]
    assert medidas["revisor"] == min(medidas["revisor_pasadas"])
    assert _cumple_recomendacion(medidas, umbrales) is cumple
