import pytest
from pydantic import ValidationError

from horma.schemas.oferta import OfertaExtraida, Salario
from horma.schemas.origen import Origen


def test_oferta_valida_con_campos_vacios():
    o = OfertaExtraida(titulo="Camarera", instrucciones_embebidas=[])
    assert o.empresa is None and o.salario is None and o.idiomas == []


def test_oferta_con_salario_y_url():
    o = OfertaExtraida(titulo="Dev", salario=Salario(minimo=20000, maximo=30000, moneda="EUR"),
                       url="https://ejemplo.test/1")
    assert o.salario.maximo == 30000


def test_oferta_rechaza_titulo_ausente_y_salario_incoherente():
    with pytest.raises(ValidationError):
        OfertaExtraida()
    with pytest.raises(ValidationError):
        Salario(minimo=30000, maximo=20000, moneda="EUR")


def test_origen_requiere_fragmento():
    assert Origen(entidad="oferta", entidad_id=1, campo="titulo", fragmento="Camarera").campo == "titulo"
    with pytest.raises(ValidationError):
        Origen(entidad="oferta", entidad_id=1, campo="titulo", fragmento="")
