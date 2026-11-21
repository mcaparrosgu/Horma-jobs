"""Fase 3 · T21: consola de la fase 3 (RF-3.11, RT-04, RT-05)."""
import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from horma.cli import app as cli
from horma.evals import SETS, EsperadoCv, _entrada_cv

RAIZ = Path(__file__).resolve().parent.parent
TRAZA = [{"frase": "Camarera · Bar Sol", "fragmento": "Camarera en Bar Sol"}]
APROBADO = {"veredicto_cv": "aprobado", "veredicto_carta": "aprobado", "problemas": []}
OFERTA = json.loads((RAIZ / "evals/cv/ofertas/camarera-bar-luna.json").read_text(encoding="utf-8"))
ENTRADAS = {
    "redactor-cv": ({"cv_base": "Camarera en Bar Sol", "cv_maestro": "Camarera en Bar Sol", "oferta": OFERTA},
                    {"contenido": "## Experiencia\nCamarera · Bar Sol", "traza": TRAZA}),
    "redactor-carta": ({"cv_maestro": "Camarera en Bar Sol", "cv_adaptado": "Camarera en Bar Sol",
                        "oferta": OFERTA, "sector": "hosteleria_turismo"},
                       {"contenido": "Hola equipo,\nUn saludo", "traza": []}),
    "juez-candidatura": ({"cv": "Camarera · Bar Sol", "cv_traza": TRAZA, "carta": "Hola equipo",
                          "carta_traza": [], "cv_maestro": "Camarera en Bar Sol",
                          "cv_base": "Camarera en Bar Sol", "oferta": OFERTA}, APROBADO),
}


@pytest.fixture(autouse=True)
def _desde_la_raiz(monkeypatch):
    monkeypatch.chdir(RAIZ)  # la consola busca evals/cv/usuarias en la carpeta actual


def _json(ruta: Path, datos) -> Path:
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return ruta


@pytest.mark.parametrize("nombre", ENTRADAS)
def test_agente_correr_de_los_agentes_de_la_fase_3_en_simulado(tmp_path, nombre):
    entrada, respuesta = ENTRADAS[nombre]
    e, r_ = _json(tmp_path / "e.json", entrada), _json(tmp_path / "r.json", respuesta)
    r = CliRunner().invoke(cli, ["agente", "correr", nombre, "--entrada", str(e), "--simulado",
                                 "--respuesta", str(r_)])
    assert r.exit_code == 0, r.output


@pytest.mark.parametrize("aparcado", ["clasificador-respuesta", "generador-cv-base"])
def test_agente_aparcado_avisa_y_no_se_ejecuta(tmp_path, aparcado):
    e = _json(tmp_path / "e.json", {})
    r = CliRunner().invoke(cli, ["agente", "correr", aparcado, "--entrada", str(e)])
    assert r.exit_code == 2 and "aparcado" in r.output


@pytest.mark.parametrize("quitado", ["juez-cv", "juez-carta", "selector-cv-base"])
def test_agente_quitado_falla_con_un_mensaje_claro(tmp_path, quitado):
    e = _json(tmp_path / "e.json", {})
    r = CliRunner().invoke(cli, ["agente", "correr", quitado, "--entrada", str(e)])
    assert r.exit_code == 2
    assert "ya no existe" in r.output and ("juez-candidatura" in r.output or "elegir_cv_base" in r.output)


def _flujo_candidatura(tmp_path, *extra, input=None):
    caso = RAIZ / "evals/cv/casos/10-flujo-camarera-con-tres-cv-base"
    e = _entrada_cv(caso)
    esperado = EsperadoCv.model_validate_json((caso / "esperado.json").read_text(encoding="utf-8"))
    resp = _json(tmp_path / "r.json", SETS["cv"].simuladas(esperado, e))
    ofertas = _json(tmp_path / "ofertas.json", {"ofertas": [{"oferta_id": 5, "oferta": e["oferta"]}]})
    orden = ["flujo", "correr", "candidatura", "--usuaria", e["usuaria"], "--oferta", "5",
             "--ofertas", str(ofertas), "--simulado", "--respuestas", str(resp), *extra]
    return CliRunner().invoke(cli, orden, input=input)


def test_flujo_correr_candidatura_con_usuaria_y_oferta_sin_api(tmp_path):
    r = _flujo_candidatura(tmp_path)
    assert r.exit_code == 0, r.output
    assert "elegir_cv_base" in r.output and "componer" in r.output


