"""Fase 1 · T02: interfaz Flow y PlainFlow."""
import pytest

from horma.flows.base import ErrorDePaso, Flow
from horma.flows.plain import PlainFlow


def _sumar(n):
    def paso(e):
        e["total"] = e.get("total", 0) + n
        e.setdefault("visitados", []).append(n)
        return e
    return paso


def _flujo():
    pasos = {"a": _sumar(1), "b": _sumar(10), "c": _sumar(100), "fin": lambda e: e}
    aristas = {"a": "b", "b": lambda e: "c" if e["total"] < 20 else "fin", "c": "b"}
    return PlainFlow("prueba", pasos=pasos, aristas=aristas, inicio="a", finales={"fin"})


def test_plainflow_cumple_la_interfaz_y_recorre_las_aristas():
    f = _flujo()
    assert isinstance(f, Flow)
    e = f.run({})
    assert e["visitados"] == [1, 10, 100, 10]  # a → b → c → b → fin (arista condicional)
    assert f.pasos() == ["a", "b", "c", "fin"]


def test_run_step_ejecuta_un_solo_paso_y_siguiente_dice_el_proximo():
    f = _flujo()
    e = f.run_step("b", {"total": 0})
    assert e["total"] == 10
    assert f.siguiente("b", e) == "c"
    assert f.siguiente("fin", e) is None


def test_un_paso_que_falla_lanza_error_de_paso_con_su_nombre():
    def roto(e):
        raise ValueError("sin datos")
    f = PlainFlow("roto", pasos={"a": _sumar(1), "b": roto}, aristas={"a": "b"}, inicio="a",
                  finales={"b"})
    with pytest.raises(ErrorDePaso) as exc:
        f.run({})
    assert exc.value.paso == "b" and "sin datos" in str(exc.value)


def test_un_bucle_infinito_se_corta():
    f = PlainFlow("bucle", pasos={"a": _sumar(1)}, aristas={"a": "a"}, inicio="a", finales=set())
    with pytest.raises(ErrorDePaso):
        f.run({}, max_pasos=5)


def test_aristas_a_pasos_inexistentes_se_rechazan_al_construir():
    with pytest.raises(ValueError):
        PlainFlow("mal", pasos={"a": _sumar(1)}, aristas={"a": "no_existe"}, inicio="a",
                  finales=set())
