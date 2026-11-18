"""Límites de ritmo (RF-4.6d): ventana deslizante en memoria del proceso de la API.

Generaliza el limitador de `POST /ofertas` (por clave de API) a otras rutas, por IP o por usuaria.
Los umbrales salen de `.env`. Los tamaños máximos de petición se controlan aparte, en `main.py`."""
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable, Hashable
from typing import Literal

from fastapi import HTTPException, Request

from horma.config import Ajustes, ajustes

VENTANA_S = 60
MENSAJE = "Has hecho demasiadas peticiones seguidas. Espera un minuto y vuelve a intentarlo."


class Limitador:
    """Ventana deslizante de 60 s por clave (un id de clave de API, una IP, una usuaria…)."""

    def __init__(self):
        self._marcas: dict[Hashable, deque[float]] = defaultdict(deque)
        self._cerrojo = threading.Lock()

    def permitir(self, clave: Hashable, limite: int, ahora: float | None = None,
                 ventana: float = VENTANA_S) -> bool:
        ahora = time.monotonic() if ahora is None else ahora
        with self._cerrojo:
            marcas = self._marcas[clave]
            while marcas and ahora - marcas[0] >= ventana:
                marcas.popleft()
            if len(marcas) >= limite:
                if not marcas:  # límite 0: nada se permite y no se guarda la clave
                    del self._marcas[clave]
                return False
            marcas.append(ahora)
            return True


def _ip(request: Request) -> str:
    return request.client.host if request.client else "desconocida"


def limitar(cubo: str, limite: Callable[[Ajustes], int], por: Literal["ip", "usuaria"], *,
           ventana: float = VENTANA_S, mensaje: str = MENSAJE):
    """Dependencia de FastAPI: 429 si se supera `limite` peticiones por `ventana` (un minuto) en el `cubo`.

    Rutas con el mismo `cubo` comparten contador (p. ej. crear y reintentar una candidatura).
    Con `por="usuaria"` y sin sesión no cuenta nada: ya responderá 401 la ruta."""
    def dependencia(request: Request) -> None:
        quien = _ip(request) if por == "ip" else request.session.get("usuaria_id")
        if quien is None:
            return
        if not request.app.state.limitador.permitir((cubo, quien), limite(ajustes()), ventana=ventana):
            raise HTTPException(status_code=429, detail=mensaje)
    return dependencia


limite_login = limitar("login", lambda a: a.limite_login_por_minuto, "ip")
limite_subida_cv = limitar("subida_cv", lambda a: a.limite_cv_por_minuto, "usuaria")
limite_url = limitar("url", lambda a: a.limite_url_hora, "usuaria", ventana=3600,
                     mensaje="Has pedido demasiadas lecturas. Espera un rato o pega el texto de la oferta.")
limite_candidaturas = limitar("candidaturas", lambda a: a.limite_candidaturas_por_minuto, "usuaria")
