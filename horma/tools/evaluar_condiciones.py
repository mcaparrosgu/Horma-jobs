"""Cuánto se parecen las condiciones de una oferta a las que busca la usuaria (RF-2.12).

Código puro, sin IA y sin coste. Solo se miran las condiciones que ella ha marcado: contrato, país,
remoto, sueldo mínimo, idiomas y «solo con salario publicado». Cada una sale «cumple», «no cumple» o
«sin dato» (la oferta no lo dice, o no se puede comparar):

- `bajo`: alguna condición marcada no se cumple.
- `medio`: ninguna falla, pero de alguna no hay dato (p. ej. pide sueldo mínimo y la oferta no lo publica).
- `alto`: todas las marcadas se cumplen, o no ha marcado ninguna.

`faltas` dice con palabras cuáles no cumple o no dice, para enseñarlas junto al veredicto (spec 012,
RF-12.25, D-120). Ninguna de las dos toca la nota."""
from typing import Literal

from horma.schemas.oferta import Oferta
from horma.schemas.preferencias import Preferencias
from horma.tools.normalizar_oferta import normalizar_oferta, por_hora

Nivel = Literal["bajo", "medio", "alto"]


_CONTRATOS = {"indefinido": "Contrato indefinido", "temporal": "Contrato temporal",
              "jornada_completa": "Jornada completa", "media_jornada": "Media jornada",
              "practicas": "Contrato en prácticas", "freelance": "Contrato de autónomo",
              "otro": "Otro tipo de contrato"}
_EN_PAIS = {
    "ES": "España", "PT": "Portugal", "FR": "Francia", "DE": "Alemania", "IT": "Italia", "NL": "Países Bajos",
    "BE": "Bélgica", "LU": "Luxemburgo", "IE": "Irlanda", "GB": "Reino Unido", "AT": "Austria", "CH": "Suiza",
    "DK": "Dinamarca", "SE": "Suecia", "NO": "Noruega", "FI": "Finlandia", "IS": "Islandia", "PL": "Polonia",
    "CZ": "Chequia", "SK": "Eslovaquia", "HU": "Hungría", "RO": "Rumanía", "BG": "Bulgaria", "GR": "Grecia",
    "HR": "Croacia", "SI": "Eslovenia", "EE": "Estonia", "LV": "Letonia", "LT": "Lituania", "MT": "Malta",
    "CY": "Chipre", "US": "Estados Unidos", "CA": "Canadá", "MX": "México", "AR": "Argentina",
    "CO": "Colombia", "CL": "Chile", "PE": "Perú", "UY": "Uruguay", "BR": "Brasil", "OTRO": "otro país"}
_IDIOMAS = {"es": "español", "en": "inglés", "fr": "francés", "de": "alemán", "it": "italiano",
            "pt": "portugués", "ca": "catalán", "eu": "euskera", "gl": "gallego", "nl": "neerlandés",
            "pl": "polaco", "ru": "ruso", "zh": "chino", "ar": "árabe", "ro": "rumano", "otro": "otro idioma"}


def _y(nombres: list[str]) -> str:
    return nombres[0] if len(nombres) == 1 else f"{', '.join(nombres[:-1])} y {nombres[-1]}"


def _sueldo_escrito(oferta: Oferta, frase: str) -> str:
    s = oferta.salario
    cifras = "–".join(f"{v:g}" for v in dict.fromkeys((s.minimo, s.maximo)) if v is not None)
    return " ".join(x for x in (cifras, s.moneda, "por hora" if por_hora(frase) else None) if x)


def _comprobar(oferta: Oferta, prefs: Preferencias, frase: str = "") -> list[tuple[bool | None, str]]:
    """Por cada condición marcada: (True cumple · False no cumple · None sin dato, texto si no cumple)."""
    n = normalizar_oferta(oferta, frase)
    r: list[tuple[bool | None, str]] = []

    if prefs.contratos:
        if n.tipo_contrato is None:
            r.append((None, "No dice el contrato"))
        else:
            r.append((n.tipo_contrato in prefs.contratos, _CONTRATOS[n.tipo_contrato]))
    if prefs.paises:
        if n.pais in (None, "REMOTO"):
            r.append((None, "No dice el país"))
        else:
            r.append((n.pais in prefs.paises, f"En {_EN_PAIS[n.pais]}"))
    if prefs.idiomas:
        if not n.idiomas:
            r.append((None, "No dice el idioma"))
        else:
            pide = f"Pide {_y([_IDIOMAS[i] for i in n.idiomas])}"
            r.append((bool(set(n.idiomas) & set(prefs.idiomas)), pide))
    if prefs.solo_remoto:
        texto = "No dice si es remoto" if oferta.modalidad is None else "No es remoto"
        r.append((oferta.modalidad == "remoto", texto))
    if prefs.sueldo_minimo is not None:
        maximo = n.salario_anual_eur_max
        if maximo is None:
            s = oferta.salario
            dicho = s is not None and (s.minimo is not None or s.maximo is not None)
            r.append((None, f"Sueldo que no se puede comparar: {_sueldo_escrito(oferta, frase)}" if dicho
                      else "No dice el sueldo"))
        else:
            r.append((maximo >= prefs.sueldo_minimo, "El sueldo es inferior a tu mínimo"))
    if prefs.solo_salario:
        r.append((oferta.auditoria.salario_publicado, "No dice el sueldo"))
    return r


def evaluar_condiciones(oferta: Oferta, prefs: Preferencias) -> Nivel:
    resultados = [cumple for cumple, _ in _comprobar(oferta, prefs)]
    if any(c is False for c in resultados):
        return "bajo"
    return "medio" if any(c is None for c in resultados) else "alto"


def faltas(oferta: Oferta, prefs: Preferencias, frase_sueldo: str = "") -> list[str]:
    """`frase_sueldo` es la línea del anuncio con el sueldo: dice si es por hora o al mes."""
    comprobadas = _comprobar(oferta, prefs, frase_sueldo)
    return list(dict.fromkeys(texto for cumple, texto in comprobadas if cumple is not True))
