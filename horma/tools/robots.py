"""¿Permite el robots.txt del portal leer esa URL? (RF-1.7)"""
from urllib.robotparser import RobotFileParser

AGENTE = "HormaBot"


def permite(robots_txt: str | None, url: str, agente: str = AGENTE) -> bool | None:
    """True/False según el robots.txt; None si no se pudo leer. Un robots.txt vacío no restringe."""
    if robots_txt is None:
        return None
    p = RobotFileParser()
    p.parse(robots_txt.splitlines())
    return p.can_fetch(agente, url)
