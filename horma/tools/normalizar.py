"""Normaliza la respuesta de una fuente a ofertas en texto crudo (RF-1.2) y calcula huellas."""
import hashlib
import html
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser

MAX_TEXTO = 20000
# (campo del mapeo, etiqueta en el texto). El título va solo en la primera línea.
_CAMPOS = [("empresa", "Empresa"), ("ubicacion", "Ubicación"), ("contrato", "Contrato"),
           ("remoto", "Remoto"), ("salario", "Salario"), ("fecha", "Publicada"), ("url", "URL")]
_BLOQUES = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section",
            "article", "header", "footer", "table"}


class _Texto(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes: list[str] = []
        self._ignorar = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "template"):
            self._ignorar += 1
        elif tag in _BLOQUES:
            self.partes.append("\n")
        if tag == "li":
            self.partes.append("- ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template"):
            self._ignorar = max(0, self._ignorar - 1)
        elif tag in _BLOQUES:
            self.partes.append("\n")

    def handle_data(self, data):
        if not self._ignorar:
            self.partes.append(data)


def html_a_texto(contenido: str) -> str:
    p = _Texto()
    p.feed(contenido)
    p.close()
    lineas = (re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in "".join(p.partes).split("\n"))
    return "\n".join(ln for ln in lineas if ln)


def huella(texto: str) -> str:
    """Igual para dos textos que solo difieren en mayúsculas o espacios."""
    normal = re.sub(r"\s+", " ", texto.casefold()).strip()
    return hashlib.sha256(normal.encode("utf-8")).hexdigest()


def obtener(datos, ruta: str | None):
    """Valor en la ruta `a.b.0.c`; None si no existe."""
    if not ruta:
        return datos
    actual = datos
    for parte in ruta.split("."):
        if isinstance(actual, dict):
            actual = actual.get(parte)
        elif isinstance(actual, list) and parte.isdigit() and int(parte) < len(actual):
            actual = actual[int(parte)]
        else:
            return None
    return actual


def items(respuesta, mapeo: dict[str, str]) -> list[dict]:
    lista = obtener(respuesta, mapeo.get("lista"))
    return [x for x in lista if isinstance(x, dict)] if isinstance(lista, list) else []


def _como_texto(campo: str, valor) -> str | None:
    if valor is None or valor == "" or valor == []:
        return None
    if isinstance(valor, bool):
        return "sí" if valor else "no"
    if campo == "fecha" and isinstance(valor, int | float):
        return datetime.fromtimestamp(valor, tz=UTC).date().isoformat()
    if isinstance(valor, list):
        return ", ".join(str(x) for x in valor if x not in (None, ""))
    if isinstance(valor, dict):
        return None
    return html.unescape(str(valor)).strip()


@dataclass(frozen=True)
class OfertaNormalizada:
    texto: str
    id_externo: str
    url: str | None


def oferta_a_texto(item: dict, mapeo: dict[str, str]) -> OfertaNormalizada:
    titulo = _como_texto("titulo", obtener(item, mapeo.get("titulo"))) or "Oferta sin título"
    lineas = [titulo]
    for campo, etiqueta in _CAMPOS:
        if campo in mapeo and (valor := _como_texto(campo, obtener(item, mapeo[campo]))):
            lineas.append(f"{etiqueta}: {valor}")
    descripcion = obtener(item, mapeo.get("descripcion")) if "descripcion" in mapeo else None
    if isinstance(descripcion, str) and descripcion.strip():
        lineas += ["", html_a_texto(descripcion)]
    texto = "\n".join(lineas)[:MAX_TEXTO]
    id_bruto = obtener(item, mapeo["id"]) if "id" in mapeo else None
    url = _como_texto("url", obtener(item, mapeo["url"])) if "url" in mapeo else None
    return OfertaNormalizada(texto=texto, id_externo=str(id_bruto) if id_bruto else huella(texto),
                             url=url)
