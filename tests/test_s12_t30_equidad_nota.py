"""Spec 012 · T30: equidad de la nota en pares que solo cambian edad, nacionalidad o un hueco (RF-12.22)."""
import json
import shutil
from pathlib import Path

from horma.evals import correr_set
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.perfil import Perfil
from horma.tools.copia_ciega import copia_ciega

RAIZ = Path(__file__).resolve().parent.parent / "evals"
PAR = ("49-par-edad-adm-a", "50-par-edad-adm-b")
HUECO = ("57-par-hueco-almacen-a", "58-par-hueco-almacen-b")


def _respuestas(caso: str, nota: int, explicacion: str) -> list[dict]:
    entrada = json.loads((RAIZ / "recomendacion" / "casos" / caso / "entrada.json").read_text("utf-8"))
    puesto = copia_ciega(Perfil.model_validate(entrada["perfil"])).experiencias[0].puesto
    return [{"matches": [{"oferta_id": 1, "nota": nota, "condiciones": "alto", "explicacion": explicacion,
                          "cita_perfil": puesto,
                          "cita_oferta": entrada["oferta"]["titulo"]}]},
            {"apoyada": True, "motivo": "Sí."}]


def _correr(tmp_path, par, notas_a, notas_b,
            explicacion="Tu experiencia encaja con el puesto. La oferta pide lo mismo."):
    for caso in par:
        shutil.copytree(RAIZ / "recomendacion" / "casos" / caso, tmp_path / "recomendacion" / "casos" / caso)
    respuestas = []
    for caso, notas in zip(par, (notas_a, notas_b), strict=True):
        for n in notas:
            respuestas += _respuestas(caso, n, explicacion)
    return correr_set("recomendacion", raiz=tmp_path, proveedor=ProveedorSimulado(respuestas),
                      veces=len(notas_a))


def test_dos_medianas_a_mas_de_3_puntos_hacen_fallar_la_equidad(tmp_path):
    r = _correr(tmp_path, PAR, [94, 94, 94], [90, 90, 94])
    assert r["metricas"] == {"equidad": 0.0, "pares_mal": [PAR[0]]} and not r["aprobado"]


def test_manda_la_mediana_y_3_puntos_valen(tmp_path):
    r = _correr(tmp_path, PAR, [94, 94, 86], [91, 100, 91])  # medianas 94 y 91
    assert r["metricas"] == {"equidad": 1.0, "pares_mal": []}


def test_una_explicacion_que_cita_el_hueco_hace_fallar_la_equidad(tmp_path):
    r = _correr(tmp_path, HUECO, [95], [95],
                explicacion="Tienes experiencia en almacén pese a tu parón. La oferta pide carné.")
    assert r["metricas"]["equidad"] == 0.0 and not r["aprobado"]


def test_el_set_simulado_entero_mide_los_seis_pares(tmp_path):
    shutil.copytree(RAIZ / "recomendacion", tmp_path / "recomendacion")
    r = correr_set("recomendacion", raiz=tmp_path, simulado=True)
    assert r["metricas"] == {"equidad": 1.0, "pares_mal": []} and r["aprobado"]
