"""Flujo clasificar_perfil (RF-2.5): vuelve a clasificar un perfil tras una respuesta o corrección de la
usuaria, sin repetir la extracción. Un solo paso (el agente pequeño) y sin acceso a la base de datos.

Estado de entrada: {"perfil": Perfil}. Estado de salida: además, "taxonomia"."""
from horma.agents.clasificador_postulante.agent import ClasificadorPostulante
from horma.agents.clasificador_postulante.schemas import EntradaClasificadorPostulante
from horma.flows.plain import PlainFlow
from horma.llm.proveedor import Proveedor
from horma.schemas.perfil import Perfil


def crear(proveedor: Proveedor | None = None) -> PlainFlow:

    def clasificar(e: dict) -> dict:
        perfil = Perfil.model_validate(e["perfil"]).model_copy(update={"instrucciones_embebidas": []})
        e["taxonomia"] = ClasificadorPostulante.run(
            EntradaClasificadorPostulante(perfil=perfil), proveedor=proveedor).model_dump(mode="json")
        return e

    return PlainFlow("clasificar_perfil", pasos={"clasificar": clasificar}, aristas={},
                     inicio="clasificar", finales={"clasificar"})
