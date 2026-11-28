"""Spec 012 · T14k (RF-12.12 y 12.35, D-100): volver a puntuar en código lo grabado de `recomendacion`, sin
llamar al modelo, y juntar varias ejecuciones como pasadas seguidas."""
import copy
import json
import shutil
from pathlib import Path

from test_s12_t11_harness_nota import APOYADA, ORDEN, UNA, _matches
from typer.testing import CliRunner

from horma.cli import app as cli
from horma.evals import correr_set
from horma.llm.simulado import ProveedorSimulado

RAIZ = Path(__file__).resolve().parent.parent / "evals"
TODO_SI = [{"requisito": 1, "tipo": "exigido", "cubierto": "si"},
           {"requisito": 2, "tipo": "exigido", "cubierto": "si"}]


def _raiz(tmp_path: Path) -> Path:
    for caso in (UNA, ORDEN):
        shutil.copytree(RAIZ / "recomendacion" / "casos" / caso, tmp_path / "recomendacion" / "casos" / caso)
    return tmp_path


def _una_pasada(n_una: int = 90) -> list[dict]:
    """Respuestas de una pasada de los dos casos, en el orden en que se piden (`UNA` y después `ORDEN`)."""
    return [_matches(UNA, [n_una]), APOYADA, _matches(ORDEN), *[APOYADA] * 5]


def _correr(raiz: Path, veces: int, respuestas: list[dict]) -> dict:
    por_caso = {UNA: [], ORDEN: []}
    for i in range(veces):  # el harness corre todas las pasadas de un caso antes del siguiente
        por_caso[UNA] += respuestas[i][:2]
        por_caso[ORDEN] += respuestas[i][2:]
    prov = ProveedorSimulado(por_caso[UNA] + por_caso[ORDEN])
    return correr_set("recomendacion", raiz=raiz, proveedor=prov, veces=veces)


def _notas(r: dict) -> list:
    return [[o.get("nota") for o in s.get("ofertas") or [s]] for d in r["detalle"] for s in d["salidas"]]


def test_con_el_codigo_de_hoy_da_lo_mismo_sin_llamar_al_modelo(tmp_path):
    raiz = _raiz(tmp_path)
    vivo = _correr(raiz, 1, [_una_pasada()])
    otra = correr_set("recomendacion", raiz=raiz, grabado=[vivo])
    assert otra["campos"] == vivo["campos"] and otra["aprobado"] == vivo["aprobado"]
    assert _notas(otra) == _notas(vivo) and otra["coste"] == 0.0


def test_vuelve_a_acotar_desde_la_nota_del_modelo(tmp_path):
    raiz = _raiz(tmp_path)
    vivo = _correr(raiz, 1, [[_matches(UNA, [60], marcas=TODO_SI, relacion="mismo_puesto"), APOYADA,
                              _matches(ORDEN), *[APOYADA] * 5]])
    [[una]] = [vivo["detalle"][0]["salidas"]]
    assert (una["nota_modelo"], una["nota"]) == (60, 90)  # regla 1
    viejo = copy.deepcopy(vivo)
    viejo["detalle"][0]["salidas"][0]["nota"] = 12  # lo que daba otro código
    otra = correr_set("recomendacion", raiz=raiz, grabado=[viejo])
    [[una]] = [otra["detalle"][0]["salidas"]]
    assert una["nota"] == 90 and una["explicacion"].startswith("Te la recomendamos por esto.")


def test_junta_dos_ejecuciones_como_tres_pasadas_seguidas(tmp_path):
    raiz = _raiz(tmp_path)
    primera = _correr(raiz, 1, [_una_pasada(90)])
    resto = _correr(raiz, 2, [_una_pasada(85), _una_pasada(60)])
    r = correr_set("recomendacion", raiz=raiz, grabado=[primera, resto])
    assert [p["nota"] for p in r["pasadas"]] == [1.0, 1.0, 0.0] and not r["aprobado"]  # manda la peor
    assert r["detalle"][0]["notas"] == [[90], [85], [60]] and r["detalle"][0]["variacion"] == 30
    assert r["grabado"] == [primera["fecha"], resto["fecha"]]


def test_manda_el_peor_control_del_revisor_grabado(tmp_path):
    raiz = _raiz(tmp_path)
    vivo = _correr(raiz, 1, [_una_pasada()])
    assert vivo["aprobado"]
    otra = correr_set("recomendacion", raiz=raiz, grabado=[vivo, {**vivo, "control_revisor": 0.5}])
    assert otra["control_revisor"] == 0.5 and not otra["aprobado"]


def test_un_caso_sin_salidas_grabadas_falla_entero(tmp_path):
    raiz = _raiz(tmp_path)
    vivo = _correr(raiz, 1, [_una_pasada()])
    del vivo["detalle"][1]["salidas"]
    r = correr_set("recomendacion", raiz=raiz, grabado=[vivo])
    assert "error" in r["detalle"][1] and not r["aprobado"]


def test_la_consola_repuntua_uno_o_varios_resultados(tmp_path):
    raiz = _raiz(tmp_path)
    archivos = []
    for i, veces in enumerate((1, 2)):
        r = _correr(raiz, veces, [_una_pasada()] * veces)
        archivos.append(tmp_path / f"r{i}.json")
        archivos[-1].write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    salida = CliRunner().invoke(cli, ["eval", "repuntuar", *map(str, archivos), "--raiz", str(raiz)])
    assert salida.exit_code == 0, salida.output
    assert "pasada 3: nota 1.00 · orden 1.00" in salida.output and "APROBADO" in salida.output
    assert "sin llamar al modelo" in salida.output
