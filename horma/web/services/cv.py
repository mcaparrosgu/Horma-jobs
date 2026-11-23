"""Servicio de CV: comprueba el archivo, lo guarda con nombre aleatorio y, si es fuente, encola
`perfilar` (RF-2.1, RF-2.1b, RF-2.10). El archivo vive en un volumen que solo monta la API."""
import hashlib
import uuid
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from horma.config import ajustes
from horma.tools.clasificar_documento import clasificar_documento
from horma.tools.convertir_cv import ArchivoNoValido, convertir_cv
from horma.web.db import sesion_de, sesion_sistema
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
          nombre: str | None, clase: str | None = None, escrito_por_ella: bool = False) -> dict:
    """Sin `clase`, Horma detecta con reglas si es un CV o una carta (RF-10.14b). Si duda, no guarda nada y
    devuelve `{"duda": True}`: la pantalla pregunta y vuelve a subir con la clase elegida."""
    a = ajustes()
    if clase is not None and clase not in CLASES:
        raise ArchivoRechazado(422, "La clase debe ser «fuente» o «carta».")
    tipo = _tipo(nombre_original)
    if len(contenido) > a.max_cv_bytes:
        raise ArchivoRechazado(413, f"El archivo supera el máximo de {a.max_cv_bytes // (1024 * 1024)} MB.")
    texto = None
    try:
        texto = convertir_cv(contenido, tipo)
    except ArchivoNoValido as e:
        raise ArchivoRechazado(422, str(e)) from e
    if clase is None:
        detectada = clasificar_documento(texto or "")
        if detectada == "duda":
            return {"duda": True}
        clase = "fuente" if detectada == "cv" else "carta"
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


MAX_LOTE = 5
TEXTO_MAX_LOTE = "Puedes subir hasta 5 archivos a la vez. Elige 5 o menos."


class LoteDemasiado(Exception):
    """Más de `MAX_LOTE` archivos: no se sube ninguno (RF-10.18b)."""


def _comprobar(nombre_original: str, contenido: bytes) -> tuple[str, str | None]:
    """(tipo, texto) del archivo, o `ArchivoRechazado` con el motivo corto de RF-10.18c."""
    extension = Path(nombre_original).suffix.lower().lstrip(".")
    if extension not in EXTENSIONES:
        raise ArchivoRechazado(415, "formato no admitido")
    maximo = ajustes().max_cv_bytes
    if len(contenido) > maximo:
        raise ArchivoRechazado(413, f"pesa más de {maximo // (1024 * 1024)} MB")
    tipo = EXTENSIONES[extension]
    try:
        return tipo, convertir_cv(contenido, tipo)
    except ArchivoNoValido as e:
        raise ArchivoRechazado(422, "no se ha podido leer") from e


def _ya_subido(s, contenido: bytes) -> bool:
    """Un archivo con el mismo contenido que otro ya subido (RF-10.18d): solo se leen los de igual tamaño."""
    for ruta in repo.rutas_de_igual_tamano(s, len(contenido)):
        try:
            if (carpeta() / ruta).read_bytes() == contenido:
                return True
        except OSError:
            continue
    return False


