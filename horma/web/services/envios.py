"""Medición de destinos (RF-11.1): a qué portal lleva cada oferta del catálogo y cuántas exigen cuenta.
Solo lee direcciones y sigue redirecciones con `GET`: no envía nada ni llama al modelo (RF-11.1c).
Se calcula al pedirla; no se guarda en ninguna tabla."""
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import Engine

from horma.tools.resolver_destino import Destino, resolver_destino
from horma.web.db import sesion_sistema
from horma.web.repositories import ofertas as repo

NO_AUTOMATICO = "No automático"
SIN_ENLACE = "La oferta no tiene enlace."
HILOS = 8


def medir_destinos(engine: Engine, resolver: Callable[[str | None], Destino] = resolver_destino) -> dict:
    with sesion_sistema(engine) as s:
        urls = repo.urls_catalogo(s)
    return resumir(urls, resolver)


def resumir(urls: list[str | None], resolver: Callable[[str | None], Destino] = resolver_destino) -> dict:
    distintas = sorted({u for u in urls if u})
    with ThreadPoolExecutor(max_workers=HILOS) as pool:  # una dirección se resuelve una sola vez
        destinos = dict(zip(distintas, pool.map(resolver, distintas), strict=True))
    cuentas: Counter[tuple[str, bool]] = Counter()
    motivos: Counter[str] = Counter()
    for u in urls:
        d = destinos.get(u) if u else None
        if d is not None and d.automatico:
            cuentas[(d.portal or NO_AUTOMATICO, d.exige_cuenta)] += 1
        else:
            cuentas[(NO_AUTOMATICO, False)] += 1
            motivos[d.motivo if d is not None and d.motivo else SIN_ENLACE] += 1
    orden = sorted(cuentas.items(), key=lambda x: (x[0][0] == NO_AUTOMATICO, -x[1], x[0][0]))
    filas = [{"portal": p, "ofertas": n, "exige_cuenta": e, "automatico": p != NO_AUTOMATICO}
             for (p, e), n in orden]
    automaticas = sum(f["ofertas"] for f in filas if f["automatico"])
    return {"total": len(urls), "automaticas": automaticas,
            "exigen_cuenta": sum(f["ofertas"] for f in filas if f["exige_cuenta"]),
            "no_automaticas": len(urls) - automaticas, "filas": filas,
            "motivos": [{"motivo": m, "ofertas": n}
                        for m, n in sorted(motivos.items(), key=lambda x: (-x[1], x[0]))]}
