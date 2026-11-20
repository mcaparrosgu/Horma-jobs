"""SQL de las ofertas descartadas por la usuaria (RF-8.6). La RLS deja ver y tocar solo las suyas."""
from sqlalchemy import text
from sqlalchemy.orm import Session


def descartar(s: Session, usuaria_id: int, oferta_id: int) -> None:
    s.execute(text("insert into descartes (usuaria_id, oferta_id) values (:u, :o) "
                   "on conflict do nothing"), {"u": usuaria_id, "o": oferta_id})


def recuperar(s: Session, oferta_id: int) -> None:
    s.execute(text("delete from descartes where oferta_id = :o"), {"o": oferta_id})


def ids(s: Session) -> list[int]:
    return list(s.execute(text("select oferta_id from descartes order by 1")).scalars())
