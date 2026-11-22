"""S8 · T64: «No consta» (RF-10.13) sin duplicados ni texto interno."""
from horma.flows.candidatura import combinar_huecos


def _h(requisito: str) -> dict:
    return {"requisito": requisito, "propuesta": "Añádelo si lo tienes."}


def test_el_mismo_requisito_con_otra_forma_sale_una_vez():
    huecos = combinar_huecos([_h("PMS (Opera, según la taxonomía de la oferta)")], ["pms"])
    assert [h["requisito"] for h in huecos] == ["PMS"]


def test_tildes_y_mayusculas_no_duplican():
    huecos = combinar_huecos([_h("Francés")], ["FRANCES"])
    assert len(huecos) == 1


def test_inclusion_no_duplica():
    huecos = combinar_huecos([_h("Carné de manipulador de alimentos")], ["manipulador de alimentos"])
    assert len(huecos) == 1


def test_ningun_hueco_lleva_texto_interno():
    huecos = combinar_huecos([_h("Excel (según la taxonomía)")], ["Sage"])
    assert all("taxonom" not in h["requisito"].lower() for h in huecos)
    assert [h["requisito"] for h in huecos] == ["Excel", "Sage"]


def test_huecos_distintos_se_conservan():
    assert len(combinar_huecos([_h("Francés")], ["Alemán", "Sage"])) == 3
