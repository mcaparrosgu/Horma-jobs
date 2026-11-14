"""SQL de los CV subidos (RF-2.1, RF-2.1b, RF-2.10). La sesión (RLS) ya limita todo a su dueña."""
from sqlalchemy import text
from sqlalchemy.orm import Session

COLUMNAS = "id, nombre, nombre_original, tipo, clase, tamano, creado_en"


def listar(s: Session) -> list[dict]:
    return [dict(f) for f in s.execute(text(
        f"select {COLUMNAS} from cv_archivos order by id")).mappings().all()]


def uno(s: Session, cv_id: int) -> dict | None:
    fila = s.execute(text(f"select {COLUMNAS}, ruta from cv_archivos where id = :i"),
                     {"i": cv_id}).mappings().first()
    return dict(fila) if fila else None


def nombre_en_uso(s: Session, nombre: str, *, excepto_cv: int | None = None,
                  excepto_base: int | None = None) -> bool:
    """Dentro de la cuenta no hay dos CV (subidos o base) con el mismo nombre (RF-2.1b)."""
    en_cv = s.execute(text("select 1 from cv_archivos where lower(nombre) = lower(:n) "
                           "and id is distinct from :e"), {"n": nombre, "e": excepto_cv}).first()
    en_base = s.execute(text("select 1 from cv_base where lower(nombre) = lower(:n) "
                             "and estado = 'hecho' and id is distinct from :e"),
                        {"n": nombre, "e": excepto_base}).first()
    return bool(en_cv or en_base)


def crear(s: Session, usuaria_id: int, *, nombre: str, nombre_original: str, ruta: str, tipo: str,
          clase: str, tamano: int, texto: str | None) -> int:
    return s.execute(text(
        "insert into cv_archivos (usuaria_id, nombre, nombre_original, ruta, tipo, clase, tamano, texto) "
        "values (:u, :n, :o, :r, :t, :c, :z, :x) returning id"),
        {"u": usuaria_id, "n": nombre, "o": nombre_original, "r": ruta, "t": tipo, "c": clase,
         "z": tamano, "x": texto}).scalar_one()


def renombrar(s: Session, cv_id: int, nombre: str) -> bool:
    return s.execute(text("update cv_archivos set nombre = :n where id = :i"),
                     {"i": cv_id, "n": nombre}).rowcount == 1
