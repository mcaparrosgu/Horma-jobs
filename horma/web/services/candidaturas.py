"""Servicio de candidaturas (fase 3): crear, editar, reintentar, aprobar, transiciones y PDF. Solo la
dueña toca su candidatura (RLS «propia»: para las demás no existe). Ninguna operación llama al modelo
salvo encolar `candidatura` (crear y reintentar)."""
import logging
from datetime import date

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from horma.config import ajustes
from horma.flows.candidatura import aviso_de_oferta, texto_oferta
from horma.schemas.candidatura import (
    ESTADOS,
    TransicionInvalida,
    aviso_de_error,
    hay_aviso_pendiente,
    transicion,
)
from horma.tools.avisos_vigentes import avisos_vigentes
from horma.tools.generar_pdf import generar_pdf
from horma.tools.medir_ats import errores_ats
from horma.tools.muletillas_ia import errores_muletillas
from horma.tools.rasgos_personales import rasgos_personales
from horma.tools.validar_cv import validar_cv
from horma.tools.verificar_trazabilidad import FORMULAS_CORTESIA, verificar_trazabilidad
from horma.web import checkpointer
from horma.web.db import sesion_de
from horma.web.repositories import candidaturas as repo
from horma.web.repositories import ofertas as repo_ofertas
from horma.web.repositories import perfiles, tareas

log = logging.getLogger("horma.candidaturas")


class ErrorCandidatura(Exception):
    def __init__(self, estado: int, motivo: str):
        super().__init__(motivo)
        self.estado, self.motivo = estado, motivo


def _cargar(s, candidatura_id: int) -> dict:
    c = repo.fila(s, candidatura_id)
    if c is None:
        raise ErrorCandidatura(404, "No existe esa candidatura")
    return c


def _en_borrador(c: dict) -> None:
    if c["estado"] != "borrador":
        raise ErrorCandidatura(409, "Solo se puede hacer mientras la candidatura está en borrador.")


def _borrador_desfasado(s, c: dict) -> bool:
    """Un borrador ya preparado con una versión del perfil anterior a la vigente (RF-5.1f)."""
    vigente = perfiles.vigente(s)
    return (c["estado"] == "borrador" and c["preparacion"] in ("lista", "pendiente_de_ti")
            and bool(c["perfil_version"]) and vigente is not None
            and c["perfil_version"] < vigente["version"])


def _preparada(c: dict) -> None:
    if c["preparacion"] not in ("lista", "pendiente_de_ti"):
        raise ErrorCandidatura(409, "La candidatura aún no está preparada.")


def _transicionar(s, usuaria_id: int, c: dict, destino: str, **datos) -> None:
    """Valida con `transicion()` (409 si no es legal) y deja el evento; el cambio lo hace quien llama."""
    try:
        transicion(c["estado"], destino, datos.get("motivo"), fecha=datos.get("fecha"),
                   canal=datos.get("canal"), canal_otro=datos.get("canal_otro"))
    except TransicionInvalida as e:
        raise ErrorCandidatura(409, str(e)) from e
    repo.registrar_evento(s, usuaria_id, c["id"], de=c["estado"], a=destino, motivo=datos.get("motivo"),
                          canal=datos.get("canal"))


# --- crear, tablero y detalle ------------------------------------------------------------------
def crear(engine: Engine, usuaria_id: int, oferta_id: int, repetir: bool = False) -> dict:
    a = ajustes()
    with sesion_de(engine, usuaria_id) as s:
        if not repo.oferta_procesada(s, oferta_id):
            raise ErrorCandidatura(404, "No existe esa oferta")
        if perfiles.vigente(s) is None:
            raise ErrorCandidatura(409, "Aún no tienes un perfil: sube un CV primero.")
        if repo.hay_viva(s, oferta_id):
            raise ErrorCandidatura(409, "Ya tienes una candidatura abierta para esta oferta.")
        previa = None if repetir else repo.cerrada_previa(s, oferta_id)
        if previa:
            motivo = f" (motivo: {previa['motivo_cierre']})" if previa["motivo_cierre"] else ""
            raise ErrorCandidatura(409, f"Ya preparaste el CV y la carta para esta oferta el "
                                        f"{previa['actualizado_en']:%d/%m/%Y} y se cerró{motivo}. "
                                        "Revisa Candidaturas > Cerradas o confirma para preparar otra.")
        try:
            with s.begin_nested():
                candidatura_id = repo.crear(s, usuaria_id, oferta_id)
        except IntegrityError as e:  # dos peticiones a la vez: el índice único parcial manda
            raise ErrorCandidatura(409, "Ya tienes una candidatura abierta para esta oferta.") from e
        tarea = tareas.encolar(s, usuaria_id, "candidatura", candidatura_id, a.tope_coste_candidatura,
                               a.tope_reintentos_tarea)
    return {"id": candidatura_id, "tarea_id": tarea}


