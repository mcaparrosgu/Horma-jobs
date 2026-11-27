"""Huellas del perfil (RF-10.10c, RF-10.10d). Código puro: dos hashes que cambian solo cuando cambia lo que
afecta a lo que se guarda, para no volver a puntuar ni a clasificar por una errata en otra parte.

- `huella_compatibilidad`: experiencia, formación, habilidades e idiomas de la copia ciega, que es lo que lee
  el `matcher`; sin el titular (spec 012, RF-12.30h).
- `huella_clasificacion`: experiencia, formación y certificaciones de la copia ciega, que es lo que lee
  `clasificador-postulante` (spec 012, RF-12.30h).
"""
import hashlib
import json

from horma.schemas.perfil import Perfil
from horma.tools.copia_ciega import copia_ciega

_COMPATIBILIDAD = ("experiencias", "formacion", "habilidades", "idiomas")
_CLASIFICACION = ("experiencias", "formacion", "certificaciones")


def _sin_origen(valor):
    """El origen (de qué CV y fragmento sale el dato) no cambia lo que dice el dato."""
    if isinstance(valor, dict):
        return {k: _sin_origen(v) for k, v in valor.items() if k != "origen"}
    if isinstance(valor, list):
        return [_sin_origen(v) for v in valor]
    return valor


def _huella(volcado: dict, campos: tuple[str, ...]) -> str:
    datos = {c: _sin_origen(volcado.get(c)) for c in campos}
    canon = json.dumps(datos, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:32]


def huella_compatibilidad(perfil: Perfil) -> str:
    return _huella(copia_ciega(perfil).model_dump(mode="json"), _COMPATIBILIDAD)


def huella_clasificacion(perfil: Perfil) -> str:
    return _huella(copia_ciega(perfil).model_dump(mode="json"), _CLASIFICACION)
