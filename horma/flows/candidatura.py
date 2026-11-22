"""Flujo candidatura (RF-3.1, RF-10.3): elegir_cv_base → redactar_cv → redactar_carta → comprobar → juzgar →
(vuelta única) → componer. Sin acceso a la base de datos ni a disco: el worker carga las entradas y guarda
el resultado.

Estado de entrada: {"usuaria_id": int, "perfil_version": int, "oferta": Oferta, "cv_maestro": str,
"otros_resumenes": [str] (opcional: los resúmenes de los demás CV, RF-10.14d),
"cvs_base": [{id, usuaria_id, nombre, sector, familia, contenido, estado, perfil_version, creado_en}, ...]
(opcional), "guia_estilo": GuiaEstilo | None (opcional, RF-5.6e), "longitud_cv": "mantener" | "sintetizar" |
None (opcional, RF-10.3b)}
Sin CV base (lo normal desde la simplificación, RF-10.3) el flujo parte del CV maestro. Si el worker pasa
CV base (respaldo, RF-10.3d), el código elige uno y descarta los rechazados y los de otras usuarias.
Estado de salida: además, lo de `EstadoCandidatura` (cv_base_id, cv_base_motivo, cv_contenido, cv_traza,
carta_contenido, carta_traza, huecos, avisos, problemas_juez, cobertura_ats, vuelta_hecha,
redacciones_cv, redacciones_carta, instrucciones_embebidas) y `preparacion` = `lista` o `pendiente_de_ti`.

De 3 a 5 llamadas al modelo: redactor del CV, redactor de la carta y un único juez; si algo falla,
una sola vuelta que rehace solo lo que falla (P12). Tras la vuelta se vuelve a comprobar con código,
pero no se vuelve a juzgar. El flujo nunca cambia `estado`: la candidatura sigue en `borrador` (P4).

Fase 4: tras `componer` el flujo se para (pausa antes de `entregar`); al aprobar la usuaria se reanuda y
`entregar` deja los dos PDF con el texto aprobado."""
from dataclasses import dataclass

from horma.agents.juez_candidatura.agent import JuezCandidatura
from horma.agents.juez_candidatura.schemas import EntradaJuezCandidatura
from horma.agents.redactor_carta.agent import RedactorCarta
from horma.agents.redactor_carta.schemas import EntradaRedactorCarta
from horma.agents.redactor_cv.agent import RedactorCv
from horma.agents.redactor_cv.schemas import EntradaRedactorCv
from horma.flows.base import Decision, Paso
from horma.flows.grafo import LangGraphFlow
from horma.flows.plain import PlainFlow
from horma.llm.proveedor import Proveedor
from horma.llm.vigilancia import senales_entrada
from horma.schemas.candidatura import (
    TEXTO_AVISO_OFERTA,
    Aviso,
    EstadoCandidatura,
    Problema,
    aviso_de_error,
    hay_aviso_pendiente,
)
from horma.schemas.estilo import GuiaEstilo
from horma.schemas.oferta import Oferta
from horma.tools.avisos_vigentes import avisos_vigentes
from horma.tools.elegir_cv_base import elegir_cv_base
from horma.tools.generar_pdf import generar_pdf
from horma.tools.medir_ats import medir_ats
from horma.tools.muletillas_ia import errores_muletillas
from horma.tools.rasgos_personales import rasgos_personales
from horma.tools.validar_cv import validar_cv
from horma.tools.verificar_trazabilidad import FORMULAS_CORTESIA, verificar_trazabilidad

PROPUESTA_HUECO = ("La oferta lo pide y no aparece en tu perfil: si lo tienes, añádelo tú a tu CV "
                   "maestro y vuelve a preparar la candidatura.")


def texto_oferta(oferta: Oferta) -> str:
    """La oferta como texto, fuente válida solo para la carta (RF-3.6)."""
    partes = [oferta.titulo, oferta.empresa, oferta.ubicacion, oferta.contrato, *oferta.idiomas,
              *oferta.requisitos, *oferta.taxonomia.stack]
    return "\n".join(p for p in partes if p)


