"""Descarga de páginas públicas (condiciones de uso, robots.txt) para calificar fuentes."""
import re
from collections.abc import Callable
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

from horma.tools.validar_url import Resolvedor, validar_url

Descargador = Callable[[str], str]
MAX_BYTES = 2_000_000
# ASCII: las cabeceras HTTP no admiten tildes.
AGENTE_HTTP = "HormaBot/0.1 (calificacion de fuentes de empleo)"

# Por prioridad: primero las condiciones de uso; el aviso legal o el Impressum, como último recurso.
_PATRONES = [
    re.compile(r"t[ée]rminos|condiciones|terms|tos\b|nutzungsbedingungen|\bagb\b|conditions", re.I),
    re.compile(r"aviso[ -]?legal|legal|impressum", re.I),
]


class NoEncontrada(Exception):
    """La página respondió 404 o 410."""


class Prohibida(Exception):
    """La página respondió 403: el portal no deja el acceso automático."""


def descargar_http(url: str, timeout: float = 15.0) -> str:
    with httpx.Client(follow_redirects=True, timeout=timeout,
                      headers={"User-Agent": AGENTE_HTTP}) as c, c.stream("GET", url) as r:
        if r.status_code in (404, 410):
            raise NoEncontrada(url)
        if r.status_code == 403:
            raise Prohibida(url)
        r.raise_for_status()
        cuerpo = b""
        for trozo in r.iter_bytes():
            cuerpo += trozo
            if len(cuerpo) > MAX_BYTES:
                break
        return cuerpo[:MAX_BYTES].decode(r.encoding or "utf-8", errors="replace")


_REDIRECCIONES = {301, 302, 303, 307, 308}


def seguir_redireccion(url: str, *, timeout: float = 8.0, max_saltos: int = 5,
                       transporte: httpx.BaseTransport | None = None,
                       resolver: Resolvedor | None = None) -> str:
    """La dirección final de un enlace. Solo `GET`, sin leer el cuerpo y con un máximo de saltos.
    Cada salto se valida antes de pedirlo (https, dominio público, portal no vetado): si no pasa, se
    devuelve esa dirección sin tocarla."""
    actual = url
    with httpx.Client(follow_redirects=False, timeout=timeout, transport=transporte,
                      headers={"User-Agent": AGENTE_HTTP}) as c:
        for _ in range(max_saltos):
            if validar_url(actual, resolver) is not None:
                return actual
            with c.stream("GET", actual) as r:
                destino = r.headers.get("location")
                if r.status_code not in _REDIRECCIONES or not destino:
                    return actual
            actual = urljoin(actual, destino)
    return actual


class _Enlaces(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.enlaces: list[tuple[str, str]] = []
        self._href: str | None = None
        self._texto: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._texto = []

    def handle_data(self, data):
        if self._href is not None:
            self._texto.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.enlaces.append((self._href, "".join(self._texto).strip()))
            self._href = None


def enlace_condiciones(html: str, base: str) -> str | None:
    """El enlace más probable a las condiciones de uso del portal, en el mismo dominio."""
    p = _Enlaces()
    p.feed(html)
    host = urlsplit(base).hostname
    for patron in _PATRONES:
        for href, texto in p.enlaces:
            absoluto = urljoin(base, href)
            if urlsplit(absoluto).hostname != host or not absoluto.startswith("https://"):
                continue
            if patron.search(texto) or patron.search(urlsplit(absoluto).path):
                return absoluto
    return None


def url_robots(url: str) -> str:
    partes = urlsplit(url)
    return f"{partes.scheme}://{partes.netloc}/robots.txt"
