"""S8 · T63: «Valenciano» se conserva en el CV maestro y una oferta que lo pide casa con `ca`."""
from horma.schemas.oferta import OfertaExtraida
from horma.schemas.perfil import Perfil
from horma.tools.componer_cv_maestro import componer_cv_maestro
from horma.tools.normalizar_oferta import normalizar_oferta


def _perfil(fragmento: str, nivel: str) -> Perfil:
    return Perfil.model_validate({
        "nombre": "Ana Ferrer",
        "idiomas": [{"idioma": "ca", "nivel": nivel,
                     "origen": {"fuente": "usuaria", "fragmento": fragmento}}],
    })


def test_maestro_escribe_valenciano_si_el_cv_lo_dice():
    assert "Valenciano C1" in componer_cv_maestro(_perfil("Valenciano: C1", "C1"))
    assert "Catalán" not in componer_cv_maestro(_perfil("Valenciano: C1", "C1"))


def test_maestro_escribe_catalan_si_el_cv_dice_catalan():
    texto = componer_cv_maestro(_perfil("Catalán: B2", "B2"))
    assert "Catalán B2" in texto and "Valenciano" not in texto


def test_oferta_que_pide_valenciano_casa_con_ca():
    for pedido in ("Valenciano", "valencià C1", "Valenciano y castellano"):
        assert "ca" in normalizar_oferta(OfertaExtraida(titulo="P", idiomas=[pedido])).idiomas
