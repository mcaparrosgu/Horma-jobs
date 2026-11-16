"""Avisos que siguen vigentes en un documento (RF-3.6c, RF-3.8). Código puro.

De los problemas del único juicio, solo cuentan los de ese documento cuya frase sigue literalmente en el
texto: si la usuaria (o la vuelta del redactor) ya la reescribió, el aviso desaparece sin llamar al modelo."""
from collections.abc import Sequence

from horma.schemas.candidatura import Aviso, Problema, aviso_de_problema


def avisos_vigentes(documento: str, contenido: str, problemas: Sequence[Problema | dict]) -> list[Aviso]:
    vistos: dict[tuple, Aviso] = {}
    for p in problemas:
        p = p if isinstance(p, Problema) else Problema.model_validate(p)
        if p.documento == documento and p.frase and p.frase in contenido:
            aviso = aviso_de_problema(p)
            vistos.setdefault((aviso.documento, aviso.frase, aviso.mensaje), aviso)
    return list(vistos.values())
