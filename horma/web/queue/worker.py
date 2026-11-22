"""Worker: ejecuta las tareas de la cola con tope de coste y de reintentos (RT-14).

Tipos de tarea (la carga es siempre un id, nunca texto):
- `procesar_oferta` (catálogo, modo sistema) y `calificar_fuente` (fase 1).
- `perfilar` (id de una versión nueva y pendiente del perfil), `clasificar_perfil` (id de una versión
  copiada y pendiente), `recomendar` (id de la versión del perfil con la que se
  trabaja). Las de una usuaria se ejecutan con su sesión (RLS); las demás, en modo sistema.
- `puntuar_propias` (fase 5; id de la usuaria): puntúa las ofertas que ella añadió.
- `puntuar_una` (fase 8; id de la oferta): «Puntuar ahora», puntúa solo esa oferta.
Fase 8 (RF-8.7): cada tarea sube su `progreso` (nunca baja) y `recomendar` guarda cada tanda al terminarla.
- `candidatura` (fase 3; id de la candidatura): CV y carta para una oferta.
- `leer_url` (fase 5; id de la importación): lee la página con el proveedor y crea la oferta propia.
- `analizar_estilo` (fase 5; id de la usuaria): guía de estilo con sus CV y cartas.
El tope de coste vale para cualquier tarea: se corta en la puerta única (`metricas.capturar(tope=…)`) y
una tarea que lo supera queda en `error` sin reintento y sin guardar su resultado.
Aparcadas (RF-10.11d): `generar_cv_base`, `regenerar_cv_base` y `extraer_oferta` ya no existen aquí.
"""
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import Engine

from horma.config import ajustes
from horma.flows import (
    analizar_estilo,
    calificar_fuente,
    clasificar_perfil,
    perfilar,
    procesar_oferta,
    recomendar,
)
from horma.llm import metricas
from horma.llm.proveedor import Proveedor
from horma.logs import configurar_logs, motivo_seguro
from horma.schemas.estilo import GuiaEstilo
from horma.schemas.fuente import CalificacionFuente
from horma.schemas.oferta import Oferta
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias
from horma.tools import descargar, dominio
from horma.tools.buscar_ofertas import buscar_ofertas
from horma.tools.huella_perfil import huella_compatibilidad
from horma.tools.leer_pagina import MENSAJE as MOTIVO_LECTURA
from horma.tools.leer_pagina import leer_pagina
from horma.tools.validar_url import validar_url
from horma.web import alertas, checkpointer
from horma.web.db import motor, sesion_de, sesion_sistema
from horma.web.queue import cola
from horma.web.repositories import candidaturas as repo_candidaturas
from horma.web.repositories import descartes as repo_descartes
from horma.web.repositories import estilo as repo_estilo
from horma.web.repositories import importaciones as repo_importaciones
from horma.web.repositories import ingesta as repo_ingesta
from horma.web.repositories import matches as repo_matches
from horma.web.repositories import ofertas as repo_ofertas
from horma.web.repositories import perfiles as repo_perfiles
from horma.web.repositories import tareas as repo_tareas
from horma.web.services import estilo as servicio_estilo
from horma.web.services import ofertas as servicio_ofertas
from horma.web.services import presupuesto

log = logging.getLogger("horma.worker")


@dataclass
class Dependencias:
    proveedor: Proveedor | None
    resolver: dominio.Resolvedor | None
    descargador: descargar.Descargador
    engine: Engine | None = None
    entidad_id: int | None = None
    lector: Callable[[str], str] = leer_pagina
    usuaria_id: int | None = None
    tarea_id: int | None = None
    avanzar: Callable[[int], None] | None = None  # RF-8.7: sube el avance de la tarea (nunca baja)


def con_avance(flujo, d: Dependencias, desde: int = 0):
    """Avance por pasos hechos sobre pasos del flujo, hasta el 95 % (al terminar salta a 100). `desde` es el
    punto de partida (p. ej. 20 % cuando la lectura de la URL ya está hecha)."""
    if d.avanzar is None:
        return flujo
    total, hechos = max(1, len(flujo.pasos())), 0

    def al_paso(_paso: str) -> None:
        nonlocal hechos
        hechos += 1
        d.avanzar(desde + round(min(hechos, total) / total * (95 - desde)))

    flujo.al_paso = al_paso
    return flujo


