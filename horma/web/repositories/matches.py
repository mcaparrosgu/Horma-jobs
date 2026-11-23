"""SQL de las notas del matcher. La tabla `matches` es la caché: lo ya puntuado no se vuelve a pedir."""
from sqlalchemy import text
from sqlalchemy.orm import Session

from horma.tools.buscar_ofertas import Consulta


def puntuadas(s: Session, huella: str) -> list[int]:
    """Ofertas con una nota calculada con un perfil de esa huella (RF-10.10c): no se vuelven a puntuar."""
    return list(s.execute(text("select distinct oferta_id from matches where huella_perfil = :h order by 1"),
                          {"h": huella}).scalars())


def puntuadas_de(s: Session, huella: str, oferta_id: int) -> list[int]:
    """[oferta_id] si esa oferta ya tiene nota para esa huella del perfil; si no, []."""
    return list(s.execute(text("select distinct oferta_id from matches "
                               "where huella_perfil = :h and oferta_id = :o"),
                          {"h": huella, "o": oferta_id}).scalars())


def ids_candidatas(s: Session, consulta: Consulta) -> list[int]:
    """Ejecuta el filtro duro construido por `buscar_ofertas`, en su orden."""
    return [fila[0] for fila in s.execute(text(consulta.sql), consulta.parametros)]


def listado(s: Session, ids: list[int], huella: str | None = None) -> list[dict]:
    """Las ofertas con la nota vigente de la usuaria (o ninguna: «sin puntuar»), en el orden de `ids`.
    Vigente = calculada con la huella actual del perfil; si no hay, la más reciente. `desfasado`: la nota
    se calculó con otra huella (RF-10.10c). Las filas sin huella usan la regla de las versiones."""
    if not ids:
        return []
    filas = s.execute(text(
        "select o.id, o.titulo, o.empresa, o.ubicacion, o.pais, o.remoto, o.modalidad, o.sector, o.familia, "
        "o.nivel, "
        "o.salario_publicado, o.salario_rango, o.salario_minimo, o.salario_maximo, o.salario_moneda, "
        "o.fecha_publicacion, o.url, o.atribucion, o.creada_en, o.usuaria_id is not null as propia, "
        "o.procesada_en as analizada_en, o.fantasma, o.motivos_fantasma, o.fraude, o.senales_fraude, "
        "(o.salario_anual_eur_min is not null or o.salario_anual_eur_max is not null) "
        "as sueldo_comparable, m.nota, m.condiciones, m.explicacion, m.cita_perfil, m.cita_oferta, "
        "m.retirada, m.correccion, m.perfil_version, "
        "case when m.huella_perfil is null or cast(:h as text) is null then "
        "m.perfil_version < coalesce((select max(version) from perfiles where estado = 'hecha'), 0) "
        "else m.huella_perfil <> cast(:h as text) end as desfasado, d.oferta_id is not null as descartada, "
        "c.id as candidatura_id, c.estado as candidatura_estado, c.motivo_cierre as candidatura_motivo, "
        "c.preparacion as candidatura_preparacion "
        "from ofertas o left join descartes d on d.oferta_id = o.id "
        "left join lateral (select id, estado, motivo_cierre, preparacion from candidaturas x "
        "where x.oferta_id = o.id "
        "order by (x.estado <> 'cerrada') desc, x.id desc limit 1) c on true "
        "left join lateral (select * from matches x where x.oferta_id = o.id "
        "order by (x.huella_perfil is not distinct from cast(:h as text)) desc, "
        "x.perfil_version desc limit 1) m on true "
        "where o.id = any(cast(:ids as int[]))"), {"ids": list(ids), "h": huella}).mappings().all()
    por_id = {}
    for f in filas:
        f = dict(f)
        cid = f.pop("candidatura_id")
        estado, motivo = f.pop("candidatura_estado"), f.pop("candidatura_motivo")
        preparacion = f.pop("candidatura_preparacion")
        f["candidatura"] = (None if cid is None else
                            {"id": cid, "estado": estado, "motivo_cierre": motivo, "preparacion": preparacion})  # noqa: E501
        por_id[f["id"]] = f
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


def informacion_de(s: Session, oferta_id: int) -> str | None:
    """La «información nueva» de la última corrección de esa oferta (RF-10.15), aunque la compatibilidad se
    haya vuelto a calcular después con otra versión del perfil."""
    valor = s.execute(text(
        "select correccion->>'informacion' from matches where oferta_id = :o and correccion is not null "
        "order by corregido_en desc nulls last, perfil_version desc limit 1"), {"o": oferta_id}).scalar()
    return (valor or "").strip() or None


def guardar(s: Session, usuaria_id: int, perfil_version: int, matches: list[dict],
            huella: str | None = None) -> None:
    for m in matches:
        s.execute(text(
            "insert into matches (usuaria_id, oferta_id, perfil_version, nota, condiciones, explicacion, "
            "cita_perfil, cita_oferta, retirada, huella_perfil) "
            "values (:u, :o, :v, :n, :c, :e, :cp, :co, :r, :h) "
            "on conflict (usuaria_id, oferta_id, perfil_version) do update set nota = excluded.nota, "
            "condiciones = excluded.condiciones, explicacion = excluded.explicacion, "
            "cita_perfil = excluded.cita_perfil, cita_oferta = excluded.cita_oferta, "
            "retirada = excluded.retirada, huella_perfil = excluded.huella_perfil"),
            {"u": usuaria_id, "o": m["oferta_id"], "v": perfil_version, "n": m["nota"],
             "c": m["condiciones"], "e": m["explicacion"], "cp": m["cita_perfil"],
             "co": m["cita_oferta"], "r": m["retirada"], "h": huella})
