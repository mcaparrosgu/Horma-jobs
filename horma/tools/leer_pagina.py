"""Lee una página pública con Apify (actor `rag-web-browser`) y devuelve su texto (RF-5.3f, RF-5.3h).

Sin proxies residenciales ni servicios para saltar bloqueos (RF-5.3g). El token va solo en la cabecera
`Authorization`: nunca en la URL, en un mensaje de error ni en un log. El texto leído es no fiable (RT-07)."""
import re

import httpx

from horma.config import ajustes

ACTOR = "apify~rag-web-browser"
ENDPOINT = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"
MAX_CARACTERES = 20_000  # el mismo máximo que el texto pegado (`NuevaOferta.texto`)
MIN_CARACTERES = 400  # menos que esto no es una oferta: error, bloqueo, cabecera o página vacía
# Una página corta con alguna de estas frases es un error o un bloqueo, no una oferta (prueba real de T19:
# Lever devolvió su 404 de «oferta cerrada»). En una página larga no se miran: una oferta real puede citarlas.
MAX_PAGINA_DE_ERROR = 1500
_ERROR = re.compile(
    r"404|not found|no encontrad|no existe|ya no est[aá] disponible|no longer available|has been removed"
    r"|might have closed|access denied|acceso denegado|captcha|verify you are human|enable javascript",
    re.IGNORECASE)
MENSAJE = "La página no se ha podido leer: pega el texto de la oferta."


class LecturaFallida(Exception):
    """No se pudo leer la página. El mensaje nunca contiene el token ni la respuesta del proveedor."""


def leer_pagina(url: str, *, cliente: httpx.Client | None = None, token: str | None = None,
                timeout: float | None = None) -> str:
    a = ajustes()
    token = a.apify_token if token is None else token
    if not token:
        raise LecturaFallida("falta el token del proveedor de lectura")
    propio = cliente is None
    cliente = cliente or httpx.Client()
    try:
        r = cliente.post(ENDPOINT, headers={"Authorization": f"Bearer {token}"},
                         json={"query": url, "maxResults": 1},
                         timeout=a.apify_timeout_s if timeout is None else timeout)
        r.raise_for_status()
        datos = r.json()
    except httpx.TimeoutException as e:
        raise LecturaFallida("el proveedor tardó demasiado") from e
    except httpx.HTTPStatusError as e:
        raise LecturaFallida(f"el proveedor respondió {e.response.status_code}") from None
    except (httpx.HTTPError, ValueError) as e:
        raise LecturaFallida(f"respuesta no válida del proveedor ({type(e).__name__})") from None
    finally:
        if propio:
            cliente.close()
    primero = datos[0] if isinstance(datos, list) and datos and isinstance(datos[0], dict) else {}
    texto = str(primero.get("markdown") or "").strip()
    if len(texto) < MIN_CARACTERES:
        raise LecturaFallida("la página no devolvió texto suficiente")
    if len(texto) < MAX_PAGINA_DE_ERROR and _ERROR.search(texto):
        raise LecturaFallida("la página es un error o un bloqueo, no una oferta")
    return texto[:MAX_CARACTERES]