def subir_lote(engine: Engine, usuaria_id: int, *, archivos: list[tuple[str, bytes]],
               clases: list[str] | None = None, cerrar: bool = False) -> dict:
    """Hasta `MAX_LOTE` documentos de una vez (RF-10.18). Guarda los válidos y devuelve
    `{subidos, repetidos, fallidos, dudosos, perfil}`; `perfil` es `en_marcha`, `aplazado` (sin presupuesto),
    `pendiente_de_respuesta` (hay dudosos) o `None` (nada que rehacer). El perfil se rehace una sola vez, al
    final (RF-10.18f). Sin `archivos`, `cerrar=True` cierra la pregunta: rehace con lo ya guardado (RF-10.18e)."""
    if len(archivos) > MAX_LOTE:
        raise LoteDemasiado(TEXTO_MAX_LOTE)
    if not archivos and not cerrar:
        raise ArchivoRechazado(422, "Elige al menos un archivo.")
    elegidas = [(c or None) for c in (clases or [])]
    if any(c is not None and c not in CLASES for c in elegidas):
        raise ArchivoRechazado(422, "La clase debe ser «fuente» o «carta».")
    elegidas += [None] * (len(archivos) - len(elegidas))

    fallidos: list[dict] = []
    repetidos: list[dict] = []
    dudosos: list[dict] = []
    listos: list[dict] = []
    escritos: list[Path] = []
    subidos: list[dict] = []
    try:
        with sesion_de(engine, usuaria_id) as s:
            huellas: set[str] = set()
            nombres: set[str] = set()
            for i, (nombre_original, contenido) in enumerate(archivos):
                try:
                    tipo, texto = _comprobar(nombre_original, contenido)
                except ArchivoRechazado as e:
                    fallidos.append({"nombre": nombre_original, "motivo": e.motivo})
                    continue
                huella = hashlib.sha256(contenido).hexdigest()
                if huella in huellas or _ya_subido(s, contenido):
                    repetidos.append({"nombre": nombre_original, "motivo": "ya estaba subido"})
                    continue
                clase = elegidas[i]
                if clase is None:
                    detectada = clasificar_documento(texto or "")
                    if detectada == "duda":
                        dudosos.append({"indice": i, "nombre": nombre_original})
                        continue
                    clase = "fuente" if detectada == "cv" else "carta"
                nombre = Path(nombre_original).stem[:80] or "CV"
                if nombre.lower() in nombres or repo.nombre_en_uso(s, nombre):
                    fallidos.append({"nombre": nombre_original,
                                     "motivo": "ya tienes un documento con ese nombre"})
                    continue
                huellas.add(huella)
                nombres.add(nombre.lower())
                listos.append({"nombre_original": nombre_original, "contenido": contenido, "tipo": tipo,
                               "texto": texto, "clase": clase, "nombre": nombre})
            if listos:
                carpeta().mkdir(parents=True, exist_ok=True)
            for x in listos:
                ruta = f"{uuid.uuid4().hex}.{x['tipo']}"
                try:
                    with s.begin_nested():
                        cv_id = repo.crear(s, usuaria_id, nombre=x["nombre"],
                                           nombre_original=x["nombre_original"][:200], ruta=ruta, tipo=x["tipo"],
                                           clase=x["clase"], tamano=len(x["contenido"]), texto=x["texto"])
                except IntegrityError:   # dos peticiones a la vez: el índice de nombres manda
                    fallidos.append({"nombre": x["nombre_original"],
                                     "motivo": "ya tienes un documento con ese nombre"})
                    continue
                (carpeta() / ruta).write_bytes(x["contenido"])
                escritos.append(carpeta() / ruta)
                subidos.append({"id": cv_id, "nombre": x["nombre"], "tipo": x["tipo"], "clase": x["clase"]})
            perfil = _rehacer_una_vez(s, usuaria_id, subidos, bool(dudosos))
    except BaseException:
        for destino in escritos:
            destino.unlink(missing_ok=True)
        raise
    return {"subidos": subidos, "repetidos": repetidos, "fallidos": fallidos, "dudosos": dudosos,
            "perfil": perfil}


def _rehacer_una_vez(s, usuaria_id: int, subidos: list[dict], hay_dudosos: bool) -> str | None:
    """El `perfilar` único del lote (RF-10.18f). Con dudosos pendientes solo reserva la versión; sin presupuesto
    la deja reservada para `rehacer_aplazados` (RF-10.18g). Las cartas piden la guía de estilo una sola vez."""
    a = ajustes()
    if any(x["clase"] == "carta" for x in subidos):
        servicio_estilo.encolar_si_no_hay_guia(s, usuaria_id)
    en_espera = perfiles.version_en_espera(s)
    if not any(x["clase"] == "fuente" for x in subidos) and en_espera is None:
        return None
    if hay_dudosos:
        perfiles.reservar_en_espera(s, usuaria_id)
        return "pendiente_de_respuesta"
    if en_espera is not None:
        perfil_id = en_espera
        perfiles.quitar_espera(s, perfil_id)
    else:
        perfil_id, _ = perfiles.nueva_version(s, usuaria_id)
    try:
        presupuesto.encolar(s, usuaria_id, "perfilar", perfil_id, a.tope_coste_perfilar, a.tope_reintentos_tarea)
    except presupuesto.SinPresupuesto:
        return "aplazado"   # la versión queda reservada y la recoge `rehacer_aplazados`
    return "en_marcha"


