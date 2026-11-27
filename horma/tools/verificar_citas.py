"""¿Las citas de una explicación existen de verdad? (RF-12.19, S6). Código puro, sin IA.

Una cita vale si es un fragmento de un solo campo del perfil o de la oferta que recibió el modelo, sin
mirar mayúsculas, espacios, comillas ni la puntuación de los extremos. Del perfil no se puede citar el
nombre ni de dónde salió cada dato; de la oferta, ni las instrucciones embebidas ni la auditoría."""

_NO_CITABLES = {"nombre", "version", "origen", "genero_puestos", "taxonomia", "instrucciones_embebidas",
                "preguntas_pendientes"}
_NO_CITABLES_OFERTA = {"instrucciones_embebidas", "auditoria"}


def _textos(valor, fuera: set[str]) -> list[str]:
    if isinstance(valor, dict):
        return [t for k, v in valor.items() if k not in fuera for t in _textos(v, fuera)]
    if isinstance(valor, list):
        return [t for v in valor for t in _textos(v, fuera)]
    if valor is None or isinstance(valor, bool):
        return []
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return [str(valor)] if str(valor).strip() else []


def textos_perfil(perfil: dict) -> list[str]:
    return _textos(perfil, _NO_CITABLES)


def _plano(texto: str) -> str:
    return " ".join(texto.casefold().split()).strip(" «»\"'“”.,;:…")


def _existe(cita: str, fuentes: list[str]) -> bool:
    c = _plano(cita)
    if not c:  # sin cita solo vale si no había nada que citar (un perfil vacío)
        return not fuentes
    return any(c in _plano(f) for f in fuentes)


def citas_que_no_existen(cita_perfil: str, cita_oferta: str, perfil: dict, oferta: dict) -> list[str]:
    pares = (("cita_perfil", cita_perfil, textos_perfil(perfil)),
             ("cita_oferta", cita_oferta, _textos(oferta, _NO_CITABLES_OFERTA)))
    return [campo for campo, cita, fuentes in pares if not _existe(cita, fuentes)]