def test_flujo_correr_candidatura_guarda_un_json_por_paso_con_traza(tmp_path):
    r = _flujo_candidatura(tmp_path, "--traza", str(tmp_path / "t"), "--paso-a-paso", "--salida",
                           str(tmp_path / "s.json"), input="\n" * 20)
    assert r.exit_code == 0, r.output
    nombres = sorted(p.name for p in (tmp_path / "t").iterdir())
    assert nombres[0] == "01-elegir_cv_base.json" and nombres[-1].endswith("componer.json")
    assert "entrada:" in r.output
    assert json.loads((tmp_path / "s.json").read_text(encoding="utf-8")) in ("lista", "pendiente_de_ti")


def test_oferta_que_no_esta_en_el_catalogo_da_error(tmp_path):
    ofertas = _json(tmp_path / "o.json", {"ofertas": []})
    r = CliRunner().invoke(cli, ["flujo", "correr", "candidatura", "--usuaria", "ana", "--oferta", "9",
                                 "--ofertas", str(ofertas), "--simulado", "--respuestas",
                                 str(_json(tmp_path / "r.json", []))])
    assert r.exit_code == 2


def test_flujo_correr_clasificar_respuesta_esta_aparcado(tmp_path):
    entrada = _json(tmp_path / "e.json", {"texto": "Queremos entrevistarte.", "estado_actual": "enviada"})
    r = CliRunner().invoke(cli, ["flujo", "correr", "clasificar_respuesta", "--entrada", str(entrada),
                                 "--simulado"])
    assert r.exit_code == 2 and "aparcado" in r.output  # RF-10.11d


@pytest.mark.usefixtures("limites_reales")
@pytest.mark.parametrize("conjunto", ["cv", "respuestas"])
def test_eval_correr_cv_y_respuestas_en_simulado(conjunto):
    r = CliRunner().invoke(cli, ["eval", "correr", conjunto, "--simulado"])
    assert r.exit_code == 0, r.output
    assert "APROBADO" in r.output
    assert os.path.exists("evals")


# --- T22: cierre (CI, .env.example, README, specs) ----------------------------------------------
def _texto(ruta: str) -> str:
    return (RAIZ / ruta).read_text(encoding="utf-8")


def test_ci_corre_los_dos_sets_de_la_fase_3_con_tope_y_en_simulado_sin_clave():
    ci = _texto(".github/workflows/ci.yml")
    simulado, real = ci.split("evals-reales:")
    assert "eval correr cv --simulado" in simulado and "respuestas" not in simulado  # aparcado (RF-10.11d)
    assert "eval correr cv --tope-coste 1.0" in real and "respuestas" not in real


def test_env_example_marca_los_topes_nuevos_como_de_construccion():
    env = _texto(".env.example")
    assert "TOPE_COSTE_CANDIDATURA=" in env and "TOPE_COSTE_RESPUESTA" not in env
    assert "de construcción" in env.split("TOPE_COSTE_CANDIDATURA")[0].split("Fase 3")[-1]


def test_readme_documenta_los_comandos_de_la_fase_3():
    readme = _texto("README.md")
    for comando in ("flujo correr candidatura", "eval correr cv", "redactor-cv", "juez-candidatura"):
        assert comando in readme
    assert "juez-cv" not in readme.replace("`juez-cv`, `juez-carta` y `selector-cv-base`", "")
    assert "### Fase 3" in readme


def test_specs_dan_la_fase_3_por_construida():
    assert "Fase 3 (candidatura, construida)" in _texto("specs/system.md")
    index = next(x for x in _texto("specs/index.md").splitlines() if x.startswith("- `003-candidatura/`"))
    assert "T01-T32" in index and "bloque H" in index
    assert "juez-candidatura" in _texto("specs/system.md")


def test_flujo_listar_no_falla_con_una_consola_cp1252():
    """Windows: la salida estándar en cp1252 no puede escribir «→» (se fuerza UTF-8)."""
    import subprocess
    import sys

    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "UV_NO_SYNC": "1"}
    env.pop("PYTHONUTF8", None)
    r = subprocess.run([sys.executable, "-c", "from horma.cli import app; app()", "flujo", "listar"], env=env,
                       capture_output=True, cwd=RAIZ)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    assert "→".encode() in r.stdout
