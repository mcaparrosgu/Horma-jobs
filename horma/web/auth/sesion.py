"""Dependencias de sesión: usuaria actual y protección CSRF."""
import hmac

from fastapi import Depends, HTTPException, Request


def usuaria_actual(request: Request) -> int:
    usuaria_id = request.session.get("usuaria_id")
    if not usuaria_id:
        raise HTTPException(status_code=401, detail="Sin sesión")
    return usuaria_id


def exigir_csrf(request: Request, _usuaria: int = Depends(usuaria_actual)) -> None:
    esperado = request.session.get("csrf", "")
    recibido = request.headers.get("x-csrf-token", "")
    if not esperado or not hmac.compare_digest(esperado, recibido):
        raise HTTPException(status_code=403, detail="CSRF no válido")