class _ProcesarOferta:
    def cargar(self, s, tarea: dict) -> dict:
        return repo_ofertas.para_procesar(s, tarea["entidad_id"])

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        flujo = procesar_oferta.crear(proveedor=d.proveedor, resolver=d.resolver)
        return con_avance(flujo, d, desde=20 if estado.get("url") else 0).run(estado)  # con URL, leerla fue el 20 %  # noqa: E501

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        repo_ofertas.guardar(s, tarea["entidad_id"], Oferta.model_validate(estado["oferta"]),
                             [tuple(o) for o in estado["origenes"]])
        _encadenar(s, "procesar_oferta", tarea)

    def marcar_error(self, s, tarea: dict, motivo: str) -> None:
        repo_ofertas.marcar_error(s, tarea["entidad_id"], motivo)


def _encolar_puntuar_propias(s, usuaria_id: int) -> None:
    """Una sola tarea pendiente por usuaria: recoge todas las propias sin nota para su perfil vigente
    (RF-5.3d). La carga es el id de la usuaria porque el worker, en modo sistema, no ve su perfil."""
    if not repo_tareas.pendiente(s, "puntuar_propias", usuaria_id):
        a = ajustes()
        try:
            presupuesto.encolar(s, usuaria_id, "puntuar_propias", usuaria_id, a.tope_coste_puntuar_propias,
                                a.tope_reintentos_tarea)
        except presupuesto.SinPresupuesto:
            pass  # sin presupuesto no se puntúa hoy (RF-10.9c)


def _propia_procesada(s, tarea: dict) -> None:
    """Una oferta propia recién analizada se puntúa sola (RF-5.3d)."""
    if (usuaria := repo_ofertas.dueña(s, tarea["entidad_id"])) is not None:
        _encolar_puntuar_propias(s, usuaria)


def _puntuar_si_hay_propias(s, tarea: dict) -> None:
    """Perfil nuevo: las ofertas propias añadidas antes se puntúan con su versión."""
    if repo_ofertas.hay_propias(s):
        _encolar_puntuar_propias(s, tarea["usuaria_id"])


def _estilo_la_primera_vez(s, tarea: dict) -> None:
    servicio_estilo.encolar_si_no_hay_guia(s, tarea["usuaria_id"])  # RF-5.6d


# Qué se encola al terminar cada tarea, en un solo sitio (RF-10.11). Cada paso decide si le toca.
ENCADENADOS = {
    "procesar_oferta": [_propia_procesada],
    "perfilar": [_puntuar_si_hay_propias, _estilo_la_primera_vez],
    "clasificar_perfil": [_puntuar_si_hay_propias],
}


def _encadenar(s, tipo: str, tarea: dict) -> None:
    for siguiente in ENCADENADOS.get(tipo, []):
        siguiente(s, tarea)


class _CalificarFuente:
    def cargar(self, s, tarea: dict) -> dict:
        return {"url": repo_ingesta.calificacion(s, tarea["entidad_id"])["url"]}

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        flujo = calificar_fuente.crear(proveedor=d.proveedor, descargador=d.descargador)
        return con_avance(flujo, d).run(estado)

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        repo_ingesta.guardar_calificacion(
            s, tarea["entidad_id"], CalificacionFuente.model_validate(estado["calificacion"]))

    def marcar_error(self, s, tarea: dict, motivo: str) -> None:
        repo_ingesta.marcar_error_calificacion(s, tarea["entidad_id"], motivo)


def _perfil_de_la_tarea(s, tarea: dict, *, hecha: bool = False) -> dict:
    fila = repo_perfiles.perfil_fila(s, tarea["entidad_id"])
    if fila is None:
        raise ValueError(f"no existe el perfil {tarea['entidad_id']} de esta usuaria")
    if hecha and fila["estado"] != "hecha":
        raise ValueError(f"el perfil {fila['version']} no está listo (estado: {fila['estado']})")
    return fila


