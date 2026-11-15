"""SQL de las candidaturas (fase 3). Todo es de una usuaria: la sesión (RLS «propia») ya filtra."""
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

_j = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731


def fila(s: Session, candidatura_id: int) -> dict | None:
    f = s.execute(text("select * from candidaturas where id = :i"),
                  {"i": candidatura_id}).mappings().first()
    return dict(f) if f else None


def oferta_procesada(s: Session, oferta_id: int) -> bool:
    return s.execute(text("select 1 from ofertas where id = :i and estado = 'procesada'"),
                     {"i": oferta_id}).first() is not None


def hay_viva(s: Session, oferta_id: int) -> bool:
    """¿Hay ya una candidatura no cerrada para esta oferta? (RF-3.7b)"""
    return s.execute(text("select 1 from candidaturas where oferta_id = :i and estado <> 'cerrada'"),
                     {"i": oferta_id}).first() is not None


def crear(s: Session, usuaria_id: int, oferta_id: int) -> int:
    return s.execute(text("insert into candidaturas (usuaria_id, oferta_id) values (:u, :o) returning id"),
                     {"u": usuaria_id, "o": oferta_id}).scalar_one()


def tablero(s: Session) -> list[dict]:
    """Una tarjeta por candidatura, de la última tocada a la primera."""
    return [dict(f) for f in s.execute(text(
        "select c.id, c.oferta_id, c.estado, c.preparacion, c.motivo_cierre, c.actualizado_en, "
        "o.titulo, o.empresa from candidaturas c left join ofertas o on o.id = c.oferta_id "
        "order by c.actualizado_en desc, c.id desc")).mappings()]


def detalle(s: Session, candidatura_id: int) -> dict | None:
    """La fila sin el texto del correo pegado, con la oferta y el CV base elegido."""
    f = s.execute(text(
        "select c.*, o.titulo as oferta_titulo, o.empresa as oferta_empresa, b.nombre as cv_base_nombre, "
        "b.perfil_version < coalesce((select max(version) from perfiles where estado = 'hecha'), 0) "
        "as cv_base_desfasado from candidaturas c left join ofertas o on o.id = c.oferta_id "
        "left join cv_base b on b.id = c.cv_base_id where c.id = :i"),
        {"i": candidatura_id}).mappings().first()
    return dict(f) if f else None


def eventos(s: Session, candidatura_id: int) -> list[dict]:
    return [dict(f) for f in s.execute(text(
        "select id, de, a, motivo, canal, origen, tipo, etiqueta_respuesta, creado_en "
        "from candidatura_eventos where candidatura_id = :i order by id"),
        {"i": candidatura_id}).mappings()]


def registrar_evento(s: Session, usuaria_id: int, candidatura_id: int, *, tipo: str = "transicion",
                     de: str | None = None, a: str | None = None, motivo: str | None = None,
                     canal: str | None = None, origen: str = "usuaria",
                     etiqueta_respuesta: str | None = None) -> None:
    s.execute(text(
        "insert into candidatura_eventos (usuaria_id, candidatura_id, de, a, motivo, canal, origen, tipo, "
        "etiqueta_respuesta) values (:u, :c, :de, :a, :m, :ca, :o, :t, :e)"),
        {"u": usuaria_id, "c": candidatura_id, "de": de, "a": a, "m": motivo, "ca": canal, "o": origen,
         "t": tipo, "e": etiqueta_respuesta})


def contenido_cv_base(s: Session, cv_base_id: int | None) -> str:
    if cv_base_id is None:
        return ""
    return s.execute(text("select contenido from cv_base where id = :i"), {"i": cv_base_id}).scalar() or ""


def cv_estetico_valido(s: Session, cv_id: int) -> bool:
    return s.execute(text("select 1 from cv_archivos where id = :i and clase = 'estetico'"),
                     {"i": cv_id}).first() is not None


def guardar_edicion(s: Session, candidatura_id: int, cv: str, carta: str, avisos: list[str],
                    preparacion: str) -> None:
    s.execute(text("update candidaturas set cv_contenido = :cv, carta_contenido = :ca, "
                   "avisos = cast(:a as jsonb), preparacion = :p, actualizado_en = now() where id = :i"),
              {"i": candidatura_id, "cv": cv, "ca": carta, "a": _j(avisos), "p": preparacion})


