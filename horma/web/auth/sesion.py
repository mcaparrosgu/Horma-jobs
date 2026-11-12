"""Dependencias de sesión: usuaria actual, protección CSRF y rol de administradora."""
import hmac

from fastapi import Depends, HTTPException, Request

from horma.config import ajustes


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


def es_admin(request: Request) -> bool:
    sub = request.session.get("sub")
    return bool(sub) and sub in ajustes().admins()


def exigir_admin(request: Request, _usuaria: int = Depends(usuaria_actual)) -> None:
    """RF-1.10: el dashboard de ingesta es solo para las cuentas de HORMA_ADMINS."""
    if not es_admin(request):
        raise HTTPException(status_code=403, detail="Solo para administradoras")


def exigir_admin_con_csrf(request: Request, _a: None = Depends(exigir_admin),
                          _c: None = Depends(exigir_csrf)) -> None:
    """Cambios desde el dashboard: administradora y CSRF."""
