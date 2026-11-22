"""Comprueba que una carta sigue la forma de RF-10.3g, solo con reglas (código puro, sin modelo).

Devuelve la lista de fallos en español (vacía si todo va bien): menos de una página, de 3 a 4 párrafos de
cuerpo, frases cortas, sin listas ni negritas y sin clichés de autoalabanza ni halagos a la empresa."""
import re

from horma.tools.verificar_trazabilidad import FORMULAS_CORTESIA, frases

MAX_PALABRAS = 330
MAX_PALABRAS_FRASE = 32
CLICHES = ("mejor carta de presentación", "gran motivación", "ganas de aprender", "apasionad", "proactiv",
           "empresa líder", "empresa de referencia", "es un honor", "perfil idóneo", "no dudaré",
           "me complace", "equipo de primer nivel", "me dirijo a ustedes", "quedo a su disposición")
_FIN_DE_FRASE = re.compile(r"(?<=[.!?])\s+")


def errores_estructura_carta(carta: str) -> list[str]:
    errores: list[str] = []
    formulas = {f.casefold() for f in FORMULAS_CORTESIA}
    parrafos = [p.strip() for p in re.split(r"\n\s*\n", carta.strip()) if p.strip()]
    cuerpo = [p for p in parrafos if p.casefold().strip(" .,") not in {f.strip(" .,") for f in formulas}]
    if len(carta.split()) > MAX_PALABRAS:
        errores.append(f"La carta pasa de {MAX_PALABRAS} palabras: debe caber en una página.")
    if not 3 <= len(cuerpo) <= 6:   # los saludos cuentan como un párrafo suelto
        errores.append(f"La carta tiene {len(cuerpo)} párrafos; debe tener de 3 a 4 de cuerpo.")
    for frase in (f for linea in frases(carta) for f in _FIN_DE_FRASE.split(linea)):
        if len(frase.split()) > MAX_PALABRAS_FRASE:
            errores.append(f"Frase demasiado larga: «{frase[:60]}…»")
    if (re.search(r"^\s*(?:[-*+•]|\d+[.)])\s", carta, re.MULTILINE) or "**" in carta
            or re.search(r"^#", carta, re.M)):
        errores.append("La carta no lleva listas, negritas ni encabezados: solo párrafos.")
    bajo = carta.casefold()
    errores += [f"Cliché: «{c}»." for c in CLICHES if c in bajo]
    return errores
