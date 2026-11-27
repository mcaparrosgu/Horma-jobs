"""Spec 012 · T31: set de evals de `sinonimos-puestos` (RF-12.4e, D-068 y D-071), en simulado."""
import json
import shutil
from pathlib import Path

from horma import evals_sinonimos
from horma.agents.sinonimos_puestos.agent import SinonimosPuestos
from horma.evals import correr_set
from horma.llm.simulado import ProveedorSimulado

RAIZ = Path(__file__).resolve().parent.parent
EVALS = RAIZ / "evals"
SET = "sinonimos-puestos"


def _json(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def _casos() -> dict[str, tuple[dict, dict]]:
    return {c.name: (_json(c / "entrada.json"), _json(c / "esperado.json"))
            for c in sorted((EVALS / SET / "casos").iterdir())}


def _raiz(tmp_path: Path, puesto: str) -> Path:
    for nombre, (entrada, _) in _casos().items():
        if entrada["puesto"] == puesto:
            shutil.copytree(EVALS / SET / "casos" / nombre, tmp_path / SET / "casos" / nombre)
    return tmp_path


def _correr(tmp_path, puesto, formas):
    prov = ProveedorSimulado([{"puestos": [{"puesto": puesto, "otras": formas}]}])
    return correr_set(SET, raiz=_raiz(tmp_path, puesto), proveedor=prov)


def test_el_set_tiene_unos_40_puestos_con_titulos_firmados_por_mar():
    casos = _casos()
    firmados = {(p["puesto"], p["titulo"]): p["casa"]
                for p in _json(RAIZ / "tests" / "fixtures" / "titulos_puestos.json")["pares"]}
    assert len(casos) >= 30
    for nombre, (entrada, esperado) in casos.items():
        assert esperado["titulos"], nombre
        for titulo in esperado["titulos"]:
            assert firmados[(entrada["puesto"], titulo)] is True, nombre
        for titulo in esperado["otros_puestos"]:
            assert firmados[(entrada["puesto"], titulo)] is False, nombre


def test_los_umbrales_son_los_de_mar():
    assert _json(EVALS / "umbrales.json")[SET]["metricas"] == {"ajenas": 0.05, "cobertura": 0.6}  # D-076


def test_una_forma_que_sea_otro_puesto_hace_fallar_el_set(tmp_path):
    ajeno = next(e for x, e in _casos().values() if x["puesto"] == "Sales Manager")["otros_puestos"][0]
    r = _correr(tmp_path, "Sales Manager", [ajeno])  # un anuncio que Mar marcó como otro puesto
    assert r["metricas"]["otros"] == 1 and r["metricas"]["ajenas"] == 1.0 and not r["aprobado"]
    assert r["detalle"][0]["fallos"] == ["otro_puesto"]


def test_se_toleran_hasta_5_de_cada_100_formas_ajenas():
    umbrales = _json(EVALS / "umbrales.json")[SET]["metricas"]
    base = {"cobertura": 0.6, "sin_etiquetar": []}
    assert evals_sinonimos.cumple({**base, "ajenas": 0.05}, umbrales)
    assert not evals_sinonimos.cumple({**base, "ajenas": 0.0501}, umbrales)


def test_una_forma_sin_etiqueta_no_deja_aprobar(tmp_path):
    r = _correr(tmp_path, "Camarero", ["Waiter", "Sumiller"])
    assert r["metricas"]["sin_etiquetar"] == [f"{r['detalle'][0]['caso']}: Sumiller"] and not r["aprobado"]
    assert r["detalle"][0]["fallos"] == ["etiquetado"]


def test_la_cobertura_cuenta_los_titulos_que_encuentran_las_formas_del_modelo(tmp_path):
    r = _correr(tmp_path / "si", "Camarero", ["Waiter"])
    assert r["metricas"]["cobertura"] == 1.0 and r["aprobado"]
    # Sin ninguna forma no encuentra «Waiter»: la tabla fija no cuenta, se mide solo el modelo.
    r = _correr(tmp_path / "no", "Camarero", [])
    assert r["metricas"]["cobertura"] == 0.0 and not r["aprobado"]


def test_el_set_simulado_entero_aprueba_y_la_ci_lo_corre_sin_gasto(tmp_path):
    shutil.copytree(EVALS / SET, tmp_path / SET)
    r = correr_set(SET, raiz=tmp_path, simulado=True)
    assert r["aprobado"] and r["coste"] == 0 and r["metricas"]["cobertura"] == 1.0


def test_las_respuestas_grabadas_aprueban_y_la_ci_las_repite_sin_gasto(tmp_path):
    shutil.copytree(EVALS / SET, tmp_path / SET)
    r = correr_set(SET, raiz=tmp_path, grabadas=True)
    assert r["aprobado"] and r["coste"] == 0 and r["metricas"]["ajenas"] <= 0.05
    ci = (RAIZ / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert f"horma eval correr {SET} --grabadas" in ci


def test_el_prompt_prohibe_otro_escalon_y_las_palabras_sueltas_ambiguas():
    p = " ".join(SinonimosPuestos.prompt().split())  # D-072, D-073 y D-075
    assert "En los oficios, otro escalón es otro puesto" in p
    assert "En dirección y ventas" in p
    assert "una sola palabra" in p and "otro oficio" in p
    assert "parecido" in p
