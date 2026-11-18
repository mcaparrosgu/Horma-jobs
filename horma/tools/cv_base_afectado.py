"""Qué CV base ha dejado desfasado un cambio del perfil (RF-5.1e). Código puro.

Un CV base está afectado si algún `fragmento` de su traza ya no aparece en el maestro nuevo. Así,
editar una experiencia de hostelería no toca el CV base de construcción que no la usa. La
comparación ignora mayúsculas, negritas y espacios (la misma que `verificar_trazabilidad`)."""
from collections.abc import Mapping, Sequence

from horma.tools.verificar_trazabilidad import _campo, _clave


def lineas_cambiadas(traza: Sequence[Mapping | object], maestro_nuevo: str) -> list[str]:
    """Fragmentos de la traza (sin repetir, en orden) que ya no están en el maestro nuevo."""
    maestro = _clave(maestro_nuevo)
    vistos: dict[str, None] = {}
    for t in traza:
        fragmento = _campo(t, "fragmento")
        if _clave(fragmento) not in maestro:
            vistos.setdefault(fragmento)
    return list(vistos)


def cv_base_afectado(traza: Sequence[Mapping | object], maestro_nuevo: str) -> bool:
    return bool(lineas_cambiadas(traza, maestro_nuevo))
