"""Fase 1 · T01: taxonomía y esquemas de oferta completa y de fuentes."""
import pytest
from pydantic import ValidationError

from horma.schemas import taxonomia
from horma.schemas.fuente import CalificacionFuente, Fuente
from horma.schemas.oferta import Auditoria, Oferta, OfertaExtraida
from horma.schemas.taxonomia import Taxonomia


def test_la_taxonomia_es_cerrada_y_tiene_valor_por_defecto():
    t = Taxonomia(sector="hosteleria_turismo", familia="hosteleria_restauracion", nivel="junior",
                  stack=["Excel", " sap "])
    assert t.stack == ["excel", "sap"]  # normalizado
    assert "otros" in taxonomia.SECTORES and "otros" in taxonomia.FAMILIAS
    assert "sin_especificar" in taxonomia.NIVELES
    with pytest.raises(ValidationError):
        Taxonomia(sector="astronautica", familia="otros", nivel="junior")


def test_auditoria_y_oferta_completa():
    a = Auditoria(fantasma=True, motivos_fantasma=["sin_fecha"], fraude=False,
                  salario_publicado=False, frase_pedir_salario="¿Cuál es la banda salarial?")
    o = Oferta(titulo="Camarera", auditoria=a,
               taxonomia=Taxonomia(sector="otros", familia="otros", nivel="sin_especificar"))
    assert isinstance(o, OfertaExtraida)
    assert o.recomendable is False  # fantasma → fuera de la recomendación (RF-1.9)
    with pytest.raises(ValidationError):
        Auditoria(fantasma=True, motivos_fantasma=["porque_si"], fraude=False,
                  salario_publicado=True)


def test_una_oferta_sin_salario_sigue_siendo_recomendable():
    a = Auditoria(fantasma=False, fraude=False, salario_publicado=False)
    o = Oferta(titulo="X", auditoria=a,
               taxonomia=Taxonomia(sector="otros", familia="otros", nivel="sin_especificar"))
    assert o.recomendable is True


def test_fuente_exige_https_y_nombre_simple():
    f = Fuente(nombre="arbeitnow", web="https://www.arbeitnow.com",
               url="https://www.arbeitnow.com/api/job-board-api", mapeo={"lista": "data"})
    assert f.metodo == "GET" and f.activa is False
    with pytest.raises(ValidationError):
        Fuente(nombre="x", web="https://x.test", url="http://x.test/api", mapeo={})
    with pytest.raises(ValidationError):
        Fuente(nombre="con espacios", web="https://x.test", url="https://x.test/api", mapeo={})


def test_fuente_valida_las_variables_de_clave():
    Fuente(nombre="adzuna", web="https://www.adzuna.es", url="https://api.adzuna.com/v1/api/jobs/es/search/1",
           variable_clave="ADZUNA_APP_ID,ADZUNA_APP_KEY", mapeo={})
    with pytest.raises(ValidationError):  # nunca un secreto de Horma
        Fuente(nombre="mala", web="https://x.test", url="https://x.test/api",
               variable_clave="ANTHROPIC_API_KEY", mapeo={})


def test_calificacion_de_fuente():
    c = CalificacionFuente(url="https://x.test", apta=False, excluida_por_regla=True,
                           motivos=["Excluida por regla: LinkedIn"])
    assert c.robots_permite is None and c.instrucciones_embebidas == []