class _Perfilar:
    """Lee todos los CV de la usuaria y rellena la versión reservada: perfil, orígenes y las
    preferencias que salen del CV."""

    def cargar(self, s, tarea: dict) -> dict:
        fila = _perfil_de_la_tarea(s, tarea)
        cvs = repo_perfiles.cvs_fuente(s)
        if not cvs:
            raise ValueError("la usuaria no tiene ningún CV para perfilar")
        return {"cvs": cvs, "_version": fila["version"],
                "de_usuaria": repo_perfiles.lo_de_la_usuaria(s, tarea["usuaria_id"])}

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        flujo = con_avance(perfilar.crear(proveedor=d.proveedor), d)
        return {**flujo.run(estado), "_version": estado["_version"]}

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        perfil = Perfil.model_validate({**estado["perfil"], "version": estado["_version"]})
        repo_perfiles.guardar_perfil(s, tarea["usuaria_id"], tarea["entidad_id"], perfil,
                                     estado["cv_maestro"])
        repo_perfiles.aplicar_preferencias_del_cv(
            s, tarea["usuaria_id"], Preferencias.model_validate(estado["preferencias"]))
        _encadenar(s, "perfilar", tarea)

    def marcar_error(self, s, tarea: dict, motivo: str) -> None:
        repo_perfiles.marcar_error_perfil(s, tarea["entidad_id"], motivo)


class _ClasificarPerfil:
    """Vuelve a clasificar una versión copiada (tras una respuesta o corrección de la usuaria)."""

    def cargar(self, s, tarea: dict) -> dict:
        fila = _perfil_de_la_tarea(s, tarea)
        return {"perfil": repo_perfiles.perfil_modelo(fila).model_dump(mode="json")}

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        return con_avance(clasificar_perfil.crear(proveedor=d.proveedor), d).run(estado)

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        perfil = Perfil.model_validate({**estado["perfil"], "taxonomia": estado["taxonomia"]})
        repo_perfiles.guardar_perfil(s, tarea["usuaria_id"], tarea["entidad_id"], perfil)
        repo_perfiles.aplicar_puestos_del_cv(s, tarea["usuaria_id"], estado.get("puestos") or [])
        _encadenar(s, "clasificar_perfil", tarea)

    def marcar_error(self, s, tarea: dict, motivo: str) -> None:
        repo_perfiles.marcar_error_perfil(s, tarea["entidad_id"], motivo)


class _Recomendar:
    """Puntúa las ofertas que pasan el filtro y aún no tienen nota para esta versión del perfil."""

    def cargar(self, s, tarea: dict) -> dict:
        fila = _perfil_de_la_tarea(s, tarea, hecha=True)
        perfil = repo_perfiles.perfil_modelo(fila)
        # Lo que se puntúa no depende de la vista (RF-8.4d): siempre 40-100 y de más a menos parecido.
        prefs = repo_perfiles.preferencias(s).model_copy(
            update={"rango_min": 40, "rango_max": 100, "orden": "compatibles"})
        huella = huella_compatibilidad(perfil)
        ya = repo_matches.puntuadas(s, huella)
        consulta = buscar_ofertas(prefs, perfil.taxonomia, excluir_ids=ya + repo_descartes.ids(s),  # RF-8.5d
                                  limite=recomendar.MAX_TANDAS * recomendar.TANDA)
        ids = repo_matches.ids_candidatas(s, consulta)
        ofertas = repo_ofertas.completas(s, ids)
        return {"perfil": perfil.model_dump(mode="json"), "preferencias": prefs.model_dump(mode="json"),
                "candidatas": [{"oferta_id": i, "oferta": ofertas[i].model_dump(mode="json")}
                               for i in ids if i in ofertas],
                "ya_puntuadas": ya, "_version": fila["version"], "_huella": huella}

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        def al_tanda(nuevas: list[dict], hechas: int, previstas: int) -> None:
            """Cada tanda se guarda al terminarla, en su propia transacción, y la barra avanza (RF-8.7c-e):
            si una tanda posterior falla, lo ya guardado se queda."""
            with sesion_de(d.engine, d.usuaria_id) as s:
                repo_matches.guardar(s, d.usuaria_id, estado["_version"], nuevas, estado["_huella"])
                repo_tareas.avanzar(s, d.tarea_id, min(99, round(hechas / max(1, previstas) * 100)))
        return recomendar.crear(proveedor=d.proveedor, al_tanda=al_tanda).run(estado)

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        repo_matches.guardar(s, tarea["usuaria_id"], estado["_version"], estado["recomendaciones"],
                             estado["_huella"])

    def marcar_error(self, s, tarea: dict, motivo: str) -> None:
        """Sin fila propia: el motivo queda en la tarea."""


