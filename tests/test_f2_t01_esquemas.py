"""Fase 2 · T01: esquemas Perfil, Preferencias, Match y listas cerradas de filtros."""
import pytest
from pydantic import ValidationError

from horma.schemas import filtros
from horma.schemas.match import Match
from horma.schemas.perfil import (
    Experiencia,
    Formacion,
    IdiomaPerfil,
    OrigenDato,
    Perfil,
    PreguntaPendiente,
)
from horma.schemas.preferencias import Preferencias


def _origen(frag="Camarera en Bar Sol"):
    return OrigenDato(cv_id=1, fragmento=frag)


def test_listas_cerradas_de_filtros():
    assert "ES" in filtros.PAISES and "REMOTO" in filtros.PAISES
    assert "indefinido" in filtros.CONTRATOS and "freelance" in filtros.CONTRATOS
    assert "es" in filtros.IDIOMAS and "en" in filtros.IDIOMAS
    assert "otro" in filtros.CONTRATOS and "otro" in filtros.IDIOMAS


def test_origen_de_un_dato_del_cv_exige_cv_y_fragmento():
    OrigenDato(cv_id=3, fragmento="Máster en Marketing")
    with pytest.raises(ValidationError):
        OrigenDato(fuente="cv", fragmento="sin cv")
    with pytest.raises(ValidationError):
        OrigenDato(cv_id=1, fragmento="")


def test_origen_usuaria_no_necesita_cv():
    o = OrigenDato(fuente="usuaria", fragmento="Lo escribió ella")
    assert o.cv_id is None


def test_un_dato_sin_origen_no_entra_en_el_perfil():
    with pytest.raises(ValidationError):
        Experiencia(puesto="Camarera", empresa="Bar Sol", inicio="2020-01")  # sin origen
    with pytest.raises(ValidationError):
        Formacion(titulo="Grado", centro="UB")  # sin origen
    with pytest.raises(ValidationError):
        IdiomaPerfil(idioma="en", nivel="B2")  # sin origen


def test_perfil_completo_con_origen_en_cada_dato():
    p = Perfil(
        nombre="Ana Inventada",
        experiencias=[Experiencia(puesto="Camarera", empresa="Bar Sol", inicio="2020-01", fin="2022-06",
                                  origen=_origen())],
        formacion=[Formacion(titulo="FP Hostelería", centro="IES Mar", origen=_origen("FP Hostelería"))],
        idiomas=[IdiomaPerfil(idioma="en", nivel="B2", origen=_origen("Inglés B2"))],
        preguntas_pendientes=[PreguntaPendiente(campo="experiencias[0].fin", motivo="falta",
                                                pregunta="¿Hasta cuándo trabajaste en Bar Sol?")],
    )
    assert p.version == 1 and p.experiencias[0].origen.cv_id == 1
    assert p.preguntas_pendientes[0].motivo == "falta"


def test_el_perfil_no_admite_edad_ni_nacionalidad():
    for campo in ("edad", "fecha_nacimiento", "nacionalidad", "sexo", "estado_civil", "salud", "foto"):
        with pytest.raises(ValidationError):
            Perfil(nombre="Ana", **{campo: "x"})


def test_idioma_del_perfil_debe_estar_en_la_lista_cerrada():
    with pytest.raises(ValidationError):
        IdiomaPerfil(idioma="klingon", nivel="B1", origen=_origen())


def test_pregunta_pendiente_exige_motivo_conocido():
    with pytest.raises(ValidationError):
        PreguntaPendiente(campo="x", motivo="porque_si", pregunta="¿?")


def test_preferencias_por_defecto_no_filtran_y_rango_es_40_100():
    p = Preferencias()
    assert p.familias == [] and p.paises == [] and p.sueldo_minimo is None
    assert p.solo_remoto is False and p.solo_salario is False
    assert (p.rango_min, p.rango_max) == (40, 100)
    assert p.orden == "compatibles"


def test_preferencias_valida_listas_cerradas_y_rango():
    p = Preferencias(familias=["hosteleria_restauracion", "hosteleria_restauracion"], paises=["ES", "PT"],
                     contratos=["indefinido"], idiomas=["es"], sueldo_minimo=24000)
    assert p.familias == ["hosteleria_restauracion"]  # sin duplicados
    for malo in ({"paises": ["Narnia"]}, {"familias": ["astronauta"]}, {"contratos": ["esclavo"]},
                 {"sueldo_minimo": -1}, {"rango_min": 80, "rango_max": 50}, {"rango_max": 101},
                 {"orden": "al_azar"}):
        with pytest.raises(ValidationError):
            Preferencias(**malo)


def test_preferencias_lleva_el_origen_de_cada_grupo():
    p = Preferencias(origen={"familias": "cv", "sueldo_minimo": "usuaria"})
    assert p.origen["familias"] == "cv"
    with pytest.raises(ValidationError):
        Preferencias(origen={"familias": "adivinado"})


def test_match_valido():
    m = Match(oferta_id=7, nota=82, condiciones="medio",
              explicacion="Lleva tres años de camarera. La oferta pide experiencia en sala.",
              cita_perfil="Camarera en Bar Sol", cita_oferta="experiencia en sala")
    assert m.retirada is False


def test_match_rechaza_nota_fuera_de_rango_y_explicacion_mal_dimensionada():
    base = dict(oferta_id=1, condiciones="alto", cita_perfil="a", cita_oferta="b")
    ok = "Primera frase. Segunda frase."
    with pytest.raises(ValidationError):
        Match(nota=101, explicacion=ok, **base)
    with pytest.raises(ValidationError):
        Match(nota=-1, explicacion=ok, **base)
    with pytest.raises(ValidationError):
        Match(nota=50, explicacion="Una sola frase.", **base)
    with pytest.raises(ValidationError):
        Match(nota=50, explicacion="Una. Dos. Tres. Cuatro.", **base)
    with pytest.raises(ValidationError):
        Match(nota=50, explicacion=ok, **{**base, "condiciones": "regular"})


def test_match_retirado_no_necesita_explicacion():
    m = Match(oferta_id=1, nota=60, condiciones="bajo", explicacion="", cita_perfil="", cita_oferta="",
              retirada=True)
    assert m.retirada
