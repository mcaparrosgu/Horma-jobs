"""Comprobaciones de arranque en producción (RF-4.6c): secretos distintos por entorno."""
from sqlalchemy.engine import make_url

from horma.config import Ajustes

SESSION_SECRET_MIN = 32
# Valores de ejemplo o de desarrollo que nunca deben llegar a producción
_DE_EJEMPLO = {"", "changeme", "password", "horma", "postgres", "secret", "secreto", "cambiar"}


def _es_de_ejemplo(valor: str | None) -> bool:
    v = (valor or "").strip().lower()
    return v in _DE_EJEMPLO or v.startswith(("<", "cambia", "changeme", "ejemplo"))


def problemas_de_arranque(a: Ajustes) -> list[str]:
    """Lista de motivos por los que la API no debe arrancar en producción (vacía si todo está bien)."""
    problemas = []
    if len(a.session_secret) < SESSION_SECRET_MIN or _es_de_ejemplo(a.session_secret):
        problemas.append(f"SESSION_SECRET debe tener al menos {SESSION_SECRET_MIN} caracteres "
                         "y no ser el del ejemplo")
    try:
        contrasena = make_url(a.database_url).password
    except Exception:  # noqa: BLE001 - una URL ilegible tampoco sirve
        contrasena = None
    if _es_de_ejemplo(contrasena):
        problemas.append("La contraseña de DATABASE_URL está vacía o es la del ejemplo")
    if not a.google_redirect_uri.startswith("https://"):
        problemas.append("GOOGLE_REDIRECT_URI debe empezar por https://")
    return problemas
