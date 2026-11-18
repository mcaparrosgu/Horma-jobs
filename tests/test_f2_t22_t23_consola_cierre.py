"""Fase 2 · T22-T23: consola de la fase 2, catálogo para la consola y cierre (CI, Compose, README)."""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from typer.testing import CliRunner

from horma import config
from horma.cli import app as cli
from horma.flows.registry import FLUJOS, RESULTADO
from horma.web.db import sesion_sistema
from horma.web.main import crear_app

RAIZ = Path(__file__).resolve().parent.parent
TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior",
       "stack": []}
CV = "Ana Pérez\nCamarera en Bar Sol, 2020-2023\nInglés B2"


def _json(ruta: Path, datos) -> Path:
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return ruta


# --- T22: registro de flujos --------------------------------------------------------------------
def test_los_flujos_de_la_fase_2_estan_en_el_registro():
    for nombre, clave in {"perfilar": "perfil", "clasificar_perfil": "taxonomia",
                          "generar_cv_base": "cv_base", "recomendar": "recomendaciones"}.items():
        assert nombre in FLUJOS and RESULTADO[nombre] == clave


def test_flujo_listar_incluye_perfilar_y_recomendar():
    r = CliRunner().invoke(cli, ["flujo", "listar"])
    assert "perfilar: extraer → verificar_origen" in r.output
    assert "recomendar: candidatas → puntuar_tanda" in r.output


# --- T22: agente correr con los 4 agentes nuevos --------------------------------------------------
def test_agente_correr_clasificador_postulante_en_simulado(tmp_path):
    perfil = {"version": 1, "nombre": "Ana"}
    entrada = _json(tmp_path / "e.json", {"perfil": perfil})
    resp = _json(tmp_path / "r.json", TAX)
    r = CliRunner().invoke(cli, ["agente", "correr", "clasificador-postulante", "--entrada",
                                 str(entrada), "--simulado", "--respuesta", str(resp)])
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["familia"] == "hosteleria_restauracion"


# --- T22: flujo correr perfilar -------------------------------------------------------------------
def _extraccion():
    return {"perfil": {"experiencias": [{"puesto": "Camarera", "empresa": "Bar Sol", "origen": {
        "fuente": "cv", "cv_id": 1, "fragmento": "Camarera en Bar Sol, 2020-2023"}}]},
        "cv_maestro": "# Ana Pérez\n" + CV}


def test_flujo_correr_perfilar_con_un_cv_en_markdown_guarda_la_traza(tmp_path):
    cv = tmp_path / "cv.md"
    cv.write_text(CV, encoding="utf-8")
    resp = _json(tmp_path / "r.json", [_extraccion(), TAX])
    traza = tmp_path / "traza"
    r = CliRunner().invoke(cli, ["flujo", "correr", "perfilar", "--usuaria", "ana", "--entrada",
                                 str(cv), "--simulado", "--respuestas", str(resp),
                                 "--traza", str(traza), "--salida", str(tmp_path / "perfil.json")])
    assert r.exit_code == 0, r.output
    perfil = json.loads((tmp_path / "perfil.json").read_text(encoding="utf-8"))
    assert perfil["experiencias"][0]["puesto"] == "Camarera"
    assert sorted(p.name for p in traza.iterdir())[0] == "01-extraer.json"
    assert len(list(traza.iterdir())) == 6  # un JSON por paso


def test_flujo_correr_perfilar_acepta_un_docx_y_rechaza_un_archivo_falso(tmp_path):
    falso = tmp_path / "cv.pdf"
    falso.write_bytes(b"esto no es un pdf")
    resp = _json(tmp_path / "r.json", [])
    r = CliRunner().invoke(cli, ["flujo", "correr", "perfilar", "--entrada", str(falso),
                                 "--simulado", "--respuestas", str(resp)])
    assert r.exit_code == 2


# --- T22: recomendar ------------------------------------------------------------------------------
def _cand(i, titulo="Camarera"):
    return {"oferta_id": i, "oferta": {
        "titulo": f"{titulo} {i}", "taxonomia": TAX,
        "auditoria": {"fantasma": False, "fraude": False, "salario_publicado": False}}}


