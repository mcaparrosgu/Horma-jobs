"""Fase 9a, T08: la coincidencia de títulos se mide con títulos reales etiquetados por Mar (RF-9.3e).

Precisión ≥ 0,95 y cobertura ≥ 0,90. Si no llega, se ajusta `normalizar_titulo`, no el set. Mientras Mar no
haya etiquetado el set (`verificado_por_mar`), el test se salta."""
import json
from pathlib import Path

import pytest

from horma.tools.normalizar_titulo import casa_con_puestos, normalizar_titulo

RUTA = Path(__file__).parent / "fixtures" / "titulos_puestos.json"
# Las formas que dio el modelo para los puestos del set (26-nov, D-061).
MODELO = json.loads((RUTA.parent / "sinonimos_modelo.json").read_text(encoding="utf-8"))
PRECISION_MINIMA = 0.95
COBERTURA_MINIMA = 0.90


def _casa(titulo: str, puesto: str) -> bool:
    return f" {normalizar_titulo(puesto)} " in f" {normalizar_titulo(titulo)} "


def test_el_set_tiene_unos_200_pares_con_su_propuesta():
    d = json.loads(RUTA.read_text(encoding="utf-8"))
    assert 180 <= len(d["pares"]) <= 220  # 150 de 9a y ~50 sinónimos (RF-12.4)
    assert all(_casa(p["titulo"], p["puesto"]) == p["propuesta"] for p in d["pares"])


def test_precision_y_cobertura_sobre_los_titulos_etiquetados():
    d = json.loads(RUTA.read_text(encoding="utf-8"))
    if not d["verificado_por_mar"] or any(p["casa"] is None for p in d["pares"]):
        pytest.skip("Pendiente: Mar etiqueta «casa» en tests/fixtures/titulos_puestos.json")
    tp = fp = fn = 0
    for p in d["pares"]:
        dice = casa_con_puestos(p["titulo"], [p["puesto"]], sinonimos=MODELO)  # RF-12.4c
        tp += dice and p["casa"]
        fp += dice and not p["casa"]
        fn += (not dice) and p["casa"]
    assert tp / (tp + fp) >= PRECISION_MINIMA, f"precisión {tp / (tp + fp):.2f}"
    assert tp / (tp + fn) >= COBERTURA_MINIMA, f"cobertura {tp / (tp + fn):.2f}"
