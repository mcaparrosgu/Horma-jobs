"""SQL de las candidaturas (fase 3). Todo es de una usuaria: la sesión (RLS «propia») ya filtra."""
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

_j = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731


def fila(s: Session, candidatura_id: int) -> dict | None:
    f = s.execute(text("select * from candidaturas where id = :i"),
                  {"i": candidatura_id}).mappings().first()
    return dict(f) if f else None


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