def aviso_de_oferta(oferta: Oferta) -> Aviso | None:
    """Aviso fijo si la oferta tiene señales de manipulación (RF-4.5b): por su texto o porque la
    auditoría de la fase 1 ya encontró instrucciones embebidas. Solo informa; no cambia nada más."""
    texto = "\n".join([texto_oferta(oferta), *oferta.instrucciones_embebidas])
    if oferta.instrucciones_embebidas or senales_entrada(texto):
        return Aviso(documento="oferta", mensaje=TEXTO_AVISO_OFERTA)
    return None


def _guia(e: dict) -> GuiaEstilo | None:
    """La guía de estilo de la usuaria, si la hay (RF-5.6e). Sin ella, todo se redacta como siempre."""
    return GuiaEstilo.model_validate(e["guia_estilo"]) if e.get("guia_estilo") else None


def _sumar(e: dict, nuevas: list[str]) -> None:
    e["instrucciones_embebidas"] = list(dict.fromkeys([*e.get("instrucciones_embebidas", []), *nuevas]))


def _como_problemas(errores: list[str]) -> list[Problema]:
    """Los errores de `comprobar` como problemas de la carta, para que el redactor los reciba (P12)."""
    return [Problema(documento="carta", tipo="sin_origen",
                     frase=aviso_de_error("carta", x).frase or "", motivo=x) for x in errores]


# Claves del estado que no son de `EstadoCandidatura`: entradas del worker, datos de trabajo entre pasos y
# lo que deja `entregar`; `estado` (de la candidatura) es entrada opcional que el flujo nunca modifica.
# LangGraphFlow las declara todas en su estado (RF-4.1).
CLAVES_INTERNAS = frozenset({
    "errores_cv", "errores_carta", "errores_formato", "palabras_sugeridas", "ausentes_sin_origen",
    "huecos_redactor", "rehacer", "cv_base_contenido", "cv_maestro", "cvs_base", "oferta", "usuaria_id",
    "perfil_version", "en_pausa", "cv_pdf", "carta_pdf", "estado", "guia_estilo", "longitud_cv",
    "otros_resumenes"})


CLAVES_ESTADO = frozenset(EstadoCandidatura.model_fields) | CLAVES_INTERNAS


@dataclass(frozen=True)
class Definicion:
    """Pasos, aristas, inicio, pausas y finales: los comparten PlainFlow y LangGraphFlow (RT-12)."""

    pasos: dict[str, Paso]
    aristas: dict[str, str | Decision]
    inicio: str
    pausas: frozenset[str]
    finales: frozenset[str]


