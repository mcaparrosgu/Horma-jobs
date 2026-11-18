"""¿Se puede leer esta URL? Solo https, dominio público y portal no vetado (RF-5.3g, RF-5.3h)."""
import ipaddress
import json
import re
import socket
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

Resolvedor = Callable[[str], list[str]]

_VETADOS = Path(__file__).resolve().parent.parent / "assets" / "portales_vetados.json"
_NUMERICO = re.compile(r"^[0-9a-fx.]+$", re.IGNORECASE)  # 2130706433, 0x7f.1, 127.1…
_LOCALES = (".local", ".localhost", ".internal", ".lan", ".home", ".intranet")
PEGAR = "Pega el texto de la oferta."


@lru_cache(maxsize=1)
def _vetados_cache() -> dict[str, str]:
    datos = json.loads(_VETADOS.read_text(encoding="utf-8"))
    return {d: nombre for nombre, dominios in datos.items() for d in dominios}


def _vetados() -> dict[str, str]:
    """Dominio vetado → nombre del portal. Se lee de `horma/assets/portales_vetados.json`."""
    return _vetados_cache()


def _resolver(host: str) -> list[str]:
    return sorted({i[4][0] for i in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)})


def _es_publica(ip: str) -> bool:
    return ipaddress.ip_address(ip.split("%")[0]).is_global


def validar_url(url: str, resolver: Resolvedor | None = None) -> str | None:
    """None si la URL se puede leer; si no, el motivo en llano para la usuaria."""
    try:
        partes = urlsplit((url or "").strip())
        host = (partes.hostname or "").rstrip(".").casefold()
        partes.port  # noqa: B018 — falla si el puerto no es un número
    except ValueError:
        return "La dirección no es válida."
    if partes.scheme != "https":
        return "Solo se aceptan direcciones que empiecen por https://."
    if not host:
        return "La dirección no es válida."
    if partes.username is not None or partes.password is not None:
        return "La dirección no puede llevar usuario ni credenciales."
    try:
        ipaddress.ip_address(host)
        return "No se aceptan direcciones IP, solo el nombre de la página."
    except ValueError:
        pass
    if _NUMERICO.match(host):
        return "No se aceptan direcciones IP, solo el nombre de la página."
    if "." not in host or host.endswith(_LOCALES):
        return "La dirección no es de una página pública."
    for dominio, portal in _vetados().items():
        if host == dominio or host.endswith("." + dominio):
            return f"{portal} no permite leer sus páginas automáticamente. {PEGAR}"
    try:
        ips = (resolver or _resolver)(host)
    except OSError:
        return "No se ha encontrado esa página."
    if not ips:
        return "No se ha encontrado esa página."
    if not all(_es_publica(ip) for ip in ips):
        return "La dirección no es de una página pública."
    return None
