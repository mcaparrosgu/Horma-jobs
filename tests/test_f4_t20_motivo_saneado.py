"""Fase 4 · T20: el motivo de error y el log no llevan texto de la usuaria; `LOG_LEVEL` se aplica
(RF-4.7c)."""
import logging

import pytest
from pydantic import BaseModel, ValidationError

from horma import config
from horma.flows.base import ErrorDePaso
from horma.llm.gateway import SalidaInvalida
from horma.llm.metricas import TopeSuperado
from horma.logs import configurar_logs, motivo_seguro

SECRETO = "Calle Falsa 123, teléfono 600112233"


class _M(BaseModel):
    nombre: int


def _validacion() -> ValidationError:
    with pytest.raises(ValidationError) as e:
        _M.model_validate({"nombre": SECRETO})
    return e.value


def test_error_de_paso_con_texto_de_la_usuaria_deja_solo_paso_y_tipo():
    causa = RuntimeError(f"fallo con {SECRETO}")
    m = motivo_seguro(ErrorDePaso("adaptar_cv", causa))
    assert m == "paso adaptar_cv: RuntimeError" and SECRETO not in m


def test_una_validacion_de_pydantic_no_vuelca_los_valores_de_entrada():
    err = _validacion()
    assert SECRETO in str(err)  # el mensaje original sí lo llevaría
    m = motivo_seguro(ErrorDePaso("perfilar", err))
    assert SECRETO not in m and "ValidationError" in m


def test_mensajes_fijos_del_codigo_se_conservan():
    m = motivo_seguro(ErrorDePaso("f", "este flujo no tiene pausas"))
    assert m == "paso f: este flujo no tiene pausas"
    m = motivo_seguro(ErrorDePaso("elegir", ValueError("la usuaria no tiene ningún CV base válido")))
    assert "CV base" in m


def test_tope_superado_y_salida_invalida_tienen_mensaje_propio():
    assert motivo_seguro(TopeSuperado(f"tope {SECRETO}")) == "tope de coste superado"
    m = motivo_seguro(SalidaInvalida(SECRETO))
    assert "formato" in m and SECRETO not in m
    assert motivo_seguro(ErrorDePaso("p", SalidaInvalida(SECRETO))) == f"paso p: {m}"
    assert motivo_seguro(ErrorDePaso("p", TopeSuperado(SECRETO))) == "paso p: tope de coste superado"


def test_excepcion_cualquiera_deja_solo_su_clase():
    assert motivo_seguro(KeyError(SECRETO)) == "KeyError"


@pytest.fixture
def nivel(monkeypatch):
    raiz = logging.getLogger()
    antes = raiz.level
    yield lambda v: (monkeypatch.setenv("LOG_LEVEL", v), config.ajustes.cache_clear(), configurar_logs())[-1]
    raiz.setLevel(antes)
    config.ajustes.cache_clear()


def test_log_level_warning_silencia_los_info(nivel, caplog):
    assert nivel("WARNING") == logging.WARNING
    assert not logging.getLogger("horma.worker").isEnabledFor(logging.INFO)
    assert logging.getLogger("horma.worker").isEnabledFor(logging.WARNING)


def test_log_level_info_y_valor_invalido(nivel):
    assert nivel("info") == logging.INFO
    assert nivel("ruidoso") == logging.INFO
