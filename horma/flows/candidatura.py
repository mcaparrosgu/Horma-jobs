"""Flujo candidatura (RF-3.1): elegir_cv_base → redactar_cv → verificar → juzgar_cv → (redactar_cv) →
medir_ats → (redactar_cv) → redactar_carta → verificar_carta → juzgar_carta → (redactar_carta) →
componer. Sin acceso a la base de datos ni a disco: el worker carga las entradas y guarda el resultado.

Estado de entrada: {"usuaria_id": int, "perfil_version": int, "oferta": Oferta, "cv_maestro": str,
"cvs_base": [{id, usuaria_id, nombre, sector, familia, contenido, estado, perfil_version}, ...]}
(todos los CV base de la usuaria; el flujo descarta los rechazados y los de otras usuarias).
Estado de salida: además, lo de `EstadoCandidatura` (cv_base_id, cv_base_motivo, cv_contenido,
cv_traza, carta_contenido, carta_traza, huecos, avisos, cobertura_ats, vueltas_cv, vueltas_carta,
instrucciones_embebidas) y `preparacion` = `lista` o `pendiente_de_ti`.

El CV se redacta como máximo 3 veces (la primera y 2 vueltas, incluida la que pide `medir_ats`) y la
carta como máximo 2. El flujo nunca cambia `estado`: la candidatura sigue en `borrador` (P4)."""
from horma.agents.juez_carta.agent import JuezCarta
from horma.agents.juez_carta.schemas import EntradaJuezCarta
from horma.agents.juez_cv.agent import JuezCv
from horma.agents.juez_cv.schemas import EntradaJuezCv
from horma.agents.redactor_carta.agent import RedactorCarta
from horma.agents.redactor_carta.schemas import EntradaRedactorCarta
from horma.agents.redactor_cv.agent import RedactorCv
from horma.agents.redactor_cv.schemas import EntradaRedactorCv
from horma.agents.selector_cv_base.agent import SelectorCvBase
from horma.agents.selector_cv_base.schemas import CvBaseOpcion, EntradaSelectorCvBase
from horma.flows.plain import PlainFlow
from horma.llm.proveedor import Proveedor
from horma.schemas.candidatura import EstadoCandidatura, Problema
from horma.schemas.oferta import Oferta
from horma.tools.medir_ats import medir_ats
from horma.tools.rasgos_personales import rasgos_personales
from horma.tools.verificar_trazabilidad import FORMULAS_CORTESIA, verificar_trazabilidad

MAX_VUELTAS_CV = 3
MAX_VUELTAS_CARTA = 2
PROPUESTA_HUECO = ("La oferta lo pide y no aparece en tu perfil: si lo tienes, añádelo tú a tu CV "
                   "maestro y vuelve a preparar la candidatura.")


def _texto_oferta(oferta: Oferta) -> str:
    """La oferta como texto, fuente válida solo para la carta (RF-3.6)."""
    partes = [oferta.titulo, oferta.empresa, oferta.ubicacion, oferta.contrato, *oferta.idiomas,
              *oferta.requisitos, *oferta.taxonomia.stack]
    return "\n".join(p for p in partes if p)


def _sumar(e: dict, clave: str, nuevas: list[str]) -> None:
    e[clave] = list(dict.fromkeys([*e.get(clave, []), *nuevas]))


