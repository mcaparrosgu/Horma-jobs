"""Huellas del perfil (RF-10.10c, RF-10.10d). Código puro: dos hashes que cambian solo cuando cambia lo que
afecta a lo que se guarda, para no volver a puntuar ni a clasificar por una errata en otra parte.

- `huella_compatibilidad`: experiencia, formación, habilidades, idiomas y titular (lo que mira el `matcher`).
- `huella_clasificacion`: experiencia, formación y titular (lo que mira `clasificador-postulante`).
"""
import hashlib
import json

from horma.schemas.perfil import Perfil

_COMPATIBILIDAD = ("titular", "experiencias", "formacion", "habilidades", "idiomas")
_CLASIFICACION = ("titular", "experiencias", "formacion")


def _sin_origen(valor):
    """El origen (de qué CV y fragmento sale el dato) no cambia lo que dice el dato."""
    if isinstance(valor, dict):
        return {k: _sin_origen(v) for k, v in valor.items() if k != "origen"}
    if isinstance(valor, list):
        return [_sin_origen(v) for v in valor]
    return valor


def _huella(perfil: Perfil, campos: tuple[str, ...]) -> str:
    volcado = perfil.model_dump(mode="json")
    datos = {c: _sin_origen(volcado.get(c)) for c in campos}
    canon = json.dumps(datos, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:32]


def huella_compatibilidad(perfil: Perfil) -> str:
    return _huella(perfil, _COMPATIBILIDAD)


def huella_clasificacion(perfil: Perfil) -> str:
    return _huella(perfil, _CLASIFICACION)