class _PuntuarPropias(_Recomendar):
    """Puntúa TODAS las ofertas propias de la usuaria sin nota para su perfil vigente, sin filtros ni
    rango (RF-5.3d, RF-5.3e). Por tandas de 30 con el mismo flujo que `recomendar`. Entidad = id de la
    usuaria. Sin perfil o sin ofertas pendientes no hace nada (y no llama al modelo)."""

    def cargar(self, s, tarea: dict) -> dict:
        fila = repo_perfiles.vigente(s)
        if fila is None:
            return {"candidatas": []}
        perfil = repo_perfiles.perfil_modelo(fila)
        prefs = repo_perfiles.preferencias(s).model_copy(update={"rango_min": 0, "rango_max": 100})
        huella = huella_compatibilidad(perfil)
        ids = repo_ofertas.propias_sin_nota(s, tarea["usuaria_id"], huella,
                                            recomendar.MAX_TANDAS * recomendar.TANDA)
        ofertas = repo_ofertas.completas(s, ids)
        return {"perfil": perfil.model_dump(mode="json"), "preferencias": prefs.model_dump(mode="json"),
                "candidatas": [{"oferta_id": i, "oferta": ofertas[i].model_dump(mode="json")}
                               for i in ids if i in ofertas],
                "ya_puntuadas": [], "_version": fila["version"], "_huella": huella}

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        if not estado["candidatas"]:
            return {**estado, "recomendaciones": []}
        return super().ejecutar(estado, d)

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        if estado["recomendaciones"]:
            super().guardar(s, tarea, estado)


class _PuntuarUna(_Recomendar):
    """«Puntuar ahora» (RF-8.5e): puntúa solo una oferta, la del catálogo o una propia (RLS).
    Entidad = id de la
    oferta. Va por el mismo flujo que `recomendar`, con una sola candidata."""

    def cargar(self, s, tarea: dict) -> dict:
        fila = repo_perfiles.vigente(s)
        if fila is None:
            raise ValueError("la usuaria no tiene un perfil construido")
        oferta = repo_ofertas.completas(s, [tarea["entidad_id"]]).get(tarea["entidad_id"])
        if oferta is None:
            raise ValueError(f"la oferta {tarea['entidad_id']} no está procesada")
        prefs = repo_perfiles.preferencias(s).model_copy(update={"rango_min": 0, "rango_max": 100})
        perfil = repo_perfiles.perfil_modelo(fila)
        return {"perfil": perfil.model_dump(mode="json"),
                "preferencias": prefs.model_dump(mode="json"),
                "candidatas": [{"oferta_id": tarea["entidad_id"], "oferta": oferta.model_dump(mode="json")}],
                "ya_puntuadas": [], "_version": fila["version"],
                "_huella": huella_compatibilidad(perfil)}


class _Candidatura:
    """Prepara CV y carta para una oferta (entidad = id de la candidatura): carga el perfil vigente, el
    CV maestro y la longitud elegida; los CV base solo con el respaldo activo (RF-10.3d)."""

    def cargar(self, s, tarea: dict) -> dict:
        c = repo_candidaturas.fila(s, tarea["entidad_id"])
        if c is None:
            raise ValueError(f"no existe la candidatura {tarea['entidad_id']} de esta usuaria")
        perfil = repo_perfiles.vigente(s)
        if perfil is None:
            raise ValueError("la usuaria no tiene un perfil construido")
        oferta = repo_ofertas.completas(s, [c["oferta_id"]]).get(c["oferta_id"])
        if oferta is None:
            raise ValueError(f"la oferta {c['oferta_id']} no está procesada")
        guia = repo_estilo.guia(s)
        return {"usuaria_id": tarea["usuaria_id"], "perfil_version": perfil["version"],
                "oferta": oferta.model_dump(mode="json"), "cv_maestro": perfil["cv_maestro"],
                "cvs_base": (repo_candidaturas.cv_base_para_flujo(s)
                             if ajustes().horma_cv_base_respaldo else []),
                "longitud_cv": repo_perfiles.longitud_cv(s),
                "guia_estilo": guia["guia"] if guia else None}

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        """Corre hasta la pausa (antes de `entregar`). Con `langgraph` el estado queda en el hilo de la
        candidatura hasta que se aprueba o se cierra (RF-4.3)."""
        flujo = con_avance(checkpointer.flujo_candidatura(d.engine, proveedor=d.proveedor), d)
        return flujo.run(estado, hilo=checkpointer.hilo_de(d.entidad_id))

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        repo_candidaturas.guardar_preparacion(s, tarea["entidad_id"], estado["perfil_version"], estado)

    def marcar_error(self, s, tarea: dict, motivo: str) -> None:
        repo_candidaturas.marcar_error(s, tarea["entidad_id"], motivo)


