import dataclasses

import pytest
from pydantic import BaseModel

from horma.llm import completar, metricas
from horma.llm.gateway import SalidaInvalida
from horma.llm.simulado import ProveedorSimulado


class Entrada(BaseModel):
    texto: str


class Salida(BaseModel):
    titulo: str


@pytest.fixture(autouse=True)
def _limpiar():
    metricas.vaciar()
    yield
    metricas.vaciar()


def _run(prov, **kw):
    return completar(agente="prueba", prompt="Extrae.", entrada=Entrada(texto="hola"),
                     esquema_salida=Salida, modelo="pequeno", proveedor=prov,
                     dormir=lambda s: None, **kw)


def test_devuelve_salida_validada():
    prov = ProveedorSimulado([{"titulo": "Camarera"}])
    assert _run(prov) == Salida(titulo="Camarera")


def test_salida_corrupta_reintenta_una_vez_con_el_error():
    prov = ProveedorSimulado([{"mal": 1}, {"titulo": "ok"}])
    assert _run(prov).titulo == "ok"
    assert len(prov.llamadas) == 2
    assert "titulo" in prov.llamadas[1]["usuario"]  # el error de validación viaja en el reintento


def test_salida_corrupta_dos_veces_lanza_salida_invalida():
    prov = ProveedorSimulado([{"mal": 1}, {"mal": 2}])
    with pytest.raises(SalidaInvalida):
        _run(prov)
    assert [m.resultado for m in metricas.registradas()][-1] == "salida_invalida"


def test_error_transitorio_se_reintenta_con_retroceso():
    esperas = []
    prov = ProveedorSimulado([TimeoutError("lento"), {"titulo": "ok"}])
    r = completar(agente="p", prompt="x", entrada=Entrada(texto="a"), esquema_salida=Salida,
                  proveedor=prov, dormir=esperas.append)
    assert r.titulo == "ok" and len(esperas) == 1 and esperas[0] > 0


def test_metricas_sin_texto():
    prov = ProveedorSimulado([{"titulo": "Camarera"}])
    _run(prov)
    m = metricas.registradas()[-1]
    campos = {f.name for f in dataclasses.fields(m)}
    assert {"agente", "modelo", "tokens_entrada", "tokens_salida", "coste", "latencia_ms",
            "resultado"} <= campos
    assert not any("texto" in c or "prompt" in c or "salida" == c for c in campos)
    assert m.agente == "prueba" and m.resultado == "ok" and m.tokens_entrada > 0
