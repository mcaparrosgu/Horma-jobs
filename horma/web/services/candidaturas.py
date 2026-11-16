"""Servicio de candidaturas (fase 3): crear, editar, guardar encima del CV base, aprobar, transiciones,
PDF y respuesta de la empresa. Solo la dueña toca su candidatura (RLS «propia»: para las demás no existe).
Ninguna de estas operaciones llama al modelo salvo encolar `candidatura` y `clasificar_respuesta`."""
from datetime import date

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from horma.config import ajustes
from horma.flows.candidatura import texto_oferta
from horma.schemas.candidatura import ESTADOS, TransicionInvalida, transicion
from horma.tools.generar_pdf import generar_pdf
from horma.tools.medir_ats import errores_ats
from horma.tools.rasgos_personales import rasgos_personales
from horma.tools.verificar_trazabilidad import FORMULAS_CORTESIA, verificar_trazabilidad
from horma.web.db import sesion_de
from horma.web.repositories import candidaturas as repo
from horma.web.repositories import cv as repo_cv
from horma.web.repositories import ofertas as repo_ofertas
from horma.web.repositories import perfiles, tareas

PREFIJO_DESFASADO = "El CV base «"  # aviso que escribe el flujo; al editar se conserva


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
                          canal=datos.get("canal"), origen=datos.get("origen", "usuaria"),
                          etiqueta_respuesta=datos.get("etiqueta_respuesta"))


# --- crear, tablero y detalle ------------------------------------------------------------------
def crear(engine: Engine, usuaria_id: int, oferta_id: int, repetir: bool = False) -> dict:
    a = ajustes()
    with sesion_de(engine, usuaria_id) as s:
        if not repo.oferta_procesada(s, oferta_id):
            raise ErrorCandidatura(404, "No existe esa oferta")
        if perfiles.vigente(s) is None:
            raise ErrorCandidatura(409, "Aún no tienes un perfil: sube un CV primero.")
        if not any(f["estado"] == "hecho" for f in perfiles.listar_cv_base(s)):
            raise ErrorCandidatura(409, "Genera un CV base primero: sin él no se puede preparar.")
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
    clasificando = f.pop("respuesta_pendiente") is not None  # el correo pegado nunca sale a la pantalla
    union = ("oferta_titulo", "oferta_empresa", "cv_base_nombre", "cv_base_desfasado")
    return {**{k: v for k, v in f.items() if k not in union},
            "oferta": {"id": f["oferta_id"], "titulo": f["oferta_titulo"], "empresa": f["oferta_empresa"]},
            "cv_base": ({"id": f["cv_base_id"], "nombre": f["cv_base_nombre"],
                         "desfasado": bool(f["cv_base_desfasado"])} if f["cv_base_id"] else None),
            "clasificando": clasificando, "eventos": eventos}


# --- edición -----------------------------------------------------------------------------------
def _avisos(s, c: dict, cv: str, carta: str) -> list[str]:
    """Recalcula los avisos con las mismas herramientas que el flujo y sin llamar al modelo: lo que ella
    escribe no tiene traza y sale como aviso para que lo revise (RF-3.8)."""
    perfil = perfiles.por_version(s, c["perfil_version"]) if c["perfil_version"] else None
    maestro = (perfil or {}).get("cv_maestro") or ""
    base = repo.contenido_cv_base(s, c["cv_base_id"])
    oferta = repo_ofertas.completas(s, [c["oferta_id"]]).get(c["oferta_id"])
    fuentes_cv = [x for x in (maestro, base) if x]
    fuentes_carta = [*fuentes_cv, *([texto_oferta(oferta)] if oferta else [])]
    avisos = [a for a in c["avisos"] if a.startswith(PREFIJO_DESFASADO)]
    avisos += [f"Formato del CV para ATS: {x}" for x in errores_ats(cv)]
    avisos += [f"CV: {x}" for x in verificar_trazabilidad(cv, c["cv_traza"], fuentes_cv or [""])]
    avisos += [f"CV, rasgo personal: {x}" for x in rasgos_personales(cv)]
    avisos += [f"Carta: {x}" for x in verificar_trazabilidad(
        carta, c["carta_traza"], fuentes_carta or [""], formulas_cortesia=FORMULAS_CORTESIA, por_frase=True)]
    avisos += [f"Carta, rasgo personal: {x}" for x in rasgos_personales(carta)]
    return list(dict.fromkeys(avisos))


def editar(engine: Engine, usuaria_id: int, candidatura_id: int, cv: str | None, carta: str | None) -> dict:
    with sesion_de(engine, usuaria_id) as s:
        c = _cargar(s, candidatura_id)
        _en_borrador(c)
        _preparada(c)
        cv_nuevo = c["cv_contenido"] if cv is None else cv
        carta_nueva = c["carta_contenido"] if carta is None else carta
        avisos = _avisos(s, c, cv_nuevo, carta_nueva)
        preparacion = "pendiente_de_ti" if avisos else "lista"
        repo.guardar_edicion(s, candidatura_id, cv_nuevo, carta_nueva, avisos, preparacion)
    return {"id": candidatura_id, "avisos": avisos, "preparacion": preparacion}


