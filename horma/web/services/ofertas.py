"""Servicio de ofertas: alta en el catálogo y encolado del flujo procesar_oferta (RF-1.3, RF-1.4)."""
import re
import unicodedata
from datetime import datetime

from sqlalchemy import Engine

from horma.config import ajustes
from horma.web.db import sesion_de, sesion_sistema
from horma.web.repositories import importaciones, tareas
from horma.web.repositories import ingesta as repo_ingesta
from horma.web.repositories import ofertas as repo
from horma.web.services import presupuesto

TIPO_TAREA = "procesar_oferta"


class FuenteNoValida(Exception):
    """La fuente indicada no existe o no está activa."""


class NoPareceOferta(ValueError):
    """El texto pegado por una usuaria no tiene pinta de oferta de trabajo."""


MIN_PALABRAS_OFERTA = 5
MIN_LETRAS_OFERTA = 25
MOTIVO_NO_OFERTA = ("Ese texto no parece una oferta de trabajo. Pega la oferta completa: puesto, empresa y "
                    "lo que piden u ofrecen.")


# Vocabulario de empleo (RF-5.3i): raíces sin tildes, en español y en inglés. Una oferta real usa varias;
# una receta, un cuento o un correo personal, casi ninguna.
_VOCABULARIO_EMPLEO = re.compile(
    r"\b(ofert|emple|trabajo|trabajar en|puesto|vacante|contrat|salari|sueld|retribu|remuner|brut[oa]s|"
    r"jornada|horari|turno|experiencia|requisit|requi|imprescindible|valorable|se valora|busca|"
    r"necesita|incorpor|candidat|entrevista|funciones|responsabilidad|empresa|cargo|beneficios|"
    r"teletrabajo|remoto|hibrid|presencial|curricul|cv|inscri|titulacion|freelance|autonom|publicad|"
    r"job|role|position|hiring|salary|requirement|experience|responsibilit|apply|candidate|benefits|"
    r"remote|full[- ]time|part[- ]time|skills)"
    r"|\d\s?(k|€|euros)\b")   # una cifra de sueldo («35-40k», «1.200 €»)
MIN_TERMINOS_EMPLEO = 1


def _sin_tildes(texto: str) -> str:
    t = unicodedata.normalize("NFD", texto)
    return "".join(c for c in t if unicodedata.category(c) != "Mn").casefold()


def parece_oferta(texto: str) -> bool:
    """Filtro barato y sin modelo (RF-5.3g, RF-5.3i): sin etiquetas ni enlaces, ¿quedan 5 palabras y 25
    letras, y alguna palabra propia de una oferta de empleo? No decide si es buena oferta; solo deja
    fuera lo que claramente no es texto de una oferta (una receta, un cuento…). Ante la duda, deja pasar:
    rechazar una oferta real es peor que analizar un texto que no lo es."""
    limpio = re.sub(r"<[^>]*>|https?://\S+", " ", texto or "")
    palabras = re.findall(r"[^\W\d_]{2,}", limpio)
    if len(palabras) < MIN_PALABRAS_OFERTA or sum(len(p) for p in palabras) < MIN_LETRAS_OFERTA:
        return False
    terminos = {m.group(0).strip() for m in _VOCABULARIO_EMPLEO.finditer(_sin_tildes(limpio))}
    return len(terminos) >= MIN_TERMINOS_EMPLEO