def definicion(proveedor: Proveedor | None = None) -> Definicion:

    def validar(e: dict) -> EstadoCandidatura:
        return EstadoCandidatura.model_validate(e)

    def elegir(e: dict) -> dict:
        validar(e)
        # Sin CV base el flujo parte del maestro (RF-10.3); con respaldo (RF-10.3d) elige uno por código.
        elegido, motivo = (elegir_cv_base(e["oferta"], e["cvs_base"], e["usuaria_id"])
                           if e.get("cvs_base") else ({"id": None, "contenido": None}, None))
        e.update(avisos=[], problemas_juez=[], errores_cv=[], errores_carta=[], errores_formato=[],
                 palabras_sugeridas=[], ausentes_sin_origen=[], huecos=[], huecos_redactor=[],
                 instrucciones_embebidas=[], vuelta_hecha=False, rehacer=None, redacciones_cv=0,
                 redacciones_carta=0, cobertura_ats=None, preparacion="en_curso",
                 cv_base_id=elegido["id"], cv_base_motivo=motivo, cv_base_contenido=elegido["contenido"])
        return e

    def redactar_cv(e: dict) -> dict:
        validar(e)
        e["redacciones_cv"] += 1
        r = RedactorCv.run(EntradaRedactorCv(
            cv_base=e["cv_base_contenido"], cv_maestro=e["cv_maestro"], longitud=e.get("longitud_cv"),
            otros_resumenes=e.get("otros_resumenes") or [],
            oferta=Oferta.model_validate(e["oferta"]),
            errores_previos=[*e["errores_cv"], *e["errores_formato"]],
            problemas_previos=[Problema.model_validate(p) for p in e["problemas_juez"]
                               if p["documento"] == "cv"],
            palabras_sugeridas=e["palabras_sugeridas"], guia_estilo=_guia(e)), proveedor=proveedor)
        _sumar(e, r.instrucciones_embebidas)
        e.update(cv_contenido=r.contenido, cv_traza=[t.model_dump(mode="json") for t in r.traza],
                 huecos_redactor=[h.model_dump(mode="json") for h in r.huecos])
        return e

    def redactar_carta(e: dict) -> dict:
        validar(e)
        e["redacciones_carta"] += 1
        oferta = Oferta.model_validate(e["oferta"])
        problemas = [Problema.model_validate(p) for p in e["problemas_juez"] if p["documento"] == "carta"]
        r = RedactorCarta.run(EntradaRedactorCarta(
            cv_maestro=e["cv_maestro"], cv_adaptado=e["cv_contenido"], oferta=oferta,
            sector=oferta.taxonomia.sector, errores_previos=[],
            problemas_previos=[*problemas, *_como_problemas(e["errores_carta"])],
            guia_estilo=_guia(e)), proveedor=proveedor)
        _sumar(e, r.instrucciones_embebidas)
        e.update(carta_contenido=r.contenido, carta_traza=[t.model_dump(mode="json") for t in r.traza])
        return e

    def comprobar(e: dict) -> dict:
        """Todo con código: trazabilidad, rasgos personales y muletillas de IA de los dos documentos, y
        longitud, secciones, fechas y ATS del CV."""
        validar(e)
        oferta = Oferta.model_validate(e["oferta"])
        fuentes_cv = [x for x in (e["cv_maestro"], e["cv_base_contenido"], *(e.get("otros_resumenes") or [])) if x]
        e["errores_cv"] = [
            *verificar_trazabilidad(e["cv_contenido"], e["cv_traza"], fuentes_cv),
            *[f"Rasgo personal en el CV: {r}" for r in rasgos_personales(e["cv_contenido"])],
            *errores_muletillas("cv", e["cv_contenido"])]
        e["errores_carta"] = [
            *verificar_trazabilidad(e["carta_contenido"], e["carta_traza"],
                                    [*fuentes_cv, texto_oferta(oferta)],
                                    formulas_cortesia=FORMULAS_CORTESIA, por_frase=True),
            *[f"Rasgo personal en la carta: {r}" for r in rasgos_personales(e["carta_contenido"])],
            *errores_muletillas("carta", e["carta_contenido"])]
        m = medir_ats(e["cv_contenido"], oferta, fuentes_cv)
        e.update(cobertura_ats=m["cobertura"],
                 errores_formato=[*[f"Estructura del CV: {x}"
                                     for x in validar_cv(e["cv_contenido"], e["cv_maestro"])],
                                  *[f"Formato del CV para ATS: {x}" for x in m["errores_formato"]]],
                 palabras_sugeridas=m["ausentes_con_origen"], ausentes_sin_origen=m["ausentes_sin_origen"])
        return e

    def _falla(e: dict, documento: str) -> bool:
        errores = (e["errores_cv"] + e["errores_formato"] + e["palabras_sugeridas"]
                   if documento == "cv" else e["errores_carta"])
        return bool(errores) or any(p["documento"] == documento for p in e["problemas_juez"])

    def juzgar(e: dict) -> dict:
        """Un solo juicio. Decide también qué se rehace en la vuelta única (solo lo que falla)."""
        validar(e)
        r = JuezCandidatura.run(EntradaJuezCandidatura(
            cv=e["cv_contenido"], cv_traza=e["cv_traza"], carta=e["carta_contenido"],
            carta_traza=e["carta_traza"], cv_maestro=e["cv_maestro"],
            cv_base=e["cv_base_contenido"] or "", oferta=Oferta.model_validate(e["oferta"]),
            guia_estilo=_guia(e)), proveedor=proveedor)
        _sumar(e, r.instrucciones_embebidas)
        e["problemas_juez"] = [p.model_dump(mode="json") for p in r.problemas]
        # Si el CV falla se rehace el CV y, después, la carta (que se apoya en él); si solo falla la carta,
        # solo ella. Las palabras ATS con origen entran en esta misma vuelta (P13).
        e["rehacer"] = "cv" if _falla(e, "cv") else "carta" if _falla(e, "carta") else None
        e["vuelta_hecha"] = e["rehacer"] is not None
        return e

    def componer(e: dict) -> dict:
        """Avisos en llano sobre el texto final: errores de `comprobar` y problemas del juez vigentes."""
        validar(e)
        vistos = {h["requisito"].casefold() for h in e["huecos_redactor"]}
        huecos = [*e["huecos_redactor"],
                  *({"requisito": p, "propuesta": PROPUESTA_HUECO}
                    for p in e["ausentes_sin_origen"] if p.casefold() not in vistos)]
        e["huecos"] = list({h["requisito"].casefold(): h for h in huecos}.values())
        errores_del_cv = [*e["errores_formato"], *e["errores_cv"]]
        de_la_oferta = aviso_de_oferta(Oferta.model_validate(e["oferta"]))
        avisos = [*([de_la_oferta] if de_la_oferta else []),
                  *(aviso_de_error("cv", x, e["cv_contenido"]) for x in errores_del_cv),
                  *(aviso_de_error("carta", x, e["carta_contenido"]) for x in e["errores_carta"]),
                  *avisos_vigentes("cv", e["cv_contenido"], e["problemas_juez"]),
                  *avisos_vigentes("carta", e["carta_contenido"], e["problemas_juez"])]
        e["avisos"] = [a.model_dump(mode="json") for a in
                       {(a.documento, a.frase, a.mensaje): a for a in avisos}.values()]
        e["preparacion"] = "pendiente_de_ti" if hay_aviso_pendiente(e["avisos"]) else "lista"
        validar(e)
        return e

    def tras_comprobar(e: dict) -> str:
        return "componer" if e["vuelta_hecha"] and e["redacciones_carta"] > 1 else "juzgar"

    def tras_juzgar(e: dict) -> str:
        return {"cv": "redactar_cv", "carta": "redactar_carta"}.get(e["rehacer"], "componer")

    # Destinos posibles de cada decisión (los usa LangGraphFlow para dibujar las aristas condicionales).
    tras_comprobar.destinos = ("componer", "juzgar")
    tras_juzgar.destinos = ("redactar_cv", "redactar_carta", "componer")

    def entregar(e: dict) -> dict:
        """Código puro, sin modelo: los dos PDF con el texto que haya en el estado (el aprobado). No cambia
        `estado`: eso lo hace el servicio (RF-4.3c)."""
        titulo = Oferta.model_validate(e["oferta"]).titulo or "oferta"
        e["cv_pdf"] = generar_pdf(e["cv_contenido"], f"CV · {titulo}")
        e["carta_pdf"] = generar_pdf(e["carta_contenido"], f"Carta de presentación · {titulo}", "carta")
        return e

    pasos = {"elegir_cv_base": elegir, "redactar_cv": redactar_cv, "redactar_carta": redactar_carta,
             "comprobar": comprobar, "juzgar": juzgar, "componer": componer, "entregar": entregar}
    aristas = {"elegir_cv_base": "redactar_cv", "redactar_cv": "redactar_carta",
               "redactar_carta": "comprobar", "comprobar": tras_comprobar, "juzgar": tras_juzgar,
               "componer": "entregar"}
    return Definicion(pasos, aristas, "elegir_cv_base", frozenset({"entregar"}), frozenset({"entregar"}))


def crear(proveedor: Proveedor | None = None) -> PlainFlow:
    d = definicion(proveedor)
    return PlainFlow("candidatura", pasos=d.pasos, aristas=d.aristas, inicio=d.inicio,
                     finales=set(d.finales), pausas=set(d.pausas))


def crear_grafo(proveedor: Proveedor | None = None, *, checkpointer=None) -> LangGraphFlow:
    """Misma definición que `crear`, ejecutada con LangGraph. `checkpointer` se inyecta desde fuera."""
    d = definicion(proveedor)
    return LangGraphFlow("candidatura", pasos=d.pasos, aristas=d.aristas, inicio=d.inicio,
                         finales=set(d.finales), pausas=set(d.pausas), claves=CLAVES_ESTADO,
                         checkpointer=checkpointer)