class _LeerUrl:
    """Lee la URL de una importación y entrega el texto a `recibir`, como una oferta pegada: privada de la
    usuaria y con su URL guardada (RF-5.3f). Entidad = id de la importación. Cualquier fallo deja un motivo
    fijo (la web pide pegar el texto) y no se reintenta: cada lectura cuesta."""

    def cargar(self, s, tarea: dict) -> dict:
        fila = repo_importaciones.fila(s, tarea["entidad_id"])
        if fila is None:
            raise ValueError(f"no existe la importación {tarea['entidad_id']} de esta usuaria")
        if (motivo := validar_url(fila["url"])) is not None:  # otra vez: pasó tiempo desde que se pidió
            raise ValueError(motivo)
        return {"url": fila["url"], "usuaria_id": tarea["usuaria_id"]}

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        texto = d.lector(estado["url"])
        r = servicio_ofertas.recibir(d.engine, texto, url=estado["url"], usuaria_id=estado["usuaria_id"])
        return {"oferta_id": r["id"]}

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        repo_importaciones.marcar_leida(s, tarea["entidad_id"], estado["oferta_id"])

    def marcar_error(self, s, tarea: dict, motivo: str) -> None:
        repo_importaciones.marcar_error(s, tarea["entidad_id"], MOTIVO_LECTURA)  # fijo: sin detalles


class _AnalizarEstilo:
    """Analiza cómo escribe la usuaria (entidad = id de la usuaria). Una llamada al modelo; solo se encola
    la primera vez o con el botón «Volver a analizar mi estilo» (RF-5.6d)."""

    def cargar(self, s, tarea: dict) -> dict:
        documentos = repo_estilo.documentos(s)
        if not documentos:
            raise ValueError("la usuaria no tiene documentos para analizar su estilo")
        return {"documentos": documentos}

    def ejecutar(self, estado: dict, d: Dependencias) -> dict:
        return con_avance(analizar_estilo.crear(proveedor=d.proveedor), d).run(estado)

    def guardar(self, s, tarea: dict, estado: dict) -> None:
        repo_estilo.guardar(s, tarea["usuaria_id"], GuiaEstilo.model_validate(estado["guia"]), "modelo")

    def marcar_error(self, s, tarea: dict, motivo: str) -> None:
        """Sin fila propia: el motivo queda en la tarea."""


MANEJADORES = {"procesar_oferta": _ProcesarOferta(),
               "calificar_fuente": _CalificarFuente(), "perfilar": _Perfilar(),
               "clasificar_perfil": _ClasificarPerfil(),
               "recomendar": _Recomendar(), "puntuar_propias": _PuntuarPropias(),
               "puntuar_una": _PuntuarUna(),
               "candidatura": _Candidatura(), "leer_url": _LeerUrl(),
               "analizar_estilo": _AnalizarEstilo()}


