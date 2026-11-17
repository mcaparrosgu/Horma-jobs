"""T10 (RF-4.4c): `calidad` corre todo en simulado y `evals-reales` usa el modelo solo a mano (RF-5.8)."""
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
CI = RAIZ / ".github" / "workflows" / "ci.yml"


def _ci() -> dict:
    d = yaml.safe_load(CI.read_text(encoding="utf-8"))
    d["on"] = d.pop(True, d.get("on"))  # YAML lee `on` como True
    return d


def test_hay_tres_jobs_y_se_lanza_en_push_pr_y_a_mano():
    d = _ci()
    assert {"secretos", "calidad", "evals-reales"} <= set(d["jobs"])
    assert {"push", "pull_request", "workflow_dispatch"} <= set(d["on"])


def test_calidad_corre_todo_en_simulado_y_cv_con_las_dos_implementaciones():
    texto = yaml.dump(_ci()["jobs"]["calidad"], width=10_000)
    assert "pytest" in texto and "ruff" in texto and "lint-imports" in texto
    for impl in ("plain", "langgraph"):
        assert f"eval correr cv --simulado --flujo {impl}" in texto
    assert "--simulado" in texto and "--tope-coste" not in texto


def test_evals_reales_solo_a_mano_con_langgraph_y_tope():
    # RF-5.8: aparcado hasta el lanzamiento; ni en push ni en PR.
    job = _ci()["jobs"]["evals-reales"]
    assert job["if"] == "github.event_name == 'workflow_dispatch'"
    assert "pull_request" not in job["if"] and "base_ref" not in job["if"]
    assert job["env"]["HORMA_FLOW_IMPL"] == "langgraph"
    texto = yaml.dump(job, width=10_000)
    assert "--simulado" not in texto  # no pasa a simulado nunca
    assert "--tope-coste 1.0 --flujo langgraph" in texto and "--tope-coste 1.0" in texto


def test_sin_clave_el_job_falla_y_no_imprime_su_valor():
    job = _ci()["jobs"]["evals-reales"]
    paso = next(p for p in job["steps"] if "Comprobar la clave" in p.get("name", ""))
    assert "exit 1" in paso["run"] and "-z" in paso["run"]
    assert "echo $ANTHROPIC_API_KEY" not in paso["run"] and 'echo "$ANTHROPIC_API_KEY"' not in paso["run"]