def aprobar(s: Session, candidatura_id: int, documento: str, cv_estetico_id: int | None) -> None:
    s.execute(text("update candidaturas set estado = 'aprobada', documento = :d, cv_estetico_id = :e, "
                   "actualizado_en = now() where id = :i"),
              {"i": candidatura_id, "d": documento, "e": cv_estetico_id})


def marcar_enviada(s: Session, candidatura_id: int, fecha, canal: str, canal_otro: str | None) -> None:
    s.execute(text("update candidaturas set estado = 'enviada', enviada_en = :f, canal = :c, "
                   "canal_otro = :o, actualizado_en = now() where id = :i"),
              {"i": candidatura_id, "f": fecha, "c": canal, "o": canal_otro})


def cambiar_estado(s: Session, candidatura_id: int, estado: str, motivo_cierre: str | None = None) -> None:
    s.execute(text("update candidaturas set estado = :e, motivo_cierre = :m, actualizado_en = now() "
                   "where id = :i"), {"i": candidatura_id, "e": estado, "m": motivo_cierre})


def guardar_respuesta_pendiente(s: Session, candidatura_id: int, texto: str) -> None:
    """El texto vive solo hasta que el worker lo clasifica; también se borra la propuesta anterior."""
    s.execute(text("update candidaturas set respuesta_pendiente = :t, respuesta_propuesta = null, "
                   "actualizado_en = now() where id = :i"), {"i": candidatura_id, "t": texto})


def borrar_propuesta(s: Session, candidatura_id: int) -> None:
    s.execute(text("update candidaturas set respuesta_propuesta = null, respuesta_pendiente = null, "
                   "actualizado_en = now() where id = :i"), {"i": candidatura_id})


def cv_base_para_flujo(s: Session) -> list[dict]:
    """Todos los CV base de la usuaria; el flujo descarta los rechazados."""
    return [dict(f) for f in s.execute(text(
        "select id, usuaria_id, nombre, sector, familia, contenido, estado, perfil_version "
        "from cv_base order by id")).mappings().all()]


def guardar_preparacion(s: Session, candidatura_id: int, perfil_version: int, r: dict) -> None:
    """Deja en la fila lo que produjo el flujo; `estado` (borrador…) no se toca nunca."""
    s.execute(text(
        "update candidaturas set cv_base_id = :cb, cv_base_motivo = :cm, perfil_version = :pv, "
        "cv_contenido = :cv, cv_traza = cast(:cvt as jsonb), carta_contenido = :ca, "
        "carta_traza = cast(:cat as jsonb), huecos = cast(:h as jsonb), avisos = cast(:a as jsonb), "
        "cobertura_ats = :ats, vueltas_cv = :vcv, vueltas_carta = :vca, "
        "instrucciones_embebidas = cast(:ie as jsonb), preparacion = :p, motivo_error = null, "
        "actualizado_en = now() where id = :i"),
        {"i": candidatura_id, "cb": r["cv_base_id"], "cm": r["cv_base_motivo"], "pv": perfil_version,
         "cv": r["cv_contenido"], "cvt": _j(r["cv_traza"]), "ca": r["carta_contenido"],
         "cat": _j(r["carta_traza"]), "h": _j(r["huecos"]), "a": _j(r["avisos"]),
         "ats": r["cobertura_ats"], "vcv": r["vueltas_cv"], "vca": r["vueltas_carta"],
         "ie": _j(r["instrucciones_embebidas"]), "p": r["preparacion"]})


def marcar_error(s: Session, candidatura_id: int, motivo: str) -> None:
    s.execute(text("update candidaturas set preparacion = 'error', motivo_error = :m, "
                   "actualizado_en = now() where id = :i"), {"i": candidatura_id, "m": motivo[:500]})


def guardar_propuesta(s: Session, candidatura_id: int, propuesta: dict) -> None:
    """Guarda la propuesta y borra el texto del correo: no se conserva (RF-3.9)."""
    s.execute(text("update candidaturas set respuesta_propuesta = cast(:p as jsonb), "
                   "respuesta_pendiente = null, actualizado_en = now() where id = :i"),
              {"i": candidatura_id, "p": _j(propuesta)})


def borrar_respuesta_pendiente(s: Session, candidatura_id: int) -> None:
    s.execute(text("update candidaturas set respuesta_pendiente = null, actualizado_en = now() "
                   "where id = :i"), {"i": candidatura_id})
