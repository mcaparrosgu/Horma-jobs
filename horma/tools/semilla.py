"""Lee la semilla de fuentes (config/endpoints.json). Sin base de datos: la usan la migración y
`horma ingestar --en-seco`."""
import json
from pathlib import Path

from horma.schemas.fuente import Fuente

RUTA = Path(__file__).resolve().parents[2] / "config" / "endpoints.json"


def fuentes_semilla(ruta: Path = RUTA) -> list[Fuente]:
    if not ruta.exists():
        return []
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return [Fuente.model_validate(f) for f in datos["fuentes"]]
