"""Comprueba con código lo que el `analizador_estilo` propone (RF-5.6b, RF-5.6c, RT-08, RT-09).

- Cada rasgo cuya cita no está literal en algún documento se quita (RT-08).
- Un rasgo cuyo texto o cita contiene un rasgo personal (edad, salud, familia…) se quita.
- Una guía que describe a la persona («es una persona tranquila», «su personalidad») se rechaza entera.
- Las instrucciones embebidas se conservan solo si están de verdad en algún documento (RT-07)."""
import re
import unicodedata

from horma.agents.analizador_estilo.schemas import DocumentoEstilo, SalidaAnalizadorEstilo
from horma.schemas.estilo import GuiaEstilo, RasgoEstilo
from horma.tools.rasgos_personales import rasgos_personales

_DESCRIBE_PERSONA = re.compile(
    r"\b(?:es|parece|resulta|se trata de|se muestra|suena a)\s+(?:una?\s+)?"
    r"(?:persona|mujer|hombre|chica|chico|joven|alguien|profesional)\b|"
    r"\b(?:personalidad|caracter|temperamento|forma de ser)\b|"
    r"\bpersona\s+(?:tranquil|segur|timid|extrovert|introvert|amabl|simpatic|seri|calid|cercan|metodic|"
    r"organizad|trabajador|responsable|optimist)", re.IGNORECASE)


class GuiaNoValida(Exception):
    """La guía describe a la persona o trae rasgos personales: no se guarda."""

    def __init__(self, motivos: list[str]):
        self.motivos = motivos
        super().__init__("; ".join(motivos))


def _plano(texto: str) -> str:
    t = unicodedata.normalize("NFKC", texto).casefold()
    return re.sub(r"\s+", " ", t).strip()


def _sin_acentos(texto: str) -> str:
    t = unicodedata.normalize("NFD", texto)
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _describe_persona(texto: str) -> bool:
    return bool(_DESCRIBE_PERSONA.search(_sin_acentos(texto)))


def _rasgos_validos(rasgos: list[RasgoEstilo], textos: list[str]) -> list[RasgoEstilo]:
    validos = []
    for r in rasgos:
        cita = _plano(r.cita)
        if not cita or not any(cita in t for t in textos):
            continue
        if rasgos_personales(r.rasgo) or rasgos_personales(r.cita):
            continue
        validos.append(r)
    return validos


def motivos_de_rechazo(guia: GuiaEstilo) -> list[str]:
    """Por qué una guía no se puede guardar (también la que edita ella): describe a la persona o trae
    rasgos personales. Vacío si está bien."""
    propio = " ".join([guia.vinetas, *(r.rasgo for r in guia.expresiones), *(r.rasgo for r in guia.evita)])
    motivos = []
    if _describe_persona(propio):
        motivos.append("la guía describe a la persona en lugar de cómo escribe")
    personales = rasgos_personales(propio)
    if personales:
        motivos.append(f"la guía trae rasgos personales ({', '.join(personales)})")
    return motivos


def depurar_guia(salida: SalidaAnalizadorEstilo, documentos: list[DocumentoEstilo],
                 ) -> tuple[GuiaEstilo, list[str]]:
    """Devuelve la guía depurada y las instrucciones embebidas que sí están en los documentos.
    Lanza `GuiaNoValida` si la guía describe a la persona o trae rasgos personales."""
    textos = [_plano(d.texto) for d in documentos]
    guia = salida.guia
    if motivos := motivos_de_rechazo(guia):
        raise GuiaNoValida(motivos)
    depurada = guia.model_copy(update={
        "expresiones": _rasgos_validos(guia.expresiones, textos),
        "evita": _rasgos_validos(guia.evita, textos)})
    instrucciones = [i for i in dict.fromkeys(salida.instrucciones_embebidas)
                     if any(_plano(i) in t for t in textos)]
    return depurada, instrucciones