def _rehacer_perfil(s, usuaria_id: int) -> None:
    """Tras quitar un CV del perfil: se rehace con los que quedan; sin ninguno, la usuaria vuelve a «Sube tu CV»."""
    a = ajustes()
    if not perfiles.cvs_fuente(s):
        perfiles.retirar_todos(s)
        return
    perfil_id, _ = perfiles.nueva_version(s, usuaria_id)
    try:
        presupuesto.encolar(s, usuaria_id, "perfilar", perfil_id, a.tope_coste_perfilar,
                            a.tope_reintentos_tarea)
    except presupuesto.SinPresupuesto:
        pass   # la versión queda reservada y la recoge `rehacer_aplazados`


def cambiar_clase(engine: Engine, usuaria_id: int, cv_id: int, clase: str) -> dict | None:
    """«¿No es un CV? Cámbialo» (RF-10.14b). De carta a CV, se rehace el perfil con él; de CV a carta, sin él."""
    if clase not in CLASES:
        raise ArchivoRechazado(422, "La clase debe ser «fuente» o «carta».")
    with sesion_de(engine, usuaria_id) as s:
        cv = repo.uno(s, cv_id)
        if cv is None:
            return None
        if cv["clase"] == clase:
            return {"id": cv_id, "clase": clase}
        if clase == "fuente" and cv["texto_vacio"]:
            raise ArchivoRechazado(422, "No se pudo leer el texto de este documento.")
        repo.cambiar_clase(s, cv_id, clase)
        if clase == "fuente":
            _rehacer_perfil(s, usuaria_id)
        else:
            if cv["clase"] == "fuente":
                _rehacer_perfil(s, usuaria_id)
            servicio_estilo.encolar_si_no_hay_guia(s, usuaria_id)
    return {"id": cv_id, "clase": clase}


def eliminar(engine: Engine, usuaria_id: int, cv_id: int) -> bool:
    """Quita el CV (fila y texto) y, ya confirmado, su archivo. Si era uno de los CV de los que sale el perfil,
    el perfil se rehace con los que quedan; sin ninguno, la usuaria vuelve a «Sube tu CV» (RF-10.14).
    Las candidaturas ya hechas no se tocan. Rehacer gasta del presupuesto del día: sin él, el CV se borra y
    el perfil se rehace en cuanto vuelva a haberlo (`rehacer_aplazados`)."""
    with sesion_de(engine, usuaria_id) as s:
        cv = repo.uno(s, cv_id)
        if cv is None:
            return False
        repo.eliminar(s, cv_id)
        if cv["clase"] == "fuente":
            _rehacer_perfil(s, usuaria_id)
    (carpeta() / cv["ruta"]).unlink(missing_ok=True)
    return True


def rehacer_aplazados(engine: Engine) -> int:
    """Encola el `perfilar` de las versiones que quedaron sin presupuesto, de cada usuaria que ya lo tenga
    (RF-10.14). Lo llama el worker de vez en cuando."""
    a = ajustes()
    n = 0
    with sesion_sistema(engine) as s:
        aplazados = perfiles.aplazados(s)
    for usuaria_id, perfil_id in aplazados:
        with sesion_de(engine, usuaria_id) as s:
            if perfiles.en_espera_de_respuesta(s, perfil_id):
                continue   # aún puede responder la pregunta de un lote (RF-10.18e)
            try:
                presupuesto.encolar(s, usuaria_id, "perfilar", perfil_id, a.tope_coste_perfilar,
                                    a.tope_reintentos_tarea)
                perfiles.quitar_espera(s, perfil_id)
                n += 1
            except presupuesto.SinPresupuesto:
                continue
    return n


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


AVISO_DOCX = ("Así se lee tu documento; el diseño original del Word no se puede mostrar aquí.")


def texto(engine: Engine, usuaria_id: int, cv_id: int) -> dict | None:
    """El texto con el que Horma lee un documento, para «Ver» un DOCX (RF-10.14c). Solo la dueña (RLS)."""
    with sesion_de(engine, usuaria_id) as s:
        if repo.uno(s, cv_id) is None:
            return None
        return {"texto": repo.texto(s, cv_id) or "", "aviso": AVISO_DOCX}


def archivo(engine: Engine, usuaria_id: int, cv_id: int) -> tuple[dict, Path] | None:
    """El CV y la ruta de su archivo, si existe y es de la usuaria (RLS)."""
    with sesion_de(engine, usuaria_id) as s:
        cv = repo.uno(s, cv_id)
    if not cv:
        return None
    ruta = carpeta() / cv["ruta"]
    return (cv, ruta) if ruta.is_file() else None
