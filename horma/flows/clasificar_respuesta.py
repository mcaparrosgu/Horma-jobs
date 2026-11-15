"""Flujo clasificar_respuesta (RF-3.9): clasificar → proponer → componer. Sin acceso a la base de datos.

Estado de entrada: {"texto": str (correo pegado por la usuaria), "estado_actual": Estado}.
Estado de salida: además, "etiqueta", "instrucciones_embebidas" y "propuesta" (`Propuesta`).

El modelo solo ve el texto del correo: nunca el estado de la candidatura. La propuesta la decide el
código con `transicion_por_respuesta`; si la transición no es legal o el correo trae instrucciones
dirigidas a una IA, es «ninguna» (RT-07). El flujo nunca cambia `estado_actual`: la usuaria confirma
o descarta la propuesta fuera del flujo."""
from horma.agents.clasificador_respuesta.agent import ClasificadorRespuesta
from horma.agents.clasificador_respuesta.schemas import EntradaClasificadorRespuesta
from horma.flows.plain import PlainFlow
from horma.llm.proveedor import Proveedor
from horma.schemas.candidatura import Propuesta, transicion_por_respuesta


def crear(proveedor: Proveedor | None = None) -> PlainFlow:

    def clasificar(e: dict) -> dict:
        r = ClasificadorRespuesta.run(EntradaClasificadorRespuesta(texto=e["texto"]),
                                      proveedor=proveedor)
        e.update(etiqueta=r.etiqueta, instrucciones_embebidas=r.instrucciones_embebidas)
        return e

    def proponer(e: dict) -> dict:
        propuesta = (Propuesta(tipo="ninguna") if e["instrucciones_embebidas"]
                     else transicion_por_respuesta(e["estado_actual"], e["etiqueta"]))
        e["propuesta"] = propuesta.model_dump(mode="json")
        return e

    def componer(e: dict) -> dict:
        return e

    return PlainFlow("clasificar_respuesta",
                     pasos={"clasificar": clasificar, "proponer": proponer, "componer": componer},
                     aristas={"clasificar": "proponer", "proponer": "componer"},
                     inicio="clasificar", finales={"componer"})