def procesar_una(engine: Engine, proveedor: Proveedor | None = None, *,
                 resolver: dominio.Resolvedor | None = dominio.resuelve,
                 descargador: descargar.Descargador = descargar.descargar_http,
                 lector: Callable[[str], str] = leer_pagina) -> str | None:
    """Procesa una tarea. Devuelve el estado final de la tarea o None si no había ninguna."""
    tarea = cola.reclamar(engine)
    if tarea is None:
        return None
    usuaria = tarea["usuaria_id"]

    def sesion():
        return sesion_de(engine, usuaria) if usuaria else sesion_sistema(engine)

    manejador = MANEJADORES.get(tarea["tipo"])
    error: Exception | None = None
    estado = None
    restante = float(tarea["tope_coste"]) - float(tarea["coste_acumulado"])
    with metricas.capturar(tope=restante) as llamadas:
        try:
            if manejador is None:
                raise ValueError(f"tipo de tarea desconocido: {tarea['tipo']}")
            with sesion() as s:
                entrada = manejador.cargar(s, tarea)
            def avanzar(p: int) -> None:
                with sesion() as s2:
                    repo_tareas.avanzar(s2, tarea["id"], p)

            deps = Dependencias(proveedor, resolver, descargador, engine, tarea["entidad_id"], lector,
                                usuaria, tarea["id"], avanzar)
            estado = manejador.ejecutar(entrada, deps)
        except Exception as e:  # noqa: BLE001 - cualquier fallo cuenta como intento fallido
            error = e
    coste = float(sum(ll.coste for ll in llamadas))
    acumulado = float(tarea["coste_acumulado"]) + coste

    with sesion() as s:
        repo_tareas.registrar_llamadas(s, tarea["id"], llamadas)
        motivo = None
        if isinstance(error, metricas.TopeSuperado) or acumulado > float(tarea["tope_coste"]):
            motivo = f"tope de coste superado ({acumulado:.6f} > {float(tarea['tope_coste']):.6f})"
        elif error is None:
            manejador.guardar(s, tarea, estado)
            repo_tareas.actualizar(s, tarea["id"], "hecha", coste)
            return "hecha"
        elif tarea["intentos"] >= tarea["tope_reintentos"] or manejador is None:
            motivo = f"reintentos agotados ({tarea['intentos']}): {motivo_seguro(error)}"
        if motivo:
            motivo = motivo[:500]
            if manejador:
                manejador.marcar_error(s, tarea, motivo)
            repo_tareas.actualizar(s, tarea["id"], "error", coste, motivo)
            log.warning("tarea %s detenida: %s", tarea["id"], motivo)
            return "error"
        repo_tareas.actualizar(s, tarea["id"], "pendiente", coste)
        return "pendiente"


def comprobar_alertas(engine: Engine, ultima: float | None, ahora: float) -> float | None:
    """Llama a `alertas.comprobar` si han pasado `ALERTA_INTERVALO_MIN` minutos desde la última vez.
    Devuelve el instante de la última comprobación. Un fallo se registra y no para el worker."""
    a = ajustes()
    if ultima is not None and ahora - ultima < a.alerta_intervalo_min * 60:
        return ultima
    try:
        alertas.comprobar(engine, a)
    except Exception as e:  # noqa: BLE001
        log.error("No se pudieron comprobar las alertas (%s)", type(e).__name__)
    return ahora


def comprobar_aplazadas(engine: Engine, ultima: float | None, ahora: float) -> float | None:
    """Cada `ALERTA_INTERVALO_MIN` minutos encola las propias que quedaron sin presupuesto (RF-10.9e)."""
    if ultima is not None and ahora - ultima < ajustes().alerta_intervalo_min * 60:
        return ultima
    try:
        servicio_ofertas.encolar_propias_aplazadas(engine)
    except Exception as e:  # noqa: BLE001
        log.error("No se pudieron encolar las ofertas aplazadas (%s)", type(e).__name__)
    return ahora


def main() -> None:
    configurar_logs()
    engine = motor()
    log.info("worker en marcha")
    if (n := cola.reencolar_interrumpidas(engine)):
        log.warning("%s tarea(s) interrumpidas por una parada anterior vuelven a la cola", n)
    if not alertas.correo_configurado(ajustes()):
        log.warning("SMTP_HOST o ALERTAS_CORREO sin configurar: las alertas solo salen en pantalla y log")
    ultima: float | None = None
    ultima_aplazadas: float | None = None
    while True:
        ultima = comprobar_alertas(engine, ultima, time.monotonic())
        ultima_aplazadas = comprobar_aplazadas(engine, ultima_aplazadas, time.monotonic())
        if procesar_una(engine) is None:
            time.sleep(1.0)


if __name__ == "__main__":
    main()
