"""Greenhouse empresa a empresa (RF-5.5c). Su API de lectura es pública y no tiene directorio:
cada empresa tiene un «board token». Aquí se comprueba cada token y se convierte en una `Fuente`
(siempre inactiva hasta una calificación apta). La lista vive en `config/greenhouse.json`."""
import json
import re
from pathlib import Path

import httpx

from horma.schemas.fuente import Fuente

RUTA = Path(__file__).resolve().parents[2] / "config" / "greenhouse.json"
API = "https://boards-api.greenhouse.io/v1/boards"
_TOKEN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,38}$")
USER_AGENT = "HormaBot/0.1 (ingesta de ofertas)"


def fuente_de(token: str, nombre: str) -> Fuente:
    return Fuente(
        nombre=f"gh-{token}", web="https://boards.greenhouse.io", url=f"{API}/{token}/jobs",
        parametros={"content": "true"},
        mapeo={"lista": "jobs", "id": "id", "titulo": "title", "empresa": f"={nombre}",
               "ubicacion": "location.name", "fecha": "updated_at", "url": "absolute_url",
               "descripcion": "content"},
        cada_horas=12, atribucion=f"Ofertas de {nombre} (Greenhouse)", activa=False)


def validar_token(token: str, http: httpx.Client) -> str | None:
    """Nombre de la empresa si el token responde; None si no existe o no tiene forma de token."""
    if not _TOKEN.match(token):
        return None
    r = http.get(f"{API}/{token}", headers={"User-Agent": USER_AGENT}, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    nombre = r.json().get("name")
    return nombre.strip() if isinstance(nombre, str) and nombre.strip() else None


def fuentes_de(ruta: Path = RUTA) -> list[Fuente]:
    if not ruta.exists():
        return []
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return [fuente_de(e["token"], e["nombre"]) for e in datos["empresas"]]


def anadir(ruta: Path, empresas: list[dict]) -> int:
    """Añade a la lista las empresas nuevas (por token), ordenadas. Devuelve cuántas añadió."""
    datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {"empresas": []}
    tokens = {e["token"] for e in datos["empresas"]}
    nuevas = [e for e in empresas if e["token"] not in tokens]
    datos["empresas"] = sorted([*datos["empresas"], *nuevas], key=lambda e: e["token"])
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return len(nuevas)
