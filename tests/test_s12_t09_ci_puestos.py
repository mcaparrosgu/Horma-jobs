"""Spec 012, T09 (D-064): la CI repite el set `puestos` con las respuestas grabadas, sin gasto."""
from pathlib import Path


def test_la_ci_corre_puestos_con_las_respuestas_grabadas():
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    calidad = ci.split("evals-reales:")[0]
    assert "horma eval correr puestos --grabadas --veces 3" in calidad
