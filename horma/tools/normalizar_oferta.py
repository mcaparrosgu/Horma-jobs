"""Deduce de una oferta su país, tipo de contrato, idiomas y sueldo anual en euros (P16, P17).

Código puro, sin IA y sin coste. Sirve para que los filtros de la usuaria (casillas de país,
contrato e idioma y el sueldo mínimo) funcionen en la base de datos. Lo que no se puede deducir
queda en `None` o vacío: el filtro deja pasar esas ofertas (P2). En pantalla el sueldo se sigue
enseñando tal como lo dice la oferta; esto solo es para comparar (P17)."""
import re
import unicodedata

from horma.schemas.filtros import NormalizacionOferta
from horma.schemas.oferta import OfertaExtraida


def _plano(texto: str | None) -> str:
    """Minúsculas, sin tildes y con espacios simples."""
    t = unicodedata.normalize("NFD", texto or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").casefold()
    return re.sub(r"\s+", " ", t).strip()


def _regex(terminos: dict[str, str]) -> re.Pattern:
    claves = sorted(terminos, key=len, reverse=True)
    return re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(c) for c in claves) + r")(?![a-z0-9])")


# --- país --------------------------------------------------------------------------------------
_PAISES_TEXTO = {
    "ES": "españa spain spanien espagne madrid barcelona valencia sevilla bilbao malaga zaragoza alicante "
          "murcia palma granada vigo coruña tenerife ibiza mallorca pamplona valladolid cordoba "
          "san sebastian donostia santander gijon oviedo cadiz girona tarragona gran canaria",
    "PT": "portugal lisboa lisbon porto braga faro coimbra",
    "FR": "france francia frankreich paris lyon marseille toulouse bordeaux lille nantes strasbourg",
    "DE": "germany alemania deutschland allemagne berlin munich munchen hamburg frankfurt cologne koln "
          "stuttgart dusseldorf leipzig dresden hannover nuremberg nurnberg bremen",
    "IT": "italy italia italien italie roma rome milan milano torino turin napoli naples bologna florence "
          "firenze",
    "NL": "netherlands holanda nederland amsterdam rotterdam utrecht eindhoven",
    "BE": "belgium belgica belgien belgique brussels bruselas bruxelles antwerp",
    "LU": "luxembourg luxemburgo",
    "IE": "ireland irlanda dublin cork",
    "GB": "uk england scotland wales london londres manchester edinburgh birmingham",
    "AT": "austria osterreich vienna wien viena salzburg",
    "CH": "switzerland suiza schweiz zurich geneva ginebra basel bern",
    "DK": "denmark dinamarca danmark copenhagen copenhague aarhus",
    "SE": "sweden suecia sverige stockholm estocolmo gothenburg malmo",
    "NO": "norway noruega norge oslo bergen",
    "FI": "finland finlandia suomi helsinki",
    "IS": "iceland islandia reykjavik",
    "PL": "poland polonia polska warsaw varsovia krakow wroclaw",
    "CZ": "czechia chequia praga prague",
    "GR": "greece grecia athens atenas",
    "RO": "romania rumania bucharest bucarest",
    "HU": "hungary hungria budapest",
    "US": "usa california texas miami seattle boston chicago",
    "CA": "canada toronto vancouver montreal",
    "MX": "mexico cdmx",
    "AR": "argentina",
    "CO": "colombia bogota medellin",
    "CL": "chile",
    "PE": "peru",
    "BR": "brazil brasil",
}
_PAISES_FRASES = {
    "ES": ["gran canaria", "san sebastian"], "GB": ["united kingdom", "reino unido", "great britain"],
    "NL": ["paises bajos", "the hague"], "US": ["united states", "estados unidos", "new york",
                                                  "san francisco"],
    "MX": ["ciudad de mexico"], "AR": ["buenos aires"], "BR": ["sao paulo"], "CL": ["santiago de chile"],
    "PE": ["lima"],
}
_PAIS: dict[str, str] = {}
for _codigo, _lista in _PAISES_TEXTO.items():
    for _t in _lista.split():
        _PAIS[_plano(_t)] = _codigo
for _codigo, _lista in _PAISES_FRASES.items():
    for _t in _lista:
        _PAIS[_plano(_t)] = _codigo
_PAIS_RE = _regex(_PAIS)
_REMOTO_RE = re.compile(r"(?<![a-z0-9])(remote|remoto|teletrabajo|worldwide|anywhere|home ?office)"
                        r"(?![a-z0-9])")


def _pais(ubicacion: str | None, remoto: bool | None) -> str | None:
    texto = _plano(ubicacion)
    m = _PAIS_RE.search(texto)
    if m:
        return _PAIS[m.group(1)]
    if remoto or _REMOTO_RE.search(texto):
        return "REMOTO"
    return None


