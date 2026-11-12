"""Identidad: Google OAuth 2.0 (OpenID Connect). Authlib valida el token de Google (JWT)."""
import logging
from typing import Protocol

from fastapi import HTTPException

from horma.config import Ajustes


class Identidad(Protocol):
    async def redirigir(self, request, redirect_uri: str): ...

    async def sub_desde_callback(self, request) -> str:
        """Devuelve el identificador estable de la usuaria en Google (`sub`)."""
        ...


class IdentidadNoConfigurada:
    """Sin credenciales de Google la app arranca, pero nadie puede entrar."""

    async def redirigir(self, request, redirect_uri: str):
        raise HTTPException(status_code=503, detail="Google OAuth no está configurado")

    async def sub_desde_callback(self, request) -> str:
        raise HTTPException(status_code=503, detail="Google OAuth no está configurado")


def crear_identidad(a: Ajustes) -> Identidad:
    if a.google_client_id and a.google_client_secret:
        return IdentidadGoogle(a)
    logging.getLogger("horma").warning("Faltan GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET: login desactivado")
    return IdentidadNoConfigurada()


class IdentidadGoogle:
    def __init__(self, a: Ajustes):
        from authlib.integrations.starlette_client import OAuth

        self._oauth = OAuth()
        self._oauth.register(
            "google", client_id=a.google_client_id, client_secret=a.google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid"},  # solo el identificador: ni email ni nombre
        )

    async def redirigir(self, request, redirect_uri: str):
        return await self._oauth.google.authorize_redirect(request, redirect_uri)

    async def sub_desde_callback(self, request) -> str:
        token = await self._oauth.google.authorize_access_token(request)
        return token["userinfo"]["sub"]
