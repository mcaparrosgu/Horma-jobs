"""RT-02 y RT-13: las reglas de arquitectura se comprueban con import-linter."""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def test_contratos_de_import_linter():
    r = subprocess.run(
        [sys.executable, "-m", "importlinter.cli", "--config", str(RAIZ / "pyproject.toml")],
        cwd=RAIZ, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_solo_llm_importa_anthropic():
    for py in (RAIZ / "horma").rglob("*.py"):
        if "llm" in py.relative_to(RAIZ / "horma").parts[:1]:
            continue
        texto = py.read_text(encoding="utf-8")
        assert "import anthropic" not in texto and "from anthropic" not in texto, py
