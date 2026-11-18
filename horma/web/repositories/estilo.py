"""SQL de la guía de estilo (RF-5.6d). La sesión (RLS) ya limita todo a su dueña."""
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from horma.schemas.estilo import GuiaEstilo

MAX_DOCUMENTOS = 10
MAX_CARACTERES = 8000  # por documento: la guía no necesita más para ver cómo escribe


def guia(s: Session) -> dict | None:
    fila = s.execute(text("select guia, origen, analizada_en from estilo")).mappings().first()
    return dict(fila) if fila else None


def guardar(s: Session, usuaria_id: int, nueva: GuiaEstilo, origen: str) -> None:
    s.execute(text(
        "insert into estilo (usuaria_id, guia, origen) values (:u, cast(:g as jsonb), :o) "
        "on conflict (usuaria_id) do update set guia = excluded.guia, origen = excluded.origen, "
        "analizada_en = now()"),
        {"u": usuaria_id, "g": json.dumps(nueva.model_dump(mode="json"), ensure_ascii=False), "o": origen})


def documentos(s: Session) -> list[dict]:
    """CV «fuente» y cartas con texto; primero los marcados «Lo escribí yo» (RF-5.6b)."""
    filas = s.execute(text(
        "select case when clase = 'carta' then 'carta' else 'cv' end as tipo, texto, escrito_por_ella "
        "from cv_archivos where clase in ('fuente', 'carta') and texto is not null "
        "order by escrito_por_ella desc, id limit :n"), {"n": MAX_DOCUMENTOS}).mappings().all()
    return [{**f, "texto": f["texto"][:MAX_CARACTERES]} for f in filas]
