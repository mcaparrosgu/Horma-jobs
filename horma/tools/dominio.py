"""Dominios: validar la empresa de una oferta (RF-1.5) y la regla de exclusión de fuentes (RF-1.7)."""
import re
import socket
from collections.abc import Callable
from urllib.parse import urlsplit

Resolvedor = Callable[[str], bool]

CORREO_GRATUITO = {
    "gmail.com", "googlemail.com", "hotmail.com", "hotmail.es", "outlook.com", "outlook.es",
    "live.com", "yahoo.com", "yahoo.es", "icloud.com", "me.com", "protonmail.com", "proton.me",
    "aol.com", "gmx.com", "gmx.de", "gmx.net", "web.de", "mail.com", "yandex.com",
}
EXCLUIDAS = {"linkedin": "LinkedIn", "lnkd": "LinkedIn", "indeed": "Indeed"}
_DOMINIO = re.compile(r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_SEGUNDO_NIVEL = {"co", "com", "org", "net", "gob", "gov", "ac", "edu"}


def normalizar(valor: str | None) -> str | None:
    """De un correo, una URL o un dominio, el dominio en minúsculas y sin `www.`."""
    if not valor:
        return None
    v = valor.strip().casefold()
    if "@" in v and "://" not in v:
        v = v.rsplit("@", 1)[1]
    host = urlsplit(v if "://" in v else f"//{v}").hostname or ""
    host = host.removeprefix("www.")
    return host if _DOMINIO.match(host) else None


def registrable(url_o_host: str) -> str | None:
    """Dominio registrable aproximado: api.portal.com → portal.com; x.empresa.co.uk → empresa.co.uk."""
    host = normalizar(url_o_host)
    if not host:
        return None
    partes = host.split(".")
    n = 3 if len(partes) >= 3 and partes[-2] in _SEGUNDO_NIVEL and len(partes[-1]) == 2 else 2
    return ".".join(partes[-n:])


def resuelve(dominio: str) -> bool:
    """Comprobación real por DNS (la usa el worker; en tests se inyecta otra)."""
    try:
        return bool(socket.getaddrinfo(dominio, None))
    except (socket.gaierror, UnicodeError, OSError):
        return False


def comprobar(dominio: str | None, resolver: Resolvedor | None) -> bool | None:
    """True si el dominio existe y no es de correo gratuito; None si no hay nada que comprobar."""
    d = normalizar(dominio)
    if not d or resolver is None:
        return None
    if d in CORREO_GRATUITO:
        return False
    return resolver(d)


def excluida_por_regla(url: str) -> str | None:
    """Nombre del portal si es LinkedIn o Indeed (nunca se usan como fuente)."""
    host = urlsplit(url if "://" in url else f"//{url}").hostname or ""
    for etiqueta in host.casefold().split("."):
        if etiqueta in EXCLUIDAS:
            return EXCLUIDAS[etiqueta]
    return None
