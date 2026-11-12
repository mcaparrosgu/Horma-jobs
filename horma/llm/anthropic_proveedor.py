"""Único archivo del proyecto que importa el SDK de Anthropic (RT-02)."""
import json

import anthropic

from horma.llm.proveedor import Respuesta


class ProveedorAnthropic:
    def __init__(self, api_key: str):
        self._cliente = anthropic.Anthropic(api_key=api_key)

    def generar(self, *, modelo: str, sistema: str, usuario: str, esquema: dict,
                timeout: float) -> Respuesta:
        # Salida estructurada: una herramienta cuyo esquema es el de salida, forzada.
        r = self._cliente.messages.create(
            model=modelo, max_tokens=4096, system=sistema, timeout=timeout,
            messages=[{"role": "user", "content": usuario}],
            tools=[{"name": "salida", "description": "Devuelve el resultado.",
                    "input_schema": esquema}],
            tool_choice={"type": "tool", "name": "salida"},
        )
        bloque = next(b for b in r.content if b.type == "tool_use")
        return Respuesta(texto=json.dumps(bloque.input, ensure_ascii=False),
                         tokens_entrada=r.usage.input_tokens, tokens_salida=r.usage.output_tokens)