def tablero(engine: Engine, usuaria_id: int) -> dict:
    with sesion_de(engine, usuaria_id) as s:
        filas = repo.tablero(s)
    columnas = {e: [] for e in ESTADOS}
    for f in filas:
        columnas[f["estado"]].append({
            "id": f["id"], "oferta_id": f["oferta_id"], "titulo": f["titulo"], "empresa": f["empresa"],
            "estado": f["estado"], "preparacion": f["preparacion"], "motivo_cierre": f["motivo_cierre"],
            "actualizado_en": f["actualizado_en"],
            "te_toca_revisar": f["preparacion"] == "pendiente_de_ti"})
    return {"total": len(filas), "columnas": [{"estado": e, "candidaturas": columnas[e]} for e in ESTADOS]}


def detalle(engine: Engine, usuaria_id: int, candidatura_id: int) -> dict:
    with sesion_de(engine, usuaria_id) as s:
        f = repo.detalle(s, candidatura_id)
        if f is None:
            raise ErrorCandidatura(404, "No existe esa candidatura")
        eventos = repo.eventos(s, candidatura_id)
    union = ("oferta_titulo", "oferta_empresa", "cv_base_nombre", "cv_base_desfasado", "cv_pdf",
             "carta_pdf")
    return {**{k: v for k, v in f.items() if k not in union}, "desfasada": bool(f["desfasada"]),
            "oferta": {"id": f["oferta_id"], "titulo": f["oferta_titulo"], "empresa": f["oferta_empresa"]},
            "cv_base": ({"id": f["cv_base_id"], "nombre": f["cv_base_nombre"],
                         "desfasado": bool(f["cv_base_desfasado"])} if f["cv_base_id"] else None),
            "eventos": eventos}


# --- edición -----------------------------------------------------------------------------------
def _avisos(s, c: dict, cv: str, carta: str) -> list[dict]:
    """Recalcula los avisos como el flujo y sin llamar al modelo: los errores de las herramientas de código
    (trazabilidad, rasgos personales, muletillas de IA, estructura del CV y ATS)
    y los problemas del juez cuya frase sigue en el texto (también los del documento que no se editó).
    Lo que ella escribe no tiene traza y sale como aviso para que lo revise (RF-3.8)."""
    perfil = perfiles.por_version(s, c["perfil_version"]) if c["perfil_version"] else None
    maestro = (perfil or {}).get("cv_maestro") or ""
    base = repo.contenido_cv_base(s, c["cv_base_id"])
    oferta = repo_ofertas.completas(s, [c["oferta_id"]]).get(c["oferta_id"])
    fuentes_cv = [x for x in (maestro, base) if x]
    fuentes_carta = [*fuentes_cv, *([texto_oferta(oferta)] if oferta else [])]
    errores_cv = [f"Formato del CV para ATS: {x}" for x in errores_ats(cv)]
    errores_cv += verificar_trazabilidad(cv, c["cv_traza"], fuentes_cv or [""])
    errores_cv += [f"Rasgo personal en el CV: {x}" for x in rasgos_personales(cv)]
    errores_cv += errores_muletillas("cv", cv)
    errores_cv += [f"Estructura del CV: {x}" for x in validar_cv(cv, maestro or None)]
    errores_carta = verificar_trazabilidad(
        carta, c["carta_traza"], fuentes_carta or [""], formulas_cortesia=FORMULAS_CORTESIA, por_frase=True)
    errores_carta += [f"Rasgo personal en la carta: {x}" for x in rasgos_personales(carta)]
    errores_carta += errores_muletillas("carta", carta)
    de_la_oferta = aviso_de_oferta(oferta) if oferta else None
    avisos = [*([de_la_oferta] if de_la_oferta else []),
              *(aviso_de_error("cv", x, cv) for x in errores_cv),
              *(aviso_de_error("carta", x, carta) for x in errores_carta),
              *avisos_vigentes("cv", cv, c["problemas_juez"]),
              *avisos_vigentes("carta", carta, c["problemas_juez"])]
    unicos = {(a.documento, a.frase, a.mensaje): a for a in avisos}
    return [a.model_dump(mode="json") for a in unicos.values()]


