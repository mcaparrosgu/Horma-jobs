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


def listado(s: Session, ids: list[int]) -> list[dict]:
    """Las ofertas con la nota más reciente de la usuaria (o ninguna: «sin puntuar»), en el orden de
    `ids`. `desfasado`: la nota se calculó con una versión anterior del perfil."""
    if not ids:
        return []
    filas = s.execute(text(
        "select o.id, o.titulo, o.empresa, o.ubicacion, o.pais, o.remoto, o.sector, o.familia, o.nivel, "
        "o.salario_publicado, o.salario_rango, o.salario_minimo, o.salario_maximo, o.salario_moneda, "
        "o.fecha_publicacion, o.url, o.creada_en, "
        "(o.salario_anual_eur_min is not null or o.salario_anual_eur_max is not null) "
        "as sueldo_comparable, m.nota, m.condiciones, m.explicacion, m.cita_perfil, m.cita_oferta, "
        "m.retirada, m.correccion, m.perfil_version, "
        "m.perfil_version < coalesce((select max(version) from perfiles where estado = 'hecha'), 0) "
        "as desfasado "
        "from ofertas o left join lateral (select * from matches x where x.oferta_id = o.id "
        "order by x.perfil_version desc limit 1) m on true "
        "where o.id = any(cast(:ids as int[]))"), {"ids": list(ids)}).mappings().all()
    por_id = {f["id"]: dict(f) for f in filas}
    return [por_id[i] for i in ids if i in por_id]


def uno(s: Session, oferta_id: int) -> dict | None:
    """La nota más reciente de una oferta."""
    fila = s.execute(text("select * from matches where oferta_id = :o order by perfil_version desc "
                          "limit 1"), {"o": oferta_id}).mappings().first()
    return dict(fila) if fila else None


def guardar_correccion(s: Session, oferta_id: int, perfil_version: int, correccion: str) -> None:
    s.execute(text("update matches set correccion = cast(:c as jsonb), corregido_en = now() "
                   "where oferta_id = :o and perfil_version = :v"),
              {"o": oferta_id, "v": perfil_version, "c": correccion})


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
