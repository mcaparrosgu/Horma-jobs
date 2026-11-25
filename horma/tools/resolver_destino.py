"""¿A qué portal lleva el enlace de una oferta? (RF-11.1b). Solo mira direcciones: no envía nada.

Primero casa la dirección tal cual; si no basta, sigue las redirecciones (solo `GET`) y casa la final.
LinkedIn, Indeed y Glassdoor dan siempre «no automático»; InfoJobs y Welcome to the Jungle son portales
como los demás. Código determinista, sin modelo.
"""
import json
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from horma.tools.descargar import seguir_redireccion

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
Seguidor = Callable[[str], str]


@dataclass(frozen=True)
class Destino:
    portal: str | None          # nombre del portal, o None si no hay canal automático
    automatico: bool            # ¿hay un canal al que Horma podría enviar?
    exige_cuenta: bool = False  # el portal pide cuenta de la candidata (lo habitual en él)
    url_final: str | None = None
    motivo: str = ""            # por qué no es automático


@lru_cache(maxsize=1)
def _portales() -> dict[str, dict]:
    return json.loads((_ASSETS / "portales.json").read_text(encoding="utf-8"))["portales"]


@lru_cache(maxsize=1)
def _vetados() -> dict[str, str]:
    datos = json.loads((_ASSETS / "portales_vetados.json").read_text(encoding="utf-8"))
    return {d: nombre for nombre, dominios in datos.items() for d in dominios}


def _host(url: str | None) -> str:
    try:
        return (urlsplit((url or "").strip()).hostname or "").rstrip(".").casefold()
    except ValueError:
        return ""


def _casa(host: str, dominio: str) -> bool:
    return host == dominio or host.endswith("." + dominio)


def _portal_de(host: str) -> tuple[str, dict] | None:
    for nombre, datos in _portales().items():
        if any(_casa(host, d) for d in datos["dominios"]):
            return nombre, datos
    return None


def _vetado_de(host: str) -> str | None:
    return next((n for d, n in _vetados().items() if _casa(host, d)), None)


def _clasificar(url: str) -> Destino | None:
    host = _host(url)
    if not host:
        return None
    if (p := _portal_de(host)):
        return Destino(portal=p[0], automatico=True, exige_cuenta=bool(p[1]["exige_cuenta"]), url_final=url)
    if (v := _vetado_de(host)):
        return Destino(portal=None, automatico=False, url_final=url,
                       motivo=f"{v} no permite el envío automático.")
    return None


def resolver_destino(url: str | None, seguir: Seguidor = seguir_redireccion) -> Destino:
    """El canal de una oferta o «no automático» con su motivo. Nunca lanza: un fallo de red es un motivo."""
    if not (url or "").strip():
        return Destino(portal=None, automatico=False, motivo="La oferta no tiene enlace.")
    if (d := _clasificar(url)):
        return d
    try:
        final = seguir(url)
    except Exception:  # noqa: BLE001 - red, tiempo o redirección rota: se cuenta, no se propaga
        return Destino(portal=None, automatico=False, url_final=url,
                       motivo="No se pudo seguir el enlace.")
    if (d := _clasificar(final)):
        return d
    return Destino(portal=None, automatico=False, url_final=final,
                   motivo="No es un portal de los que Horma conoce.")
