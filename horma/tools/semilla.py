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
    fuentes = [Fuente.model_validate(f) for f in datos["fuentes"]]
    if ruta == RUTA:  # las empresas de Greenhouse (config/greenhouse.json) entran como fuentes inactivas
        from horma.tools.greenhouse import fuentes_de

        fuentes += fuentes_de()
    return fuentes