def editar(engine: Engine, usuaria_id: int, candidatura_id: int, cv: str | None, carta: str | None) -> dict:
    with sesion_de(engine, usuaria_id) as s:
        c = _cargar(s, candidatura_id)
        _en_borrador(c)
        _preparada(c)
        cv_nuevo = c["cv_contenido"] if cv is None else cv
        carta_nueva = c["carta_contenido"] if carta is None else carta
        avisos = _avisos(s, c, cv_nuevo, carta_nueva)
        preparacion = "pendiente_de_ti" if hay_aviso_pendiente(avisos) else "lista"
        repo.guardar_edicion(s, candidatura_id, cv_nuevo, carta_nueva, avisos, preparacion)
    return {"id": candidatura_id, "avisos": avisos, "preparacion": preparacion}


# --- aprobar y transiciones --------------------------------------------------------------------
def aprobar(engine: Engine, usuaria_id: int, candidatura_id: int) -> dict:
    """Los avisos no bloquean: pulsar «Aprobar y descargar» cuenta como haberlos revisado (RF-3.8a).
    Primero se guarda la aprobación; después se reanuda el flujo (`entregar`) con el texto de la fila y se
    guardan los PDF. Si la reanudación falla, la aprobación sigue en pie y las descargas generan el PDF al
    momento (RF-4.3d)."""
    with sesion_de(engine, usuaria_id) as s:
        c = _cargar(s, candidatura_id)
        _en_borrador(c)
        _preparada(c)
        _transicionar(s, usuaria_id, c, "aprobada")
        repo.aprobar(s, candidatura_id)
        oferta = repo_ofertas.completas(s, [c["oferta_id"]]).get(c["oferta_id"])
    _entregar(engine, usuaria_id, c, oferta)
    return {"id": candidatura_id, "estado": "aprobada"}


def _entregar(engine: Engine, usuaria_id: int, c: dict, oferta) -> None:
    """Reanuda con el texto de la fila (lo que la usuaria aprobó) y guarda los PDF. Nunca rompe la
    aprobación; en el log solo quedan el paso y el tipo del error, sin texto."""
    cid = c["id"]
    try:
        textos = {"cv_contenido": c["cv_contenido"], "carta_contenido": c["carta_contenido"]}
        estado = {**textos, "oferta": oferta.model_dump(mode="json") if oferta else {},
                  "en_pausa": "entregar"}
        r = checkpointer.flujo_candidatura(engine).reanudar(checkpointer.hilo_de(cid), textos, estado=estado)
        with sesion_de(engine, usuaria_id) as s:
            repo.guardar_pdfs(s, cid, r["cv_pdf"], r["carta_pdf"])
    except Exception as e:  # noqa: BLE001 - la aprobación ya está guardada
        paso = getattr(e, "paso", "entregar")
        causa = getattr(e, "causa", e)
        log.warning("candidatura %s: falló la entrega en el paso %s (%s); los PDF se generan al descargar",
                    cid, paso, type(causa).__name__)
    finally:
        checkpointer.borrar_hilo(engine, cid)


