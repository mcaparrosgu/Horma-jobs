"""Flujo candidatura (RF-3.1): elegir_cv_base → redactar_cv → redactar_carta → comprobar → juzgar →
(vuelta única) → componer. Sin acceso a la base de datos ni a disco: el worker carga las entradas y guarda
el resultado.

Estado de entrada: {"usuaria_id": int, "perfil_version": int, "oferta": Oferta, "cv_maestro": str,
"cvs_base": [{id, usuaria_id, nombre, sector, familia, contenido, estado, perfil_version, creado_en}, ...]}
(todos los CV base de la usuaria; el código descarta los rechazados y los de otras usuarias).
Estado de salida: además, lo de `EstadoCandidatura` (cv_base_id, cv_base_motivo, cv_contenido, cv_traza,
carta_contenido, carta_traza, huecos, avisos, problemas_juez, cobertura_ats, vuelta_hecha,
redacciones_cv, redacciones_carta, instrucciones_embebidas) y `preparacion` = `lista` o `pendiente_de_ti`.

De 3 a 5 llamadas al modelo: redactor del CV, redactor de la carta y un único juez; si algo falla,
una sola vuelta que rehace solo lo que falla (P12). Tras la vuelta se vuelve a comprobar con código,
pero no se vuelve a juzgar. El flujo nunca cambia `estado`: la candidatura sigue en `borrador` (P4)."""
from horma.agents.juez_candidatura.agent import JuezCandidatura
from horma.agents.juez_candidatura.schemas import EntradaJuezCandidatura
from horma.agents.redactor_carta.agent import RedactorCarta
from horma.agents.redactor_carta.schemas import EntradaRedactorCarta
from horma.agents.redactor_cv.agent import RedactorCv
from horma.agents.redactor_cv.schemas import EntradaRedactorCv
from horma.flows.plain import PlainFlow
from horma.llm.proveedor import Proveedor
from horma.schemas.candidatura import EstadoCandidatura, Problema, aviso_de_error
from horma.schemas.oferta import Oferta
from horma.tools.avisos_vigentes import avisos_vigentes
from horma.tools.elegir_cv_base import elegir_cv_base
from horma.tools.medir_ats import medir_ats
from horma.tools.rasgos_personales import rasgos_personales
from horma.tools.verificar_trazabilidad import FORMULAS_CORTESIA, verificar_trazabilidad

PROPUESTA_HUECO = ("La oferta lo pide y no aparece en tu perfil: si lo tienes, añádelo tú a tu CV "
                   "maestro y vuelve a preparar la candidatura.")


def texto_oferta(oferta: Oferta) -> str:
    """La oferta como texto, fuente válida solo para la carta (RF-3.6)."""
    partes = [oferta.titulo, oferta.empresa, oferta.ubicacion, oferta.contrato, *oferta.idiomas,
              *oferta.requisitos, *oferta.taxonomia.stack]
    return "\n".join(p for p in partes if p)


def _sumar(e: dict, nuevas: list[str]) -> None:
    e["instrucciones_embebidas"] = list(dict.fromkeys([*e.get("instrucciones_embebidas", []), *nuevas]))


def _como_problemas(errores: list[str]) -> list[Problema]:
    """Los errores de `comprobar` como problemas de la carta, para que el redactor los reciba (P12)."""
    return [Problema(documento="carta", tipo="sin_origen",
                     frase=aviso_de_error("carta", x).frase or "", motivo=x) for x in errores]


def crear(proveedor: Proveedor | None = None) -> PlainFlow:

    def validar(e: dict) -> EstadoCandidatura:
        return EstadoCandidatura.model_validate(e)

    def elegir(e: dict) -> dict:
        validar(e)
        elegido, motivo = elegir_cv_base(e["oferta"], e["cvs_base"], e["usuaria_id"])
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
            cv_base=e["cv_base_contenido"], cv_maestro=e["cv_maestro"],
            oferta=Oferta.model_validate(e["oferta"]),
            errores_previos=[*e["errores_cv"], *e["errores_formato"]],
            problemas_previos=[Problema.model_validate(p) for p in e["problemas_juez"]
                               if p["documento"] == "cv"],
            palabras_sugeridas=e["palabras_sugeridas"]), proveedor=proveedor)
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
            problemas_previos=[*problemas, *_como_problemas(e["errores_carta"])]), proveedor=proveedor)
        _sumar(e, r.instrucciones_embebidas)
        e.update(carta_contenido=r.contenido, carta_traza=[t.model_dump(mode="json") for t in r.traza])
        return e

    def comprobar(e: dict) -> dict:
        """Todo con código: trazabilidad y rasgos personales de los dos documentos y ATS del CV."""
        validar(e)
        oferta = Oferta.model_validate(e["oferta"])
        fuentes_cv = [e["cv_maestro"], e["cv_base_contenido"]]
        e["errores_cv"] = [
            *verificar_trazabilidad(e["cv_contenido"], e["cv_traza"], fuentes_cv),
            *[f"Rasgo personal en el CV: {r}" for r in rasgos_personales(e["cv_contenido"])]]
        e["errores_carta"] = [
            *verificar_trazabilidad(e["carta_contenido"], e["carta_traza"],
                                    [*fuentes_cv, texto_oferta(oferta)],
                                    formulas_cortesia=FORMULAS_CORTESIA, por_frase=True),
            *[f"Rasgo personal en la carta: {r}" for r in rasgos_personales(e["carta_contenido"])]]
        m = medir_ats(e["cv_contenido"], oferta, fuentes_cv)
        e.update(cobertura_ats=m["cobertura"],
                 errores_formato=[f"Formato del CV para ATS: {x}" for x in m["errores_formato"]],
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
            carta_traza=e["carta_traza"], cv_maestro=e["cv_maestro"], cv_base=e["cv_base_contenido"],
            oferta=Oferta.model_validate(e["oferta"])), proveedor=proveedor)
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
        avisos = [*(aviso_de_error("cv", x, e["cv_contenido"]) for x in errores_del_cv),
                  *(aviso_de_error("carta", x, e["carta_contenido"]) for x in e["errores_carta"]),
                  *avisos_vigentes("cv", e["cv_contenido"], e["problemas_juez"]),
                  *avisos_vigentes("carta", e["carta_contenido"], e["problemas_juez"])]
        e["avisos"] = [a.model_dump(mode="json") for a in
                       {(a.documento, a.frase, a.mensaje): a for a in avisos}.values()]
        e["preparacion"] = "pendiente_de_ti" if e["avisos"] else "lista"
        validar(e)
        return e

    def tras_comprobar(e: dict) -> str:
        return "componer" if e["vuelta_hecha"] and e["redacciones_carta"] > 1 else "juzgar"

    def tras_juzgar(e: dict) -> str:
        return {"cv": "redactar_cv", "carta": "redactar_carta"}.get(e["rehacer"], "componer")

    pasos = {"elegir_cv_base": elegir, "redactar_cv": redactar_cv, "redactar_carta": redactar_carta,
             "comprobar": comprobar, "juzgar": juzgar, "componer": componer}
    aristas = {"elegir_cv_base": "redactar_cv", "redactar_cv": "redactar_carta",
               "redactar_carta": "comprobar", "comprobar": tras_comprobar, "juzgar": tras_juzgar}
    return PlainFlow("candidatura", pasos=pasos, aristas=aristas, inicio="elegir_cv_base",
                     finales={"componer"})