def recibir(engine: Engine, texto: str, *, fuente: str | None = None, clave_id: int | None = None,
            id_externo: str | None = None, url: str | None = None,
            usuaria_id: int | None = None, caduca_en: datetime | None = None,
            tope_coste: float | None = None,
            tope_reintentos: int | None = None) -> dict:
    """Guarda la oferta cruda y, si es nueva, encola su procesado. La carga de la cola es el id.
    Con `usuaria_id` la oferta es privada de esa usuaria (RF-5.3c)."""
    a = ajustes()
    if usuaria_id is not None and not parece_oferta(texto):
        raise NoPareceOferta(MOTIVO_NO_OFERTA)
    with sesion_sistema(engine) as s:
        fuente_id = atribucion = None
        if fuente:
            f = repo_ingesta.fuente(s, nombre=fuente)
            if not f or not f["activa"]:
                raise FuenteNoValida(fuente)
            fuente_id, atribucion = f["id"], f["atribucion"]
        oferta_id, estado, nueva = repo.crear(s, texto, fuente_id=fuente_id, clave_id=clave_id,
                                              id_externo=id_externo, url=url, usuaria_id=usuaria_id,
                                              caduca_en=caduca_en, atribucion=atribucion)
        aplazada = False
        if nueva:
            tope = a.tope_coste_tarea if tope_coste is None else tope_coste
            reintentos = a.tope_reintentos_tarea if tope_reintentos is None else tope_reintentos
            if usuaria_id is None:  # catálogo común: gasto del sistema, sin presupuesto de usuaria
                tareas.encolar(s, None, TIPO_TAREA, oferta_id, tope, reintentos)
            else:
                try:
                    presupuesto.encolar_oferta_propia(s, usuaria_id, oferta_id, tope, reintentos)
                except presupuesto.SinPresupuesto:  # se guarda y se analiza en cuanto haya presupuesto
                    aplazada = True
    return {"id": oferta_id, "estado": estado, "nueva": nueva, **({"aplazada": True} if aplazada else {})}


def encolar_propias_aplazadas(engine: Engine) -> int:
    """Encola el análisis de las ofertas propias que quedaron sin presupuesto, de cada usuaria que ya lo
    tenga (RF-10.9e). Lo llama el worker de vez en cuando."""
    a = ajustes()
    n = 0
    with sesion_sistema(engine) as s:
        for oferta_id, usuaria_id in repo.propias_sin_tarea(s):
            try:
                presupuesto.encolar_oferta_propia(s, usuaria_id, oferta_id, a.tope_coste_tarea,
                                                  a.tope_reintentos_tarea)
                n += 1
            except presupuesto.SinPresupuesto:
                continue
    return n


def pedir_lectura_url(engine: Engine, usuaria_id: int, url: str) -> int:
    """Encola la lectura de una URL de oferta, privada de la usuaria (RF-5.3f). Sin reintentos."""
    a = ajustes()
    with sesion_de(engine, usuaria_id) as s:
        importacion = importaciones.crear(s, usuaria_id, url.strip())
        presupuesto.encolar(s, usuaria_id, "leer_url", importacion, a.tope_coste_tarea, 1)
    return importacion


def estado_lectura_url(engine: Engine, usuaria_id: int, importacion_id: int) -> dict | None:
    with sesion_de(engine, usuaria_id) as s:
        fila = importaciones.fila(s, importacion_id)
    return {k: fila[k] for k in ("id", "estado", "motivo", "oferta_id")} if fila else None


def por_estado(engine: Engine, usuaria_id: int) -> dict:
    with sesion_de(engine, usuaria_id) as s:
        return repo.por_estado(s)


def catalogo(engine: Engine, usuaria_id: int) -> list[dict]:
    """El catálogo común con su auditoría y su taxonomía (RF-8.2c)."""
    with sesion_de(engine, usuaria_id) as s:
        filas = repo.listar(s)
    with sesion_sistema(engine) as s:
        return repo.marcar_fuente_desconocida(filas, s)


def propias(engine: Engine, usuaria_id: int) -> list[dict]:
    """Las ofertas que la usuaria ha añadido, con el avance de su análisis (RF-8.2c, RF-8.7)."""
    with sesion_de(engine, usuaria_id) as s:
        filas = repo.propias(s, usuaria_id)
    with sesion_sistema(engine) as s:  # `procesar_oferta` y `fuentes` son del sistema
        repo.marcar_fuente_desconocida(filas, s)
        avance = repo.progreso_de_analisis(s, [f["id"] for f in filas])
    return [{**f, "progreso": avance.get(f["id"])} for f in filas]


def original(engine: Engine, usuaria_id: int, oferta_id: int) -> dict | None:
    with sesion_de(engine, usuaria_id) as s:
        return repo.original(s, oferta_id)


def procesar_en_linea(engine: Engine) -> str | None:
    """Solo desarrollo (`horma_flujo_en_linea`): procesa una tarea sin worker aparte."""
    from horma.web.queue import worker  # aquí y no arriba: el worker importa este servicio
    return worker.procesar_una(engine)
