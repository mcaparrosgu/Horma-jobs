"""SQL de las notas del matcher. La tabla `matches` es la caché: lo ya puntuado no se vuelve a pedir."""
from sqlalchemy import text
from sqlalchemy.orm import Session

from horma.tools.buscar_ofertas import Consulta


def puntuadas(s: Session, perfil_version: int) -> list[int]:
    """Ofertas que ya tienen nota para esa versión del perfil."""
    return list(s.execute(text("select oferta_id from matches where perfil_version = :v order by 1"),
                          {"v": perfil_version}).scalars())


def ids_candidatas(s: Session, consulta: Consulta) -> list[int]:
    """Ejecuta el filtro duro construido por `buscar_ofertas`, en su orden."""
    return [fila[0] for fila in s.execute(text(consulta.sql), consulta.parametros)]


def guardar(s: Session, usuaria_id: int, perfil_version: int, matches: list[dict]) -> None:
    for m in matches:
        s.execute(text(
            "insert into matches (usuaria_id, oferta_id, perfil_version, nota, condiciones, explicacion, "
            "cita_perfil, cita_oferta, retirada) values (:u, :o, :v, :n, :c, :e, :cp, :co, :r) "
            "on conflict (usuaria_id, oferta_id, perfil_version) do update set nota = excluded.nota, "
            "condiciones = excluded.condiciones, explicacion = excluded.explicacion, "
            "cita_perfil = excluded.cita_perfil, cita_oferta = excluded.cita_oferta, "
            "retirada = excluded.retirada"),
            {"u": usuaria_id, "o": m["oferta_id"], "v": perfil_version, "n": m["nota"],
             "c": m["condiciones"], "e": m["explicacion"], "cp": m["cita_perfil"],
             "co": m["cita_oferta"], "r": m["retirada"]})
