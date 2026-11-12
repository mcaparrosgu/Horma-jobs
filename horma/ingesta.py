"""Ingestor (RF-1.2): lee el endpoint de una fuente, normaliza cada oferta a texto crudo y la entrega
por `POST /ofertas`. No tiene credenciales de la base de datos: solo conoce la URL de la API, su
clave de ingesta y las claves de las fuentes (variables de entorno)."""
import logging
import os
import re
import time
from collections.abc import Mapping

import httpx

from horma.schemas.fuente import Fuente
from horma.tools import normalizar

log = logging.getLogger("horma.ingesta")
_VARIABLE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")


class ErrorApi(Exception):
    """La API de Horma respondió con un error."""


class ClienteApi:
    """Habla con la API de Horma con la clave de ingesta (Bearer)."""

    def __init__(self, base_url: str, clave: str, http: httpx.Client | None = None):
        if not clave:
            raise ValueError("Falta HORMA_CLAVE_INGESTA (créala en el dashboard de ingesta).")
        self.base = base_url.rstrip("/")
        self.http = http or httpx.Client(timeout=30)
        self.cabeceras = {"Authorization": f"Bearer {clave}"}

    def _pedir(self, metodo: str, ruta: str, **kw) -> httpx.Response:
        r = self.http.request(metodo, f"{self.base}{ruta}", headers=self.cabeceras, **kw)
        if r.status_code >= 400:
            raise ErrorApi(f"{metodo} {ruta} → {r.status_code}: {r.text[:200]}")
        return r

    def empezar(self, fuente: str, limite: int) -> dict:
        return self._pedir("POST", "/api/ingesta/ejecuciones",
                           json={"fuente": fuente, "limite": limite}).json()

    def reclamar(self) -> dict | None:
        r = self._pedir("POST", "/api/ingesta/reclamar")
        return None if r.status_code == 204 else r.json()

    def publicar(self, oferta: normalizar.OfertaNormalizada, fuente: str) -> dict:
        return self._pedir("POST", "/ofertas", json={
            "texto": oferta.texto, "fuente": fuente, "id_externo": oferta.id_externo,
            "url": oferta.url}).json()

    def cerrar(self, ejecucion_id: int, **numeros) -> None:
        self._pedir("POST", f"/api/ingesta/ejecuciones/{ejecucion_id}/fin", json=numeros)

    def pedir_calificacion(self, url: str) -> dict:
        return self._pedir("POST", "/api/fuentes/calificaciones", json={"url": url}).json()

    def calificacion(self, calificacion_id: int) -> dict:
        return self._pedir("GET", f"/api/fuentes/calificaciones/{calificacion_id}").json()


def _sustituir(valor, permitidas: list[str], entorno: Mapping[str, str]):
    if not isinstance(valor, str):
        return valor

    def poner(m: re.Match) -> str:
        nombre = m.group(1)
        if nombre not in permitidas:
            raise ValueError(f"La fuente no declara la variable {nombre} en variable_clave.")
        if not entorno.get(nombre):
            raise ValueError(f"Falta la variable de entorno {nombre}.")
        return entorno[nombre]

    return _VARIABLE.sub(poner, valor)


def leer_fuente(fuente: Fuente, http: httpx.Client, limite: int,
                entorno: Mapping[str, str] | None = None) -> list[normalizar.OfertaNormalizada]:
    """Llama al endpoint y devuelve hasta `limite` ofertas normalizadas a texto crudo."""
    entorno = os.environ if entorno is None else entorno
    variables = fuente.variables()
    params = {k: _sustituir(v, variables, entorno) for k, v in fuente.parametros.items()}
    cabeceras = {k: _sustituir(v, variables, entorno) for k, v in fuente.cabeceras.items()}
    cabeceras.setdefault("User-Agent", "HormaBot/0.1 (ingesta de ofertas)")
    if fuente.metodo == "GET":
        r = http.get(fuente.url, params=params, headers=cabeceras, timeout=30)
    else:
        r = http.post(fuente.url, json=params, headers=cabeceras, timeout=30)
    r.raise_for_status()
    items = normalizar.items(r.json(), fuente.mapeo)[:limite]
    return [normalizar.oferta_a_texto(i, fuente.mapeo) for i in items]


def _ejecutar(api: ClienteApi, encargo: dict, http_fuentes: httpx.Client,
              entorno: Mapping[str, str] | None) -> dict:
    ejecucion, fuente = encargo["ejecucion"], Fuente.model_validate(encargo["fuente"])
    numeros = {"recibidas": 0, "nuevas": 0, "repetidas": 0, "errores": 0}
    motivo = None
    try:
        ofertas = leer_fuente(fuente, http_fuentes, ejecucion["limite"], entorno)
        numeros["recibidas"] = len(ofertas)
        for o in ofertas:
            try:
                r = api.publicar(o, fuente.nombre)
                numeros["nuevas" if r["nueva"] else "repetidas"] += 1
            except ErrorApi as e:
                numeros["errores"] += 1
                log.warning("oferta %s no entregada: %s", o.id_externo, e)
    except Exception as e:  # noqa: BLE001 - el endpoint falló: la ejecución queda en error
        motivo = f"{type(e).__name__}: {e}"
    api.cerrar(ejecucion["id"], **numeros, motivo=motivo)
    return {**ejecucion, **numeros, "estado": "error" if motivo else "hecha", "motivo_error": motivo}


def ingestar_fuente(api: ClienteApi, nombre: str, limite: int, http_fuentes: httpx.Client,
                    entorno: Mapping[str, str] | None = None) -> dict:
    """`horma ingestar <fuente>`: crea la ejecución, entrega las ofertas y la cierra."""
    return _ejecutar(api, api.empezar(nombre, limite), http_fuentes, entorno)


def atender_una(api: ClienteApi, http_fuentes: httpx.Client,
                entorno: Mapping[str, str] | None = None) -> dict | None:
    """Toma una ejecución pedida desde el dashboard; None si no hay ninguna."""
    encargo = api.reclamar()
    return _ejecutar(api, encargo, http_fuentes, entorno) if encargo else None


def escuchar(api: ClienteApi, http_fuentes: httpx.Client, espera: float = 5.0) -> None:
    """Bucle del servicio `ingestor`: atiende las ejecuciones del dashboard."""
    log.info("ingestor en marcha")
    while True:
        try:
            if (r := atender_una(api, http_fuentes)) is not None:
                log.info("ejecución %s: %s", r["id"], {k: r[k] for k in ("estado", "nuevas")})
                continue
        except (ErrorApi, httpx.HTTPError) as e:
            log.warning("la API no responde: %s", e)
        time.sleep(espera)