def crear(proveedor: Proveedor | None = None) -> PlainFlow:

    def validar(e: dict) -> EstadoCandidatura:
        return EstadoCandidatura.model_validate(e)

    def elegir_cv_base(e: dict) -> dict:
        validar(e)
        candidatos = [c for c in e["cvs_base"]
                      if c.get("estado") == "hecho" and c.get("usuaria_id") == e["usuaria_id"]]
        if not candidatos:
            raise ValueError("la usuaria no tiene ningún CV base válido: hay que generarlo primero")
        e.update(avisos=[], errores=[], errores_formato=[], problemas=[], palabras_sugeridas=[],
                 huecos=[], huecos_redactor=[], instrucciones_embebidas=[], vueltas_cv=0,
                 vueltas_carta=0, cobertura_ats=None, preparacion="en_curso")
        if len(candidatos) == 1:
            elegido, motivo = candidatos[0], "Es tu único CV base válido."
        else:
            r = SelectorCvBase.run(EntradaSelectorCvBase(
                oferta=Oferta.model_validate(e["oferta"]),
                cvs_base=[CvBaseOpcion(id=c["id"], nombre=c["nombre"], sector=c.get("sector") or "otros",
                                       familia=c.get("familia") or "otros", contenido=c["contenido"])
                          for c in candidatos]), proveedor=proveedor)
            _sumar(e, "instrucciones_embebidas", r.instrucciones_embebidas)
            por_id = {c["id"]: c for c in candidatos}
            if r.cv_base_id not in por_id:
                raise ValueError(f"el selector eligió el CV base {r.cv_base_id}, que no es un candidato "
                                 "válido de esta usuaria (rechazado, ajeno o fuera de la lista)")
            elegido, motivo = por_id[r.cv_base_id], r.motivo
        if elegido.get("perfil_version", e["perfil_version"]) < e["perfil_version"]:
            e["avisos"].append(
                f"El CV base «{elegido['nombre']}» es de una versión anterior del perfil "
                f"(v{elegido['perfil_version']}; ahora v{e['perfil_version']}): puede no recoger lo último.")
        e.update(cv_base_id=elegido["id"], cv_base_motivo=motivo, cv_base_contenido=elegido["contenido"])
        return e

    def redactar_cv(e: dict) -> dict:
        validar(e)
        e["vueltas_cv"] += 1
        r = RedactorCv.run(EntradaRedactorCv(
            cv_base=e["cv_base_contenido"], cv_maestro=e["cv_maestro"],
            oferta=Oferta.model_validate(e["oferta"]),
            errores_previos=[*e["errores"], *e["errores_formato"]],
            problemas_previos=[Problema.model_validate(p) for p in e["problemas"]],
            palabras_sugeridas=e["palabras_sugeridas"]), proveedor=proveedor)
        _sumar(e, "instrucciones_embebidas", r.instrucciones_embebidas)
        e.update(cv_contenido=r.contenido, cv_traza=[t.model_dump(mode="json") for t in r.traza],
                 huecos_redactor=[h.model_dump(mode="json") for h in r.huecos],
                 errores=[], errores_formato=[], problemas=[], palabras_sugeridas=[])
        return e

    def verificar(e: dict) -> dict:
        validar(e)
        e["errores"] = verificar_trazabilidad(e["cv_contenido"], e["cv_traza"],
                                              [e["cv_maestro"], e["cv_base_contenido"]])
        e["errores"] += [f"Rasgo personal en el CV: {r}" for r in rasgos_personales(e["cv_contenido"])]
        return e

    def juzgar_cv(e: dict) -> dict:
        validar(e)
        r = JuezCv.run(EntradaJuezCv(
            contenido=e["cv_contenido"], traza=e["cv_traza"], cv_maestro=e["cv_maestro"],
            cv_base=e["cv_base_contenido"], oferta=Oferta.model_validate(e["oferta"])),
            proveedor=proveedor)
        _sumar(e, "instrucciones_embebidas", r.instrucciones_embebidas)
        e["veredicto_cv"] = r.veredicto
        e["problemas"] = [p.model_dump(mode="json") for p in r.problemas]
        return e

    def medir(e: dict) -> dict:
        validar(e)
        m = medir_ats(e["cv_contenido"], Oferta.model_validate(e["oferta"]),
                      [e["cv_maestro"], e["cv_base_contenido"]])
        e.update(cobertura_ats=m["cobertura"], errores_formato=m["errores_formato"],
                 palabras_sugeridas=m["ausentes_con_origen"], ausentes_sin_origen=m["ausentes_sin_origen"],
                 errores_cv=[*e["errores"], *(["el juez no aprobó el CV"]
                                              if e["veredicto_cv"] == "corregir" else [])])
        return e

    def redactar_carta(e: dict) -> dict:
        validar(e)
        if e["vueltas_carta"] == 0:
            e.update(errores=[], problemas=[])  # los del CV ya no se pasan a la carta
        e["vueltas_carta"] += 1
        oferta = Oferta.model_validate(e["oferta"])
        r = RedactorCarta.run(EntradaRedactorCarta(
            cv_maestro=e["cv_maestro"], cv_adaptado=e["cv_contenido"], oferta=oferta,
            sector=oferta.taxonomia.sector, errores_previos=e["errores"],
            problemas_previos=[Problema.model_validate(p) for p in e["problemas"]]), proveedor=proveedor)
        _sumar(e, "instrucciones_embebidas", r.instrucciones_embebidas)
        e.update(carta_contenido=r.contenido, carta_traza=[t.model_dump(mode="json") for t in r.traza],
                 errores=[], problemas=[])
        return e

    def verificar_carta(e: dict) -> dict:
        validar(e)
        oferta = Oferta.model_validate(e["oferta"])
        e["errores"] = verificar_trazabilidad(
            e["carta_contenido"], e["carta_traza"],
            [e["cv_maestro"], e["cv_base_contenido"], _texto_oferta(oferta)],
            formulas_cortesia=FORMULAS_CORTESIA, por_frase=True)
        e["errores"] += [f"Rasgo personal en la carta: {r}" for r in rasgos_personales(e["carta_contenido"])]
        return e

    def juzgar_carta(e: dict) -> dict:
        validar(e)
        r = JuezCarta.run(EntradaJuezCarta(
            contenido=e["carta_contenido"], traza=e["carta_traza"], cv_maestro=e["cv_maestro"],
            cv_adaptado=e["cv_contenido"], oferta=Oferta.model_validate(e["oferta"])),
            proveedor=proveedor)
        _sumar(e, "instrucciones_embebidas", r.instrucciones_embebidas)
        e["veredicto_carta"] = r.veredicto
        e["problemas"] = [p.model_dump(mode="json") for p in r.problemas]
        return e

    def componer(e: dict) -> dict:
        validar(e)
        vistos = {h["requisito"].casefold() for h in e["huecos_redactor"]}
        e["huecos"] = [*e["huecos_redactor"],
                       *({"requisito": p, "propuesta": PROPUESTA_HUECO}
                         for p in e.get("ausentes_sin_origen", []) if p.casefold() not in vistos)]
        e["huecos"] = list({h["requisito"].casefold(): h for h in e["huecos"]}.values())
        if e["errores_formato"]:
            e["avisos"] += [f"Formato del CV para ATS: {x}" for x in e["errores_formato"]]
        # `errores_cv` guarda los del último CV; `errores`, los de la última carta.
        cv_limpio = not e["errores_cv"] and not e["errores_formato"]
        carta_limpia = e["veredicto_carta"] == "aprobado" and not e["errores"]
        e["preparacion"] = "lista" if cv_limpio and carta_limpia else "pendiente_de_ti"
        validar(e)
        return e

    def tras_juzgar_cv(e: dict) -> str:
        hay_fallos = bool(e["errores"]) or e["veredicto_cv"] == "corregir"
        return "redactar_cv" if hay_fallos and e["vueltas_cv"] < MAX_VUELTAS_CV else "medir_ats"

    def tras_medir(e: dict) -> str:
        pide = bool(e["errores_formato"] or e["palabras_sugeridas"])
        return "redactar_cv" if pide and e["vueltas_cv"] < MAX_VUELTAS_CV else "redactar_carta"

    def tras_juzgar_carta(e: dict) -> str:
        hay_fallos = bool(e["errores"]) or e["veredicto_carta"] == "corregir"
        return "redactar_carta" if hay_fallos and e["vueltas_carta"] < MAX_VUELTAS_CARTA else "componer"

    pasos = {"elegir_cv_base": elegir_cv_base, "redactar_cv": redactar_cv, "verificar": verificar,
             "juzgar_cv": juzgar_cv, "medir_ats": medir, "redactar_carta": redactar_carta,
             "verificar_carta": verificar_carta, "juzgar_carta": juzgar_carta, "componer": componer}
    aristas = {"elegir_cv_base": "redactar_cv", "redactar_cv": "verificar", "verificar": "juzgar_cv",
               "juzgar_cv": tras_juzgar_cv, "medir_ats": tras_medir, "redactar_carta": "verificar_carta",
               "verificar_carta": "juzgar_carta", "juzgar_carta": tras_juzgar_carta}
    return PlainFlow("candidatura", pasos=pasos, aristas=aristas, inicio="elegir_cv_base",
                     finales={"componer"})
