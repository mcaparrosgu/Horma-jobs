"""Spec 012 · T14o (RF-12.13, D-109): «la mejor, primera» solo frente a las que esperan más de 10 puntos
menos; los pares con 20 o más de diferencia esperada siguen sin poder salir al revés."""
from horma.evals import _bien_ordenadas


def test_la_mejor_no_tiene_que_separarse_de_las_que_esperan_10_puntos_menos_o_menos():
    assert _bien_ordenadas([90, 90, 40], [95, 92, 40])  # caso 46: empate
    assert _bien_ordenadas([88, 90, 40], [95, 92, 40])  # y al revés
    assert _bien_ordenadas([80, 82, 10], [90, 80, 10])  # 10 justos no es «más de 10»


def test_la_mejor_sigue_primera_frente_a_las_que_esperan_mas_de_10_menos():
    assert not _bien_ordenadas([84, 84], [95, 84])
    assert not _bien_ordenadas([80, 81], [90, 79])
    assert _bien_ordenadas([85, 84], [95, 84])


def test_un_par_a_20_o_mas_puntos_al_reves_sigue_fallando():
    assert not _bien_ordenadas([90, 50, 55], [90, 60, 40])
    assert _bien_ordenadas([90, 50, 50], [90, 60, 40])  # empatar no es salir al revés
