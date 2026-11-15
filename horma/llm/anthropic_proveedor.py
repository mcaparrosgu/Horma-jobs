"""Único archivo del proyecto que importa el SDK de Anthropic (RT-02)."""
import json

import anthropic

from horma.llm.proveedor import Respuesta


class ProveedorAnthropic:
    def __init__(self, api_key: str):
        self._cliente = anthropic.Anthropic(api_key=api_key)

    def generar(self, *, modelo: str, sistema: str, usuario: str, esquema: dict,
                timeout: float) -> Respuesta:
        # Salida estructurada: una herramienta cuyo esquema es el de salida. Los modelos 5.x no
        # admiten forzarla (tool_choice "tool"/"any"), así que va en "auto" y el sistema la exige.
        r = self._cliente.messages.create(
            model=modelo, max_tokens=16000, timeout=timeout,
            system=f"{sistema}\n\nResponde únicamente llamando a la herramienta `salida`.",
            messages=[{"role": "user", "content": usuario}],
            tools=[{"name": "salida", "description": "Devuelve el resultado.",
                    "input_schema": esquema}],
            tool_choice={"type": "auto"},
        )
        if r.stop_reason == "max_tokens":  # respuesta cortada: la herramienta llega vacía o a medias
            raise RuntimeError("El modelo agotó max_tokens antes de terminar la salida.")
        bloque = next(b for b in r.content if b.type == "tool_use")
        return Respuesta(texto=json.dumps(bloque.input, ensure_ascii=False),
                         tokens_entrada=r.usage.input_tokens, tokens_salida=r.usage.output_tokens)
