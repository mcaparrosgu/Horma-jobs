"""Spec 012, T14a (RF-12.14): notas esperadas de D-082 a D-084 y motivos sin condiciones (D-026)."""
import json
import re
from pathlib import Path

CASOS = Path(__file__).parents[1] / "evals" / "recomendacion" / "casos"
_CONDICION = re.compile(
    r"sueldo|contrato|remoto|ciudad|presencial|temporal|indefinido|condiciones|m[ií]nimo|pagado", re.I)
NUEVAS = {"02": (85, "D-083"), "04": (35, "D-083"), "07": (75, "D-082"), "13": (40, "D-083"),
          "15": (30, "D-083"), "18": (15, "D-083"), "21": (35, "D-083")}


def _esperados() -> dict[str, dict]:
    return {c.name[:2]: json.loads((c / "esperado.json").read_text(encoding="utf-8"))
            for c in CASOS.iterdir() if c.is_dir()}


def test_ningun_motivo_nombra_condiciones():
    assert [n for n, e in _esperados().items() if _CONDICION.search(e.get("motivo", ""))] == []


def test_los_ocho_esperados_nuevos_citan_su_decision():
    esperados = _esperados()
    for caso, (nota, decision) in NUEVAS.items():
        assert esperados[caso]["nota"] == nota, caso
        assert decision in esperados[caso]["motivo"], caso
    assert esperados["48"]["notas"] == [85, 35, 2, 45, 95]
    assert "D-084" in esperados["48"]["motivo"]
