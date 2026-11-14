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
from horma.web.repositories import perfiles, tareas

EXTENSIONES = {"pdf": "pdf", "docx": "docx", "md": "md", "markdown": "md"}
MEDIA = {"pdf": "application/pdf", "md": "text/markdown; charset=utf-8",
         "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
CLASES = ("fuente", "estetico")


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


def _firma_estetico(contenido: bytes, tipo: str) -> None:
    """El estético no se procesa, pero tampoco se guarda cualquier cosa: se mira la firma del archivo."""
    ok = {"pdf": contenido.lstrip()[:5] == b"%PDF-", "docx": contenido[:4] == b"PK\x03\x04",
          "md": b"\x00" not in contenido}[tipo]
    if not ok:
        raise ArchivoRechazado(422, f"El archivo no es un {tipo.upper()} válido.")


def subir(engine: Engine, usuaria_id: int, *, contenido: bytes, nombre_original: str,
          nombre: str | None, clase: str) -> dict:
    a = ajustes()
    if clase not in CLASES:
        raise ArchivoRechazado(422, "La clase debe ser «fuente» o «estetico».")
    tipo = _tipo(nombre_original)
    if len(contenido) > a.max_cv_bytes:
        raise ArchivoRechazado(413, f"El archivo supera el máximo de {a.max_cv_bytes // (1024 * 1024)} MB.")
    texto = None
    try:
        if clase == "fuente":
            texto = convertir_cv(contenido, tipo)
        elif not contenido:
            raise ArchivoNoValido("el archivo está vacío")
        else:
            _firma_estetico(contenido, tipo)
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
                               ruta=ruta, tipo=tipo, clase=clase, tamano=len(contenido), texto=texto)
            perfil_id = None
            if clase == "fuente":
                perfil_id, _ = perfiles.nueva_version(s, usuaria_id)
                tareas.encolar(s, usuaria_id, "perfilar", perfil_id, a.tope_coste_perfilar,
                               a.tope_reintentos_tarea)
    except IntegrityError as e:
        _borrar(destino, escrito)
        raise NombreRepetido(nombre) from e
    except BaseException:
        _borrar(destino, escrito)
        raise
    return {"id": cv_id, "nombre": nombre, "tipo": tipo, "clase": clase, "perfil_id": perfil_id}


def _borrar(destino: Path, escrito: bool) -> None:
    if escrito:
        destino.unlink(missing_ok=True)
