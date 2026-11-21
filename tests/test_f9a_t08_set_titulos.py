"""Fase 9a, T08: la coincidencia de títulos se mide con títulos reales etiquetados por Mar (RF-9.3e).

Precisión ≥ 0,95 y cobertura ≥ 0,90. Si no llega, se ajusta `normalizar_titulo`, no el set. Mientras Mar no
haya etiquetado el set (`verificado_por_mar`), el test se salta."""
import json
from pathlib import Path

import pytest

from horma.tools.normalizar_titulo import normalizar_titulo

RUTA = Path(__file__).parent / "fixtures" / "titulos_puestos.json"
PRECISION_MINIMA = 0.95
COBERTURA_MINIMA = 0.90


def _casa(titulo: str, puesto: str) -> bool:
    return f" {normalizar_titulo(puesto)} " in f" {normalizar_titulo(titulo)} "


def test_el_set_tiene_unos_150_pares_con_su_propuesta():
    d = json.loads(RUTA.read_text(encoding="utf-8"))
    assert 120 <= len(d["pares"]) <= 200
    assert all(_casa(p["titulo"], p["puesto"]) == p["propuesta"] for p in d["pares"])


def test_precision_y_cobertura_sobre_los_titulos_etiquetados():
    d = json.loads(RUTA.read_text(encoding="utf-8"))
    if not d["verificado_por_mar"] or any(p["casa"] is None for p in d["pares"]):
        pytest.skip("Pendiente: Mar etiqueta «casa» en tests/fixtures/titulos_puestos.json")
    tp = fp = fn = 0
    for p in d["pares"]:
        dice = _casa(p["titulo"], p["puesto"])
        tp += dice and p["casa"]
        fp += dice and not p["casa"]
        fn += (not dice) and p["casa"]
    assert tp / (tp + fp) >= PRECISION_MINIMA, f"precisión {tp / (tp + fp):.2f}"
    assert tp / (tp + fn) >= COBERTURA_MINIMA, f"cobertura {tp / (tp + fn):.2f}"
