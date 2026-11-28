"""¿La oferta pide un nivel por encima o por debajo del perfil? (spec 012, RF-12.35 y 12.36). Código puro."""
_NIVELES = ("practicas", "junior", "intermedio", "senior", "direccion")


def _posiciones(oferta: str | None, perfil: str | None) -> tuple[int, int] | None:
    if oferta in _NIVELES and perfil in _NIVELES:  # «sin_especificar» no compara
        return _NIVELES.index(oferta), _NIVELES.index(perfil)
    return None


def por_encima(oferta: str | None, perfil: str | None) -> bool:
    p = _posiciones(oferta, perfil)
    return p is not None and p[0] > p[1]


def pide_menos(relacion: str | None, oferta: str | None, perfil: str | None) -> bool:
    """RF-12.36 (D-081): se avisa, no resta nota."""
    p = _posiciones(oferta, perfil)
    return relacion in ("mismo_puesto", "afin") and p is not None and p[0] < p[1]
