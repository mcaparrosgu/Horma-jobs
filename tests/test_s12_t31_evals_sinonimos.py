"""Spec 012 · T31: set de evals de `sinonimos-puestos` (RF-12.4e, D-068 y D-071), en simulado."""
import json
import shutil
from pathlib import Path

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
    assert _json(EVALS / "umbrales.json")[SET]["metricas"] == {"otros": 0, "cobertura": 0.55}  # D-071


def test_una_forma_que_sea_otro_puesto_hace_fallar_el_set(tmp_path):
    ajeno = next(e for x, e in _casos().values() if x["puesto"] == "Sales Manager")["otros_puestos"][0]
    r = _correr(tmp_path, "Sales Manager", [ajeno])  # un anuncio que Mar marcó como otro puesto
    assert r["metricas"]["otros"] == 1 and not r["aprobado"]
    assert r["detalle"][0]["fallos"] == ["otro_puesto"]


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
    ci = (RAIZ / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert f"horma eval correr {SET} --simulado" in ci
