"""Servicio de CV: comprueba el archivo, lo guarda con nombre aleatorio y, si es fuente, encola
`perfilar` (RF-2.1, RF-2.1b, RF-2.10). El archivo vive en un volumen que solo monta la API."""
import uuid
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from horma.config import ajustes
from horma.tools.convertir_cv import ArchivoNoValido, convertir_cv
from horma.web.db import sesion_de
from horma.web.repositories import cv as repo
from horma.web.repositories import perfiles
from horma.web.services import estilo as servicio_estilo
from horma.web.services import presupuesto

EXTENSIONES = {"pdf": "pdf", "docx": "docx", "md": "md", "markdown": "md"}
MEDIA = {"pdf": "application/pdf", "md": "text/markdown; charset=utf-8",
         "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
CLASES = ("fuente", "carta")   # «estetico» se retiró (RF-10.5e); los ya subidos se conservan


class ArchivoRechazado(Exception):
    def __init__(self, estado: int, motivo: str):
        super().__init__(motivo)
        self.estado, self.motivo = estado, motivo


class NombreRepetido(Exception):
    """Ya hay un CV con ese nombre en la cuenta."""


def carpeta() -> Path:
    return Path(ajustes().ruta_archivos)


def _tipo(nombre_original: str) -> str:
    extension = Path(nombre_original).suffix.lower().lstrip(".")
    if extension not in EXTENSIONES:
        raise ArchivoRechazado(415, "Solo se admiten archivos PDF, DOCX o Markdown.")
    return EXTENSIONES[extension]


def subir(engine: Engine, usuaria_id: int, *, contenido: bytes, nombre_original: str,
          nombre: str | None, clase: str, escrito_por_ella: bool = False) -> dict:
    a = ajustes()
    if clase not in CLASES:
        raise ArchivoRechazado(422, "La clase debe ser «fuente» o «carta».")
    tipo = _tipo(nombre_original)
    if len(contenido) > a.max_cv_bytes:
        raise ArchivoRechazado(413, f"El archivo supera el máximo de {a.max_cv_bytes // (1024 * 1024)} MB.")
    texto = None
    try:
        texto = convertir_cv(contenido, tipo)
    except ArchivoNoValido as e:
        raise ArchivoRechazado(422, str(e)) from e
    nombre = (nombre or "").strip() or Path(nombre_original).stem[:80] or "CV"

    ruta = f"{uuid.uuid4().hex}.{tipo}"
    destino = carpeta() / ruta
    escrito = False
    try:
        with sesion_de(engine, usuaria_id) as s:
            if repo.nombre_en_uso(s, nombre):
                raise NombreRepetido(nombre)
            carpeta().mkdir(parents=True, exist_ok=True)
            destino.write_bytes(contenido)
            escrito = True
            cv_id = repo.crear(s, usuaria_id, nombre=nombre, nombre_original=nombre_original[:200],
                               ruta=ruta, tipo=tipo, clase=clase, tamano=len(contenido), texto=texto,
                               escrito_por_ella=escrito_por_ella)
            perfil_id = None
            if clase == "fuente":
                perfil_id, _ = perfiles.nueva_version(s, usuaria_id)
                presupuesto.encolar(s, usuaria_id, "perfilar", perfil_id, a.tope_coste_perfilar,
                               a.tope_reintentos_tarea)
            elif clase == "carta":  # solo si aún no hay guía: después, solo con el botón (RF-5.6d)
                servicio_estilo.encolar_si_no_hay_guia(s, usuaria_id)
    except IntegrityError as e:
        _borrar(destino, escrito)
        raise NombreRepetido(nombre) from e
    except BaseException:
        _borrar(destino, escrito)
        raise
    return {"id": cv_id, "nombre": nombre, "tipo": tipo, "clase": clase, "perfil_id": perfil_id}


def eliminar(engine: Engine, usuaria_id: int, cv_id: int) -> bool:
    """Quita el CV (fila y texto) y, ya confirmado, su archivo. El perfil ya construido no cambia."""
    with sesion_de(engine, usuaria_id) as s:
        cv = repo.uno(s, cv_id)
        if cv is None:
            return False
        repo.eliminar(s, cv_id)
    (carpeta() / cv["ruta"]).unlink(missing_ok=True)
    return True


def _borrar(destino: Path, escrito: bool) -> None:
    if escrito:
        destino.unlink(missing_ok=True)


def listar(engine: Engine, usuaria_id: int) -> list[dict]:
    with sesion_de(engine, usuaria_id) as s:
        return repo.listar(s)


def renombrar(engine: Engine, usuaria_id: int, cv_id: int, nombre: str) -> bool:
    """False si no existe ese CV; `NombreRepetido` si ya hay otro con ese nombre."""
    with sesion_de(engine, usuaria_id) as s:
        if repo.uno(s, cv_id) is None:
            return False
        if repo.nombre_en_uso(s, nombre, excepto_cv=cv_id):
            raise NombreRepetido(nombre)
        repo.renombrar(s, cv_id, nombre)
    return True


def marcar_escrito_por_ella(engine: Engine, usuaria_id: int, cv_id: int, valor: bool) -> bool:
    with sesion_de(engine, usuaria_id) as s:
        return repo.marcar_escrito_por_ella(s, cv_id, valor)


def archivo(engine: Engine, usuaria_id: int, cv_id: int) -> tuple[dict, Path] | None:
    """El CV y la ruta de su archivo, si existe y es de la usuaria (RLS)."""
    with sesion_de(engine, usuaria_id) as s:
        cv = repo.uno(s, cv_id)
    if not cv:
        return None
    ruta = carpeta() / cv["ruta"]
    return (cv, ruta) if ruta.is_file() else None