def guardar_cv_base(engine: Engine, usuaria_id: int, candidatura_id: int, nombre: str) -> dict:
    """Guarda el CV adaptado encima del CV base del que partió (RF-3.8). Es texto suyo: no se vuelve a
    comprobar contra el CV, pero el nombre es único y la versión anterior queda en el historial."""
    with sesion_de(engine, usuaria_id) as s:
        c = _cargar(s, candidatura_id)
        _en_borrador(c)
        _preparada(c)
        if c["cv_base_id"] is None or not c["cv_contenido"].strip():
            raise ErrorCandidatura(409, "No hay un CV adaptado que guardar.")
        if repo_cv.nombre_en_uso(s, nombre, excepto_base=c["cv_base_id"]):
            raise ErrorCandidatura(409, "Ya tienes un CV con ese nombre.")
        if not perfiles.editar_cv_base(s, c["cv_base_id"], nombre, c["cv_contenido"],
                                       origen="candidatura", candidatura_id=candidatura_id):
            raise ErrorCandidatura(404, "El CV base ya no existe.")
        repo.registrar_evento(s, usuaria_id, candidatura_id, tipo="cv_base_guardado", motivo=nombre)
    return {"id": candidatura_id, "cv_base_id": c["cv_base_id"], "nombre": nombre}


# --- aprobar y transiciones --------------------------------------------------------------------
def aprobar(engine: Engine, usuaria_id: int, candidatura_id: int, documento: str,
            cv_estetico_id: int | None, avisos_revisados: bool) -> dict:
    with sesion_de(engine, usuaria_id) as s:
        c = _cargar(s, candidatura_id)
        _en_borrador(c)
        _preparada(c)
        if (c["avisos"] or c["preparacion"] == "pendiente_de_ti") and not avisos_revisados:
            raise ErrorCandidatura(400, "Revisa los avisos y márcalos como revisados antes de aprobar.")
        if documento == "estetico":
            if cv_estetico_id is None or not repo.cv_estetico_valido(s, cv_estetico_id):
                raise ErrorCandidatura(422, "Elige uno de tus CV estéticos.")
        else:
            cv_estetico_id = None
        _transicionar(s, usuaria_id, c, "aprobada")
        repo.aprobar(s, candidatura_id, documento, cv_estetico_id)
    return {"id": candidatura_id, "estado": "aprobada"}


def marcar_enviada(engine: Engine, usuaria_id: int, candidatura_id: int, fecha: date, canal: str,
                   canal_otro: str | None) -> dict:
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
    return {"id": candidatura_id, "estado": "cerrada", "motivo_cierre": motivo}


# --- descargas ---------------------------------------------------------------------------------
def documento_pdf(engine: Engine, usuaria_id: int, candidatura_id: int, cual: str) -> tuple[str, bytes | int]:
    """`("pdf", bytes)` o `("estetico", id del CV estético)`. Solo desde que se aprobó (RF-3.8c)."""
    with sesion_de(engine, usuaria_id) as s:
        c = repo.detalle(s, candidatura_id)
    if c is None:
        raise ErrorCandidatura(404, "No existe esa candidatura")
    if c["documento"] is None:
        raise ErrorCandidatura(403, "Los PDF se pueden descargar cuando apruebas la candidatura.")
    if cual == "cv" and c["documento"] == "estetico":
        if c["cv_estetico_id"] is None:
            raise ErrorCandidatura(404, "El CV estético que elegiste ya no existe.")
        return "estetico", c["cv_estetico_id"]
    texto = c["cv_contenido"] if cual == "cv" else c["carta_contenido"]
    titulo = f"{'CV' if cual == 'cv' else 'Carta de presentación'} · {c['oferta_titulo'] or 'oferta'}"
    return "pdf", generar_pdf(texto, titulo)


# --- respuesta de la empresa -------------------------------------------------------------------
def pegar_respuesta(engine: Engine, usuaria_id: int, candidatura_id: int, texto: str) -> dict:
    a = ajustes()
    with sesion_de(engine, usuaria_id) as s:
        c = _cargar(s, candidatura_id)
        if c["estado"] == "cerrada":
            raise ErrorCandidatura(409, "Una candidatura cerrada no admite más cambios.")
        en_cola = tareas.sin_terminar(s, "clasificar_respuesta", candidatura_id)
        if c["respuesta_pendiente"] is not None or en_cola:
            raise ErrorCandidatura(409, "Ya se está clasificando una respuesta.")
        repo.guardar_respuesta_pendiente(s, candidatura_id, texto)
        tarea = tareas.encolar(s, usuaria_id, "clasificar_respuesta", candidatura_id,
                               a.tope_coste_respuesta, a.tope_reintentos_tarea)
    return {"id": candidatura_id, "tarea_id": tarea}


def confirmar_respuesta(engine: Engine, usuaria_id: int, candidatura_id: int) -> dict:
    """Aplica la propuesta si sigue siendo legal desde el estado de ahora."""
    with sesion_de(engine, usuaria_id) as s:
        c = _cargar(s, candidatura_id)
        p = c["respuesta_propuesta"]
        if not p or p["tipo"] == "ninguna":
            raise ErrorCandidatura(409, "No hay ninguna propuesta que confirmar.")
        etiqueta = p.get("etiqueta")
        if p["tipo"] == "nota":
            repo.registrar_evento(s, usuaria_id, candidatura_id, tipo="nota", origen="respuesta",
                                  etiqueta_respuesta=etiqueta)
        else:
            _transicionar(s, usuaria_id, c, p["destino"], motivo=p.get("motivo"), origen="respuesta",
                          etiqueta_respuesta=etiqueta)
            repo.cambiar_estado(s, candidatura_id, p["destino"], p.get("motivo"))
        repo.borrar_propuesta(s, candidatura_id)
    return {"id": candidatura_id}


def descartar_respuesta(engine: Engine, usuaria_id: int, candidatura_id: int) -> dict:
    with sesion_de(engine, usuaria_id) as s:
        _cargar(s, candidatura_id)
        repo.borrar_propuesta(s, candidatura_id)
    return {"id": candidatura_id}
