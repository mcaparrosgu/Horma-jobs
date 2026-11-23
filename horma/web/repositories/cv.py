"""SQL de los CV subidos (RF-2.1, RF-2.1b, RF-2.10). La sesión (RLS) ya limita todo a su dueña."""
from sqlalchemy import text
from sqlalchemy.orm import Session

COLUMNAS = "id, nombre, nombre_original, tipo, clase, tamano, creado_en, escrito_por_ella"


def listar(s: Session) -> list[dict]:
    return [dict(f) for f in s.execute(text(
        f"select {COLUMNAS} from cv_archivos order by id")).mappings().all()]


def uno(s: Session, cv_id: int) -> dict | None:
    fila = s.execute(text(f"select {COLUMNAS}, ruta, coalesce(texto, '') = '' as texto_vacio "
                          "from cv_archivos where id = :i"),
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
          clase: str, tamano: int, texto: str | None, escrito_por_ella: bool = False) -> int:
    return s.execute(text(
        "insert into cv_archivos (usuaria_id, nombre, nombre_original, ruta, tipo, clase, tamano, texto, "
        "escrito_por_ella) values (:u, :n, :o, :r, :t, :c, :z, :x, :e) returning id"),
        {"u": usuaria_id, "n": nombre, "o": nombre_original, "r": ruta, "t": tipo, "c": clase,
         "z": tamano, "x": texto, "e": escrito_por_ella}).scalar_one()


def rutas_de_igual_tamano(s: Session, tamano: int) -> list[str]:
    """Los archivos ya subidos que pesan lo mismo: candidatos a ser idénticos (RF-10.18d)."""
    return [f[0] for f in s.execute(text("select ruta from cv_archivos where tamano = :z"), {"z": tamano}).all()]


def eliminar(s: Session, cv_id: int) -> bool:
    return s.execute(text("delete from cv_archivos where id = :i"), {"i": cv_id}).rowcount == 1


def renombrar(s: Session, cv_id: int, nombre: str) -> bool:
    return s.execute(text("update cv_archivos set nombre = :n where id = :i"),
                     {"i": cv_id, "n": nombre}).rowcount == 1


def marcar_escrito_por_ella(s: Session, cv_id: int, valor: bool) -> bool:
    return s.execute(text("update cv_archivos set escrito_por_ella = :v where id = :i"),
                     {"v": valor, "i": cv_id}).rowcount == 1


def cambiar_clase(s: Session, cv_id: int, clase: str) -> bool:
    return s.execute(text("update cv_archivos set clase = :c where id = :i"),
                     {"c": clase, "i": cv_id}).rowcount == 1


def texto(s: Session, cv_id: int) -> str | None:
    return s.execute(text("select texto from cv_archivos where id = :i"), {"i": cv_id}).scalar_one_or_none()
