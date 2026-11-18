"""Lecturas de URL de ofertas (RF-5.3f). Todo va con la sesión de la usuaria: la RLS las separa."""
from sqlalchemy import text
from sqlalchemy.orm import Session


def crear(s: Session, usuaria_id: int, url: str) -> int:
    return s.execute(text("insert into importaciones (usuaria_id, url) values (:u, :l) returning id"),
                     {"u": usuaria_id, "l": url}).scalar_one()


def fila(s: Session, importacion_id: int) -> dict | None:
    r = s.execute(text("select id, url, estado, motivo, oferta_id from importaciones where id=:i"),
                  {"i": importacion_id}).mappings().first()
    return dict(r) if r else None


def marcar_leida(s: Session, importacion_id: int, oferta_id: int) -> None:
    s.execute(text("update importaciones set estado='leida', motivo=null, oferta_id=:o where id=:i"),
              {"i": importacion_id, "o": oferta_id})


def marcar_error(s: Session, importacion_id: int, motivo: str) -> None:
    s.execute(text("update importaciones set estado='error', motivo=:m where id=:i"),
              {"i": importacion_id, "m": motivo})