# --- contrato (en este orden de prioridad) -----------------------------------------------------
_CONTRATOS = [
    ("practicas", ["practicas", "internship", "praktikum", "stage", "becario", "becaria", "pasantia",
                   "werkstudent"]),
    ("freelance", ["freelance", "autonomo", "autonoma", "contractor", "honorarios", "self-employed",
                   "selbststandig"]),
    ("indefinido", ["indefinido", "permanent", "unbefristet", "cdi", "fijo", "open-ended"]),
    ("temporal", ["temporal", "temporary", "befristet", "cdd", "fixed-term", "fixed term", "determinado",
                  "obra y servicio", "seasonal", "de temporada"]),
    ("jornada_completa", ["jornada completa", "full-time", "full time", "vollzeit", "tiempo completo"]),
    ("media_jornada", ["media jornada", "part-time", "part time", "teilzeit", "tiempo parcial",
                       "jornada parcial"]),
]
_CONTRATO_RE = [(tipo, _regex({t: tipo for t in terminos})) for tipo, terminos in _CONTRATOS]


def _contrato(contrato: str | None) -> str | None:
    texto = _plano(contrato)
    if not texto:
        return None
    for tipo, patron in _CONTRATO_RE:
        if patron.search(texto):
            return tipo
    return "otro"


# --- idiomas -----------------------------------------------------------------------------------
_IDIOMAS_TEXTO = {
    "es": "español espanol spanish castellano spanisch espagnol",
    "en": "inglés ingles english englisch anglais",
    "fr": "francés frances french français francais französisch franzosisch",
    "de": "alemán aleman german deutsch allemand",
    "it": "italiano italian italienisch",
    "pt": "portugués portugues portuguese portugiesisch",
    "ca": "catalán catalan",
    "eu": "euskera vasco basque",
    "gl": "gallego galician",
    "nl": "neerlandés neerlandes holandés holandes dutch nederlands",
    "pl": "polaco polish polski",
    "ru": "ruso russian",
    "zh": "chino chinese mandarín mandarin",
    "ar": "árabe arabe arabic",
    "ro": "rumano romanian",
    "otro": "japonés japones japanese coreano korean turco turkish sueco swedish danés danes danish "
            "noruego norwegian finés fines finnish griego greek hindi ucraniano ukrainian",
}
_IDIOMA = {_plano(t): c for c, lista in _IDIOMAS_TEXTO.items() for t in lista.split()}
_IDIOMA_RE = _regex(_IDIOMA)


def _idiomas(idiomas: list[str]) -> list[str]:
    salida: list[str] = []
    for item in idiomas:
        for m in _IDIOMA_RE.finditer(_plano(item)):
            codigo = _IDIOMA[m.group(1)]
            if codigo not in salida:
                salida.append(codigo)
    return salida


# --- sueldo anual en euros ---------------------------------------------------------------------
_PERIODO_RE = re.compile(
    r"(?P<hora>/ ?h\b|/hora|por hora|la hora|hourly|per hour|/hour|stundenlohn|pro stunde|euros? ?/ ?h)"
    r"|(?P<mes>/ ?mes|al mes|por mes|mensual|per month|monthly|/month|pro monat|brutos? ?/ ?mes)"
    r"|(?P<ano>/ ?ano|al ano|por ano|anual|per year|annual|yearly|/year|p\.a\.|pro jahr)")
_EUROS = {"eur", "€", "euro", "euros"}
_MAX_MENSUAL = 6000  # por encima, sin pista en el texto, se entiende que es anual
_MIN_MENSUAL = 100  # por debajo, sin pista en el texto, se entiende que es por hora


def _periodo(texto: str) -> str | None:
    m = _PERIODO_RE.search(_plano(texto))
    return m.lastgroup if m else None


def _sueldo(oferta: OfertaExtraida, texto: str) -> tuple[float | None, float | None]:
    s = oferta.salario
    if s is None or (s.minimo is None and s.maximo is None):
        return None, None
    if _plano(s.moneda) not in _EUROS:
        return None, None
    periodo = _periodo(texto)
    if periodo is None:
        mayor = max(v for v in (s.minimo, s.maximo) if v is not None)
        periodo = "hora" if mayor < _MIN_MENSUAL else "mes" if mayor <= _MAX_MENSUAL else "ano"
    if periodo == "hora":
        return None, None
    factor = 12 if periodo == "mes" else 1
    return (s.minimo * factor if s.minimo is not None else None,
            s.maximo * factor if s.maximo is not None else None)


def normalizar_oferta(oferta: OfertaExtraida, texto: str = "") -> NormalizacionOferta:
    """`texto` es el texto crudo de la oferta: solo se usa para saber si el sueldo es mensual o anual."""
    minimo, maximo = _sueldo(oferta, texto)
    return NormalizacionOferta(
        pais=_pais(oferta.ubicacion, oferta.remoto),
        tipo_contrato=_contrato(oferta.contrato),
        idiomas=_idiomas(oferta.idiomas),
        salario_anual_eur_min=minimo,
        salario_anual_eur_max=maximo,
    )
