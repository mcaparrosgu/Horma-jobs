"""Fase 5 · prueba manual (18-nov): una tarea «en_curso» tras parar el worker vuelve a la cola.

Antes se quedaba en curso para siempre: «Regenerando…» sin fin y 409 «Ya se está regenerando»."""
# ruff: noqa: F401, F811  (fixtures importadas de otro módulo)
import pytest
from sqlalchemy import text
from test_f2_t13_t14_bd_worker import _encolar, _usuarias

from horma.web.db import sesion_de
from horma.web.queue import cola


def _estados(motor, u):
    with sesion_de(motor, u) as s:
        return [r.estado for r in s.execute(text("select estado from tareas order by id"))]


@pytest.mark.bd
def test_una_tarea_en_curso_al_arrancar_vuelve_a_pendiente(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    _encolar(motor_app, a, "regenerar_cv_base", 1)
    assert cola.reclamar(motor_app)["estado"] == "en_curso"  # el worker la tomó y se paró
    assert _estados(motor_app, a) == ["en_curso"]
    assert cola.reencolar_interrumpidas(motor_app) == 1
    assert _estados(motor_app, a) == ["pendiente"]
    assert cola.reclamar(motor_app)["id"]  # otro worker (o el mismo) puede retomarla


@pytest.mark.bd
def test_las_tareas_hechas_y_las_pendientes_no_se_tocan(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    _encolar(motor_app, a, "regenerar_cv_base", 1)
    _encolar(motor_app, a, "regenerar_cv_base", 2)
    with sesion_de(motor_app, a) as s:
        s.execute(text("update tareas set estado = 'hecha' where entidad_id = 1"))
    assert cola.reencolar_interrumpidas(motor_app) == 0
    assert _estados(motor_app, a) == ["hecha", "pendiente"]
