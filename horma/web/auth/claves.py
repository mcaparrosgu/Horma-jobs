"""Claves de API (RF-1.3): `Authorization: Bearer hk_…`, guardadas como hash, con alcance y ritmo.

Alcances:
- `ofertas`: solo `POST /ofertas` (una empresa que publica mientras no hay portal).
- `ingesta`: además, las rutas del ingestor y pedir calificaciones (consola sin BD).
"""
from dataclasses import dataclass

from fastapi import HTTPException, Request

from horma.config import ajustes
from horma.web.limites import Limitador  # noqa: F401 - se sigue importando desde aquí
from horma.web.services import ingesta as servicio


@dataclass(frozen=True)
class Clave:
    id: int
    alcance: str


def portador(request: Request) -> str | None:
    cabecera = request.headers.get("authorization", "")
    tipo, _, valor = cabecera.partition(" ")
    return valor.strip() if tipo.lower() == "bearer" and valor.strip() else None


def clave_valida(request: Request, alcances: set[str]) -> Clave:
    """La clave del `Authorization`, o 401/403."""
    texto = portador(request)
    datos = servicio.validar_clave(request.app.state.engine, texto) if texto else None
    if not datos:
        raise HTTPException(status_code=401, detail="Clave de API no válida")
    if datos["alcance"] not in alcances:
        raise HTTPException(status_code=403, detail="La clave no tiene alcance para esta ruta")
    return Clave(id=datos["id"], alcance=datos["alcance"])


def contar_ritmo(request: Request, clave: Clave) -> None:
    if not request.app.state.limitador.permitir(clave.id, ajustes().limite_ofertas_por_minuto):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones con esta clave")
