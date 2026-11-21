"""Puerta única al modelo (RT-02): reintentos, validación (RT-03) y métricas (RT-06)."""
import json
import time
from collections.abc import Callable

from pydantic import BaseModel, ValidationError

from horma.config import ajustes
from horma.llm import metricas, vigilancia
from horma.llm.proveedor import Proveedor
from horma.tools.verificar_trazabilidad import FORMULAS_CORTESIA


class SalidaInvalida(Exception):
    """La salida del modelo no valida contra el esquema tras el reintento."""


def _textos(salida: BaseModel) -> str:
    """Todas las cadenas de la salida, una por línea, para buscar fugas del prompt."""
    cadenas: list[str] = []

    def recorrer(v: object) -> None:
        if isinstance(v, str):
            cadenas.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                recorrer(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                recorrer(x)

    recorrer(salida.model_dump())
    return "\n".join(cadenas)


def _modelo_real(modelo: str) -> tuple[str, tuple[float, float]]:
    a = ajustes()
    if modelo == "mayor":
        return a.modelo_mayor, a.precio_mayor
    return a.modelo_pequeno, a.precio_pequeno


def _proveedor_por_defecto() -> Proveedor:
    from horma.llm.anthropic_proveedor import ProveedorAnthropic

    clave = ajustes().anthropic_api_key
    if not clave:
        raise RuntimeError("Falta ANTHROPIC_API_KEY en .env (o usa el modo simulado).")
    return ProveedorAnthropic(clave)


def _cadenas(valor) -> str:
    """Todas las cadenas de un dato, una por línea y sin el escapado de JSON."""
    if isinstance(valor, str):
        return valor
    if isinstance(valor, dict):
        valor = list(valor.values())
    if isinstance(valor, (list, tuple, set)):
        return "\n".join(_cadenas(v) for v in valor)
    return ""


def completar(*, agente: str, prompt: str, entrada: BaseModel, esquema_salida: type[BaseModel],
              modelo: str = "pequeno", proveedor: Proveedor | None = None,
              dormir: Callable[[float], None] = time.sleep) -> BaseModel:
    a = ajustes()
    metricas.comprobar_tope()  # antes de gastar: si el bloque ya superó su tope, no se llama al modelo
    proveedor = proveedor or _proveedor_por_defecto()
    nombre_modelo, (p_in, p_out) = _modelo_real(modelo)
    esquema = esquema_salida.model_json_schema()
    usuario = entrada.model_dump_json()
    # RF-4.5: marca y registra; no bloquea. Se mira el texto real y el JSON: en el JSON un salto de línea
    # es la secuencia «barra n» y una orden al principio de línea no casaría con el límite de palabra.
    senales = tuple(dict.fromkeys(
        [*vigilancia.senales_entrada(usuario), *vigilancia.senales_entrada(_cadenas(entrada.model_dump()))]))
    t_in = t_out = 0
    t0 = time.monotonic()

    def cerrar(resultado: str) -> None:
        metricas.registrar(metricas.Llamada(
            agente=agente, modelo=nombre_modelo, tokens_entrada=t_in, tokens_salida=t_out,
            coste=round((t_in * p_in + t_out * p_out) / 1_000_000, 6),
            latencia_ms=int((time.monotonic() - t0) * 1000), resultado=resultado,
            senales_entrada=senales))

    error_validacion = ""
    for _ in range(2):  # 1 llamada + 1 reintento con el error de validación (RT-03)
        peticion = usuario if not error_validacion else (
            f"{usuario}\n\nTu respuesta anterior no cumplía el esquema: {error_validacion}\n"
            "Corrígela.")
        for intento in range(a.llm_reintentos):  # fallos transitorios, con retroceso
            try:
                r = proveedor.generar(modelo=nombre_modelo, sistema=prompt, usuario=peticion,
                                      esquema=esquema, timeout=a.llm_timeout_s)
                break
            except (TimeoutError, ConnectionError):
                if intento == a.llm_reintentos - 1:
                    cerrar("error")
                    raise
                dormir(2 ** intento)
        t_in += r.tokens_entrada
        t_out += r.tokens_salida
        try:
            salida = esquema_salida.model_validate(json.loads(r.texto))
        except (ValidationError, json.JSONDecodeError) as e:
            error_validacion = str(e)
            continue
        if vigilancia.fuga_prompt(_textos(salida), prompt, excluir=FORMULAS_CORTESIA):  # RF-4.5c
            error_validacion = ("La salida reproduce instrucciones internas; "
                                "reescríbela con tus palabras, sin copiarlas.")
            continue
        cerrar("ok")
        return salida
    cerrar("salida_invalida")
    raise SalidaInvalida(error_validacion)
