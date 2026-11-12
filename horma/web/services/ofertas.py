"""Servicio de ofertas: orquesta el agente y decide qué datos tienen origen (RT-08)."""
import re

from sqlalchemy import Engine

from horma.agents.extractor_oferta.agent import ExtractorOferta
from horma.agents.extractor_oferta.schemas import TextoOferta
from horma.config import ajustes
from horma.llm.proveedor import Proveedor
from horma.schemas.oferta import OfertaExtraida, Salario
from horma.web.db import sesion_de
from horma.web.repositories import ofertas as repo
from horma.web.repositories import tareas

TIPO_TAREA = "extraer_oferta"


def crear_y_encolar(engine: Engine, usuaria_id: int, texto: str, *, tope_coste: float | None = None,
                    tope_reintentos: int | None = None) -> int:
    """Guarda la oferta como pendiente y encola una tarea con su id."""
    a = ajustes()
    with sesion_de(engine, usuaria_id) as s:
        oferta_id = repo.crear(s, usuaria_id, texto)
        tareas.encolar(s, usuaria_id, TIPO_TAREA, oferta_id,
                       a.tope_coste_tarea if tope_coste is None else tope_coste,
                       a.tope_reintentos_tarea if tope_reintentos is None else tope_reintentos)
    return oferta_id


def _linea_con(texto: str, aguja: str) -> str | None:
    aguja = aguja.strip().casefold()
    if not aguja:
        return None
    for linea in texto.splitlines():
        if aguja in linea.casefold():
            return linea.strip()
    return None


def _formas_numero(n: float) -> list[str]:
    entero = int(n) if float(n).is_integer() else n
    formas = [str(entero)]
    if isinstance(entero, int):
        formas += [f"{entero:,}".replace(",", "."), f"{entero:,}"]
    return formas


def _linea_numero(texto: str, n: float) -> str | None:
    for forma in _formas_numero(n):
        if (linea := _linea_con(texto, forma)):
            return linea
    return None


def con_origen(texto: str, o: OfertaExtraida) -> tuple[OfertaExtraida, list[tuple[str, str]]]:
    """Conserva solo los datos que se pueden localizar en el texto; el resto se descarta."""
    origenes: list[tuple[str, str]] = []
    datos: dict = {}

    primera = next((ln.strip() for ln in texto.splitlines() if ln.strip()), texto.strip())
    datos["titulo"] = o.titulo
    origenes.append(("titulo", _linea_con(texto, o.titulo) or primera))

    for campo in ("empresa", "ubicacion", "contrato", "fecha_publicacion"):
        valor = getattr(o, campo)
        if valor and (linea := _linea_con(texto, valor)):
            datos[campo] = valor
            origenes.append((campo, linea))
    if o.url and (linea := _linea_con(texto, str(o.url).rstrip("/"))):
        datos["url"] = o.url
        origenes.append(("url", linea))

    if o.remoto is not None:
        marca = re.search(r"remot|teletrabajo|presencial|híbrid|hibrid", texto, re.I)
        if marca and (linea := _linea_con(texto, marca.group(0))):
            datos["remoto"] = o.remoto
            origenes.append(("remoto", linea))

    if o.salario:
        s = o.salario
        lmin = _linea_numero(texto, s.minimo) if s.minimo is not None else None
        lmax = _linea_numero(texto, s.maximo) if s.maximo is not None else None
        if lmin or lmax:
            datos["salario"] = Salario(minimo=s.minimo if lmin else None,
                                       maximo=s.maximo if lmax else None, moneda=s.moneda)
            if lmin:
                origenes.append(("salario_minimo", lmin))
            if lmax:
                origenes.append(("salario_maximo", lmax))
            origenes.append(("salario_moneda", lmin or lmax))

    for campo in ("idiomas", "requisitos", "instrucciones_embebidas"):
        conservados = []
        for item in getattr(o, campo):
            if (linea := _linea_con(texto, item)):
                conservados.append(item)
                origenes.append((campo, linea))
        datos[campo] = conservados
    return OfertaExtraida(**datos), origenes


def extraer(texto: str, proveedor: Proveedor | None = None):
    """Ejecuta el agente y filtra por origen. Sin acceso a la base de datos."""
    bruta = ExtractorOferta.run(TextoOferta(texto=texto), proveedor=proveedor)
    return con_origen(texto, bruta)
