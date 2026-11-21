"""Fase 9a, T03: esquemas de actividades, periodos cubiertos y puestos."""
import pytest
from pydantic import ValidationError

from horma.schemas.perfil import Actividad, OrigenDato, Perfil, PeriodoCubierto
from horma.schemas.preferencias import Preferencias, PuestoSugerido


def test_perfil_antiguo_se_lee_sin_las_listas_nuevas():
    p = Perfil.model_validate({"version": 3, "nombre": "Ana"})
    assert p.actividades == [] and p.periodos_cubiertos == []


def test_periodo_cubierto_solo_admite_fechas():
    assert PeriodoCubierto(inicio="2019-03", fin="2020").fin == "2020"
    with pytest.raises(ValidationError):
        PeriodoCubierto(inicio="baja por enfermedad", fin="2020")
    with pytest.raises(ValidationError):
        PeriodoCubierto(inicio="2019", fin="2020", motivo="x")


def test_actividad_exige_origen_y_prohibe_extras():
    o = OrigenDato(fuente="cv", cv_id=1, fragmento="Voluntariado")
    assert Actividad(descripcion="Voluntariado", inicio="2019", origen=o).fin is None
    with pytest.raises(ValidationError):
        Actividad(descripcion="x", origen=o, motivo="y")


def test_preferencias_sin_puestos_se_leen_vacias():
    p = Preferencias.model_validate({"familias": ["datos_ia"]})
    assert p.puestos == [] and p.puestos_sugeridos == [] and p.excluidos == []
    with pytest.raises(ValidationError):
        Preferencias(puestos_sugeridos=[{"titulo": "Data Analyst"}])
    assert PuestoSugerido(titulo="Data Analyst", dato="Analista").dato
