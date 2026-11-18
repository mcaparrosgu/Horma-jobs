"""Flujo analizar_estilo (RF-5.6b-d): analizar → depurar. Sin bucle y sin acceso a la base de datos.

Estado de entrada: {"documentos": [{"tipo": "cv"|"carta", "texto": str, "escrito_por_ella": bool}, ...]}.
Estado de salida: además, "guia" (GuiaEstilo) y "instrucciones_embebidas" (solo las que están en los
documentos). Lo que el modelo propone, el código lo comprueba: las citas sin origen se quitan y una guía que
describe a la persona o trae rasgos personales se rechaza (RT-08, RT-09)."""
from horma.agents.analizador_estilo.agent import AnalizadorEstilo
from horma.agents.analizador_estilo.schemas import (
    DocumentoEstilo,
    EntradaAnalizadorEstilo,
    SalidaAnalizadorEstilo,
)
from horma.flows.plain import PlainFlow
from horma.llm.proveedor import Proveedor
from horma.tools.depurar_guia import depurar_guia


def crear(proveedor: Proveedor | None = None) -> PlainFlow:

    def _documentos(e: dict) -> list[DocumentoEstilo]:
        return [DocumentoEstilo.model_validate(d) for d in e["documentos"]]

    def analizar(e: dict) -> dict:
        r = AnalizadorEstilo.run(EntradaAnalizadorEstilo(documentos=_documentos(e)), proveedor=proveedor)
        e["analisis"] = r.model_dump(mode="json")
        return e

    def depurar(e: dict) -> dict:
        guia, instrucciones = depurar_guia(SalidaAnalizadorEstilo.model_validate(e["analisis"]),
                                           _documentos(e))
        e["guia"] = guia.model_dump(mode="json")
        e["instrucciones_embebidas"] = instrucciones
        return e

    return PlainFlow("analizar_estilo", pasos={"analizar": analizar, "depurar": depurar},
                     aristas={"analizar": "depurar"}, inicio="analizar", finales={"depurar"})
