"""Fase 5 · T05: la pantalla del perfil muestra las secciones nuevas, su ayuda y el aviso (RF-5.1c/d).

La comprobación visual (editar un proyecto en la web) la hace Mar con el plan de pruebas."""
from pathlib import Path

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"


def test_la_pantalla_dice_que_lo_editado_manda_sobre_los_cv_subidos():
    html = (ESTATICOS / "perfil.html").read_text(encoding="utf-8")
    assert ("Lo que edites aquí manda sobre tus CV subidos y se usa para redactar todos tus CV "
            "y cartas") in html
    assert "nunca se modifican" in html


def test_las_tres_secciones_tienen_ayuda_con_los_ejemplos_de_la_spec_y_boton_de_anadir():
    js = (ESTATICOS / "perfil.js").read_text(encoding="utf-8")
    for clave in ("proyectos", "certificaciones", "otros"):
        assert f'["{clave}", ' in js and f"{clave}: [[" in js
    for ejemplo in ("Web de reservas para el restaurante familiar (2024)", "TFG: app de turnos",
                    "Manipulador de alimentos", "Carné de carretillero", "Cambridge B2 First",
                    "Voluntariado en el banco de alimentos", "Carné de conducir B",
                    "Disponibilidad para viajar"):
        assert ejemplo in js
    assert "botonAnadir" in js
