"""Proveedor simulado: respuestas predefinidas, sin red. Para tests y `--simulado`."""
import json

from horma.llm.proveedor import Respuesta


class ProveedorSimulado:
    def __init__(self, respuestas: list):
        self._respuestas = list(respuestas)
        self.llamadas: list[dict] = []

    def generar(self, *, modelo: str, sistema: str, usuario: str, esquema: dict,
                timeout: float) -> Respuesta:
        self.llamadas.append({"modelo": modelo, "sistema": sistema, "usuario": usuario})
        r = self._respuestas.pop(0) if self._respuestas else {}
        if isinstance(r, BaseException):
            raise r
        texto = r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)
        return Respuesta(texto=texto, tokens_entrada=max(1, len(usuario) // 4),
                         tokens_salida=max(1, len(texto) // 4))