def _match(i, nota):
    return {"oferta_id": i, "nota": nota, "condiciones": "medio",
            "explicacion": "Tiene experiencia en sala. La oferta pide camarera.",
            "cita_perfil": "Camarera en Bar Sol", "cita_oferta": "camarera"}


def test_recomendar_con_ofertas_en_archivo_imprime_solo_lo_que_cae_en_el_rango(tmp_path):
    ofertas = _json(tmp_path / "o.json", {"ofertas": [_cand(1), _cand(2), _cand(3)]})
    resp = _json(tmp_path / "r.json", [{"matches": [_match(1, 90), _match(2, 30), _match(3, 60)]}])
    r = CliRunner().invoke(cli, ["recomendar", "ana", "--rango", "40-100", "--ofertas", str(ofertas),
                                 "--simulado", "--respuestas", str(resp)])
    assert r.exit_code == 0, r.output
    assert "Camarera 1" in r.output and "Camarera 3" in r.output and "Camarera 2" not in r.output
    assert r.output.index("Camarera 1") < r.output.index("Camarera 3")  # por nota, de mayor a menor


def test_recomendar_rechaza_un_rango_mal_escrito(tmp_path):
    ofertas = _json(tmp_path / "o.json", {"ofertas": []})
    r = CliRunner().invoke(cli, ["recomendar", "ana", "--rango", "90-10", "--ofertas", str(ofertas),
                                 "--simulado", "--respuestas", str(_json(tmp_path / "r.json", []))])
    assert r.exit_code == 2


def test_hay_un_perfil_de_prueba_valido_para_recomendar():
    from horma.schemas.perfil import Perfil

    ana = RAIZ / "evals" / "perfil" / "perfiles" / "ana.json"
    Perfil.model_validate_json(ana.read_text(encoding="utf-8"))


# --- T22: eval correr de los tres sets ------------------------------------------------------------
@pytest.mark.usefixtures("limites_reales")
@pytest.mark.parametrize("conjunto", ["perfil", "cv-base", "recomendacion"])
def test_eval_correr_simulado_de_los_tres_sets_de_la_fase_2(conjunto, tmp_path):
    r = CliRunner().invoke(cli, ["eval", "correr", conjunto, "--simulado", "--raiz",
                                 str(_copiar_evals(tmp_path))])
    assert r.exit_code == 0, r.output
    assert "APROBADO" in r.output


def _copiar_evals(tmp_path: Path) -> Path:
    import shutil

    destino = tmp_path / "evals"
    shutil.copytree(RAIZ / "evals", destino, ignore=shutil.ignore_patterns("resultados"))
    return destino


# --- T22: eval importar-correccion ----------------------------------------------------------------
CASO = {"entrada": {"perfil": {}, "preferencias": {}, "oferta": {"titulo": "Camarera"}},
        "esperado": {"nota": 35, "condiciones": "medio", "motivo": "El sueldo queda por debajo."},
        "modelo": {"nota": 80, "condiciones": "medio", "explicacion": "Encaja."}}


def test_importar_correccion_no_copia_nada_sin_confirmar(tmp_path):
    archivo = _json(tmp_path / "caso.json", CASO)
    raiz = tmp_path / "evals"
    (raiz / "recomendacion" / "casos").mkdir(parents=True)
    r = CliRunner().invoke(cli, ["eval", "importar-correccion", "--archivo", str(archivo),
                                 "--raiz", str(raiz)], input="n\n")
    assert r.exit_code == 1
    assert "35" in r.output and "80" in r.output  # enseña la nota corregida y la del modelo
    assert list((raiz / "recomendacion" / "casos").iterdir()) == []


def test_importar_correccion_confirmada_copia_entrada_y_esperado_y_no_repite(tmp_path):
    archivo = _json(tmp_path / "caso.json", CASO)
    raiz = tmp_path / "evals"
    casos = raiz / "recomendacion" / "casos"
    casos.mkdir(parents=True)
    (casos / "01-previo").mkdir()
    r = CliRunner().invoke(cli, ["eval", "importar-correccion", "--archivo", str(archivo),
                                 "--raiz", str(raiz)], input="s\n")
    assert r.exit_code == 0, r.output
    nuevo = casos / "02-correccion-camarera"
    assert json.loads((nuevo / "entrada.json").read_text(encoding="utf-8")) == CASO["entrada"]
    assert json.loads((nuevo / "esperado.json").read_text(encoding="utf-8")) == CASO["esperado"]
    otra = CliRunner().invoke(cli, ["eval", "importar-correccion", "--archivo", str(archivo),
                                    "--raiz", str(raiz)], input="s\n")
    assert otra.exit_code == 1 and len(list(casos.iterdir())) == 2


