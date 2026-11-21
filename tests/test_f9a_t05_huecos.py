"""Fase 9a, T05: detectar_huecos."""
from datetime import date

from horma.schemas.perfil import Perfil
from horma.tools.detectar_huecos import detectar_huecos

HOY = date(2026, 11, 21)
ORIG = {"fuente": "usuaria", "fragmento": "x"}


def exp(ini, fin):
    return {"puesto": "P", "inicio": ini, "fin": fin, "origen": ORIG}


def perfil(**kw):
    return Perfil.model_validate(kw)


def test_ocho_meses_es_hueco_y_cuatro_no():
    p = perfil(experiencias=[exp("2018-01", "2019-02"), exp("2019-11", "actual")])
    (h,) = detectar_huecos(p, HOY)
    assert (h.inicio, h.fin, h.meses) == ("2019-03", "2019-10", 8)
    assert h.texto == "Entre marzo de 2019 y octubre de 2019 no consta trabajo ni formación."
    assert h.clave == "hueco:2019-03:2019-10"
    cuatro = perfil(experiencias=[exp("2018-01", "2019-02"), exp("2019-07", "actual")])
    assert detectar_huecos(cuatro, HOY) == []


def test_ano_suelto_no_inventa_huecos():
    p = perfil(experiencias=[exp("2018", "2018"), exp("2019", "actual")])
    assert detectar_huecos(p, HOY) == []


def test_solapados_se_funden():
    p = perfil(experiencias=[exp("2018-01", "2020-06"), exp("2019-01", "2019-12")],
               formacion=[{"titulo": "T", "inicio": "2020-07", "fin": "actual", "origen": ORIG}])
    assert detectar_huecos(p, HOY) == []


def test_actividad_y_periodo_cubierto_tapan_el_hueco():
    base = [exp("2018-01", "2019-02"), exp("2020-01", "actual")]
    assert len(detectar_huecos(perfil(experiencias=base), HOY)) == 1
    act = [{"descripcion": "Voluntariado", "inicio": "2019-03", "fin": "2019-12", "origen": ORIG}]
    assert detectar_huecos(perfil(experiencias=base, actividades=act), HOY) == []
    per = [{"inicio": "2019-03", "fin": "2019-12"}]
    assert detectar_huecos(perfil(experiencias=base, periodos_cubiertos=per), HOY) == []


def test_sin_fecha_de_inicio_no_cuenta_y_sin_nada_no_hay_huecos():
    p = perfil(experiencias=[exp(None, "2019"), exp("2018-01", "2019-02"), exp("2020-01", "actual")])
    assert len(detectar_huecos(p, HOY)) == 1
    assert detectar_huecos(perfil(), HOY) == []


def test_hueco_final_hasta_hoy():
    (h,) = detectar_huecos(perfil(experiencias=[exp("2020-01", "2026-03")]), HOY)
    assert (h.inicio, h.fin, h.meses) == ("2026-04", "2026-10", 7)
