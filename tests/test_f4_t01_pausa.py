"""Fase 4 · T01: la interfaz Flow gana pausas y reanudar (RF-4.2, RT-12)."""
import pytest

from horma.flows.base import ErrorDePaso, Flow
from horma.flows.plain import PlainFlow


def _anotar(nombre):
    def paso(e):
        e.setdefault("visitados", []).append(nombre)
        return e
    return paso


def _flujo(pausas):
    pasos = {"a": _anotar("a"), "b": _anotar("b"), "entregar": _anotar("entregar")}
    return PlainFlow("prueba", pasos=pasos, aristas={"a": "b", "b": "entregar"}, inicio="a",
                     finales={"entregar"}, pausas=pausas)


def test_con_pausa_se_para_antes_del_paso_y_deja_en_pausa():
    f = _flujo({"entregar"})
    assert isinstance(f, Flow) and f.pausas == {"entregar"}
    e = f.run({})
    assert e["visitados"] == ["a", "b"] and e["en_pausa"] == "entregar"


def test_reanudar_aplica_los_cambios_y_termina():
    f = _flujo({"entregar"})
    e = f.reanudar("hilo-1", {"cv": "editado"}, estado=f.run({}))
    assert e["visitados"] == ["a", "b", "entregar"] and e["cv"] == "editado"
    assert e["en_pausa"] is None


def test_reanudar_en_un_flujo_sin_pausa_da_error():
    f = _flujo(set())
    with pytest.raises(ErrorDePaso):
        f.reanudar("hilo-1", {}, estado={"en_pausa": "entregar"})


def test_reanudar_sin_estado_en_pausa_da_error():
    f = _flujo({"entregar"})
    with pytest.raises(ErrorDePaso):
        f.reanudar("hilo-1", {}, estado={"visitados": []})
    with pytest.raises(ErrorDePaso):
        f.reanudar("hilo-1", {}, estado=None)


def test_sin_pausas_todo_sigue_igual():
    f = _flujo(set())
    assert f.pausas == set()
    e = f.run({}, hilo="x")
    assert e["visitados"] == ["a", "b", "entregar"] and "en_pausa" not in e


def test_pausar_en_un_paso_desconocido_se_rechaza_al_construir():
    with pytest.raises(ValueError):
        _flujo({"no_existe"})