def reintentar(engine: Engine, usuaria_id: int, candidatura_id: int) -> dict:
    """Vuelve a lanzar la preparación de esta misma candidatura, con el mismo tope de coste (RF-3.8e).
    Vale cuando la preparación ha fallado y, en un borrador, cuando se preparó con una versión anterior
    del perfil (RF-5.1f): se rehace con la vigente y se pierde lo que ella hubiera editado."""
    a = ajustes()
    with sesion_de(engine, usuaria_id) as s:
        c = _cargar(s, candidatura_id)
        if c["preparacion"] != "error" and not _borrador_desfasado(s, c):
            raise ErrorCandidatura(409, "Solo se puede volver a preparar cuando la preparación ha fallado "
                                        "o el borrador es de una versión anterior de tu perfil.")
        if tareas.sin_terminar(s, "candidatura", candidatura_id):
            raise ErrorCandidatura(409, "Ya se está preparando.")
        repo.reiniciar_preparacion(s, candidatura_id)
        tarea = tareas.encolar(s, usuaria_id, "candidatura", candidatura_id, a.tope_coste_candidatura,
                               a.tope_reintentos_tarea)
    checkpointer.borrar_hilo(engine, candidatura_id)  # empieza de cero, sin la vuelta anterior
    return {"id": candidatura_id, "tarea_id": tarea}


def marcar_enviada(engine: Engine, usuaria_id: int, candidatura_id: int, fecha: date | None,
                   canal: str | None, canal_otro: str | None) -> dict:
    """Sin fecha, la de hoy; el canal es opcional (RF-3.8b)."""
    fecha = fecha or date.today()
    with sesion_de(engine, usuaria_id) as s:
        c = _cargar(s, candidatura_id)
        _transicionar(s, usuaria_id, c, "enviada", fecha=fecha, canal=canal, canal_otro=canal_otro)
        repo.marcar_enviada(s, candidatura_id, fecha, canal, canal_otro)
    return {"id": candidatura_id, "estado": "enviada"}


def pasar_a_entrevista(engine: Engine, usuaria_id: int, candidatura_id: int) -> dict:
    with sesion_de(engine, usuaria_id) as s:
        c = _cargar(s, candidatura_id)
        _transicionar(s, usuaria_id, c, "entrevista")
        repo.cambiar_estado(s, candidatura_id, "entrevista")
    return {"id": candidatura_id, "estado": "entrevista"}


def cerrar(engine: Engine, usuaria_id: int, candidatura_id: int, motivo: str) -> dict:
    with sesion_de(engine, usuaria_id) as s:
        c = _cargar(s, candidatura_id)
        _transicionar(s, usuaria_id, c, "cerrada", motivo=motivo)
        repo.cambiar_estado(s, candidatura_id, "cerrada", motivo)
    checkpointer.borrar_hilo(engine, candidatura_id)
    return {"id": candidatura_id, "estado": "cerrada", "motivo_cierre": motivo}


# --- descargas ---------------------------------------------------------------------------------
def documento_pdf(engine: Engine, usuaria_id: int, candidatura_id: int, cual: str) -> bytes:
    """PDF del CV adaptado o de la carta. Solo desde que se aprobó (RF-3.8c)."""
    with sesion_de(engine, usuaria_id) as s:
        c = repo.detalle(s, candidatura_id)
        if c is None:
            raise ErrorCandidatura(404, "No existe esa candidatura")
        aprobada = c["estado"] in ("aprobada", "enviada", "entrevista") or (
            c["estado"] == "cerrada" and repo.fue_aprobada(s, candidatura_id))
        guardado = repo.pdf_guardado(s, candidatura_id, cual) if aprobada else None
    if not aprobada:
        raise ErrorCandidatura(403, "Los PDF se pueden descargar cuando apruebas la candidatura.")
    if guardado is not None:
        return guardado
    texto = c["cv_contenido"] if cual == "cv" else c["carta_contenido"]
    titulo = f"{'CV' if cual == 'cv' else 'Carta de presentación'} · {c['oferta_titulo'] or 'oferta'}"
    return generar_pdf(texto, titulo)