def test_importar_correccion_con_un_archivo_que_no_es_un_caso(tmp_path):
    archivo = _json(tmp_path / "caso.json", {"hola": 1})
    r = CliRunner().invoke(cli, ["eval", "importar-correccion", "--archivo", str(archivo),
                                 "--raiz", str(tmp_path)], input="s\n")
    assert r.exit_code == 2


# --- T22: /api/catalogo ---------------------------------------------------------------------------
@pytest.fixture
def api(motor_app, bd_limpia, tmp_path, monkeypatch):
    from test_f1_t10_t15_api_ingesta import IdentidadFalsa  # noqa: PLC0415

    monkeypatch.setenv("RUTA_ARCHIVOS", str(tmp_path / "archivos"))
    monkeypatch.setenv("HORMA_ADMINS", "google-admin")
    config.ajustes.cache_clear()
    with TestClient(crear_app(engine=motor_app, identidad=IdentidadFalsa()),
                    follow_redirects=False) as c:
        yield c
    config.ajustes.cache_clear()


@pytest.mark.bd
def test_catalogo_pide_clave_de_ingesta_y_no_lleva_datos_personales(api, motor_app):
    from test_f1_t10_t15_api_ingesta import bearer, crear_clave  # noqa: PLC0415

    with sesion_sistema(motor_app) as s:
        s.execute(text("insert into ofertas (texto_crudo, estado, titulo, sector, familia, nivel, "
                       "fantasma, fraude, salario_publicado) values ('t', 'procesada', 'Camarera', "
                       "'hosteleria_turismo', 'hosteleria_restauracion', 'junior', false, false, "
                       "false)"))
        s.execute(text("insert into ofertas (texto_crudo, estado, titulo) values ('x', 'pendiente', "
                       "'Sin procesar')"))
    assert api.get("/api/catalogo").status_code == 401
    clave = crear_clave(api, "ofertas")
    assert api.get("/api/catalogo", headers=bearer(clave)).status_code == 403
    r = api.get("/api/catalogo", headers=bearer(crear_clave(api, "ingesta")))
    assert r.status_code == 200
    ofertas = r.json()["ofertas"]
    assert [o["oferta"]["titulo"] for o in ofertas] == ["Camarera"]
    assert set(ofertas[0]) == {"oferta_id", "oferta"}


# --- T23: cierre -----------------------------------------------------------------------------------
def test_ci_corre_los_tres_sets_de_la_fase_2_en_simulado_y_con_modelo():
    ci = (RAIZ / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for conjunto in ("perfil", "cv-base", "recomendacion"):
        assert conjunto in ci.split("evals-reales:")[0].split("Evals en simulado")[1]
        assert conjunto in ci.split("evals-reales:")[1]


def test_compose_monta_el_volumen_de_archivos_y_env_example_lo_documenta():
    compose = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")
    assert "horma_archivos" in compose
    env = (RAIZ / ".env.example").read_text(encoding="utf-8")
    assert "RUTA_ARCHIVOS" in env


def test_el_readme_documenta_los_comandos_de_la_fase_2():
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    for comando in ("horma recomendar", "horma flujo correr perfilar", "horma eval importar-correccion",
                    "horma eval correr perfil", "horma eval correr cv-base",
                    "horma eval correr recomendacion"):
        assert comando in readme, comando


def test_el_contrato_de_independencia_incluye_los_agentes_nuevos():
    cfg = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    bloque = re.search(r"\[\[tool\.importlinter\.contracts\]\].*?independence.*?(?=\n\[\[|\Z)", cfg,
                       re.S).group(0)
    for agente in ("extractor_perfil", "clasificador_postulante", "generador_cv_base", "matcher"):
        assert f"horma.agents.{agente}" in bloque


def test_system_md_recoge_la_fase_2():
    system = (RAIZ / "specs" / "system.md").read_text(encoding="utf-8")
    for palabra in ("perfilar", "recomendar", "horma_archivos"):
        assert palabra in system
