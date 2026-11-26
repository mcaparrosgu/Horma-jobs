"""Spec 012, T07 (RF-12.4c, D-061): la búsqueda por título casa también con otras formas del puesto."""
from horma.schemas.preferencias import Preferencias
from horma.tools.buscar_ofertas import buscar_ofertas
from horma.tools.normalizar_titulo import casa_con_puestos
from horma.tools.sinonimos_puestos import otras_formas


def test_la_tabla_da_las_otras_formas_en_cualquier_genero():
    assert "chef" in otras_formas("Cocinera")
    assert "waiter" in otras_formas("Camarero/a")
    assert otras_formas("Astronauta") == ["Astronauta"]


def test_las_del_modelo_se_suman_a_las_de_la_tabla():
    assert casa_con_puestos("Chef de partie", ["Cocinero"])
    assert not casa_con_puestos("Stylist", ["Peluquera"])
    assert casa_con_puestos("Stylist", ["Peluquera"], sinonimos={"Peluquera": ["Stylist"]})


def test_una_forma_generica_solo_cuenta_en_la_familia_del_perfil():
    familias = {"familia_perfil": "tecnologia_datos", "familia_oferta": "ventas_comercial"}
    assert not casa_con_puestos("Business Developer", ["Programador"], **familias)
    assert casa_con_puestos("Programador Java", ["Programador"], **familias)


def test_el_filtro_sql_busca_las_otras_formas_pero_no_amplia_los_excluidos():
    consulta = buscar_ofertas(Preferencias(puestos=["Cocinero"], excluidos=["Camarero"]))
    assert "% chef %" in consulta.parametros["puestos"]
    assert "% waiter %" not in consulta.parametros["excluidos"]
