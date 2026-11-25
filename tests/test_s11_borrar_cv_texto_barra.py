"""Spec 011 · borrar un CV rehace el perfil con los que quedan (RF-10.14):
la barra no dice «Estamos leyendo tu CV»."""
from pathlib import Path

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"


def test_tras_borrar_un_cv_la_barra_dice_que_actualiza_el_perfil():
    textos = (ESTATICOS / "textos.js").read_text(encoding="utf-8")
    perfil = (ESTATICOS / "perfil.js").read_text(encoding="utf-8")
    assert "Actualizando tu perfil con los CV que quedan" in textos
    assert "TEXTOS.actualizandoPerfil" in perfil and "rehaciendo" in perfil
