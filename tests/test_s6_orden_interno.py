"""S6 · Orden interno (RF-10.11): contrato de imports, tabla ENCADENADOS y lo aparcado."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from horma.agents.registry import AGENTES, APARCADOS
from horma.flows.registry import APARCADOS as FLUJOS_APARCADOS
from horma.web.queue import worker


def test_los_routers_no_importan_repositorios_ni_la_cola():
    """T24: el contrato de import-linter (en pyproject.toml) se cumple."""
    exe = shutil.which("lint-imports", path=str(Path(sys.executable).parent))
    assert exe, "lint-imports no está instalado en el entorno"
    # utf-8 explícito: en Windows la consola usa cp1252 y no puede leer la salida de lint-imports.
    r = subprocess.run([exe], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONUTF8": "1"}, cwd=Path(__file__).resolve().parent.parent)
    assert r.returncode == 0, r.stdout[-800:]
    assert "Los routers solo hablan con servicios" in r.stdout


def test_los_encadenados_estan_en_una_sola_tabla():
    """T25: qué tarea lanza a cuál."""
    assert set(worker.ENCADENADOS) == {"procesar_oferta", "perfilar", "clasificar_perfil"}
    assert [f.__name__ for f in worker.ENCADENADOS["perfilar"]] == [
        "_puntuar_si_hay_propias", "_estilo_la_primera_vez", "_sinonimos"]
    assert [f.__name__ for f in worker.ENCADENADOS["procesar_oferta"]] == ["_propia_procesada"]
    assert [f.__name__ for f in worker.ENCADENADOS["clasificar_perfil"]] == [
        "_puntuar_si_hay_propias", "_sinonimos"]


def test_lo_aparcado_no_esta_activo_ni_se_puede_encolar():
    """T26: ni agentes ni flujos ni tareas del worker."""
    assert set(APARCADOS) == {"generador-cv-base", "clasificador-respuesta"}
    assert not set(APARCADOS) & set(AGENTES)
    assert set(FLUJOS_APARCADOS) == {"generar_cv_base", "clasificar_respuesta"}
    for tipo in ("generar_cv_base", "regenerar_cv_base", "extraer_oferta"):
        assert tipo not in worker.MANEJADORES
