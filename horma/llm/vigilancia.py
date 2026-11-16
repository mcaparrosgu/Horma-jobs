"""Vigilancia de entrada y de salida (RF-4.5, RF-4.5c). Código puro: marca, nunca bloquea la entrada."""
import re
from collections.abc import Sequence
from typing import Literal

TipoSenal = Literal["orden_a_ia", "accion_prohibida", "texto_oculto", "bloque_codificado"]

_I = re.IGNORECASE

# Órdenes dirigidas a una IA (español e inglés).
_ORDEN_A_IA = [re.compile(p, _I) for p in (
    r"\b(ignora|ignore|olvida|forget|disregard|omite)\b.{0,40}\b(instrucciones|instructions|prompt|reglas|rules|anterior|previous|above)",
    r"\ba partir de ahora\b",
    r"\b(from now on|a partir de este momento)\b",
    r"\b(eres|serás|actúa como|act as|you are now|you are)\s+(un|una|a|an|now)\b",
    r"\b(nota|aviso|mensaje|importante|instrucci[oó]n)\s+(para|dirigid[oa]\s+a)\s+(la|el|el\s+sistema|el\s+asistente)?\s*(ia|i\.a\.|asistente|modelo|sistema|ai|llm)\b",
    r"\b(instrucci[oó]n|nota|aviso|mensaje|instruction|note)\s+(para|for)\s+(el|la|the)\s+\w+\s*:",
    r"\b(asistente|assistant)\s+de\s+(ia|ai)\b",
    r"\bpara\s+(el\s+)?(asistente|modelo)\b\s*:",
    r"(^|\n)\s*(ia|ai|asistente|assistant|sistema|system)\s*:",
)]

# Peticiones de enviar, aprobar, cambiar estado o revelar instrucciones o datos, dirigidas a la IA.
_ACCION = [re.compile(p, _I) for p in (
    r"\b(env[ií]a|enviar|reenv[ií]a|reenviar|send|forward)\b.{0,40}"
    r"\b(perfil|datos|cv maestro|informaci[oó]n personal|personal (data|information)|profile|"
    r"candidatura|application)\b",
    r"\b(marca|marcar|mark|set)\b.{0,40}\b(como\s+)?(enviada|aprobada|sent|approved)\b",
    r"\b(aprueba|aprobar|approve)\b.{0,30}\b(candidatura|application|todo|everything|esta)\b",
    r"\b(cambia|cambiar|change)\b.{0,40}\bestado\b",
    r"\b(revela|revelar|muestra|muestrame|reveal|show|print|repite|repeat|escribe|escribir|imprime|"
    r"dime|dame|write|output|tell me)\b.{0,30}"
    r"\b(tus|tu|your|el|the|las)?\s*(instrucciones|instructions|prompt|system prompt)\b",
    r"\b(tel[eé]fono|correo|email|phone|datos|data)\b.{0,20}"
    r"\b(personal(es)?|de la (usuaria|candidata)|del candidato|of the (user|candidate))\b",
    r"\b(cierra|cerrar|descarta|descartar|retira|retirar|close|withdraw)\b.{0,30}"
    r"\b(candidatura|candidaturas|application|applications)\b",
    r"\b(borra|borrar|delete)\b.{0,30}\b(historial|history)\b",
)]

# Texto oculto: ancho cero, controles de dirección y etiquetas Unicode.
_OCULTO = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u202a-\u202e\u2066-\u2069\U000e0000-\U000e007f]")

# Bloques codificados largos: base64 o hexadecimal.
_BASE64 = re.compile(r"[A-Za-z0-9+/]{60,}={0,2}")
_HEX = re.compile(r"\b[0-9a-fA-F]{64,}\b")


def senales_entrada(texto: str) -> list[TipoSenal]:
    """Tipos de señal de manipulación que hay en `texto` (sin el texto), sin repetir."""
    encontradas: list[TipoSenal] = []
    if any(p.search(texto) for p in _ORDEN_A_IA):
        encontradas.append("orden_a_ia")
    if any(p.search(texto) for p in _ACCION):
        encontradas.append("accion_prohibida")
    if _OCULTO.search(texto):
        encontradas.append("texto_oculto")
    if _BASE64.search(texto) or _HEX.search(texto):
        encontradas.append("bloque_codificado")
    return encontradas


MIN_FUGA = 120  # caracteres literales del prompt que delatan una fuga


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def _sin_formulas(texto: str, excluir: Sequence[str]) -> list[str]:
    """El texto cortado por las fórmulas cerradas: ningún fragmento atraviesa una fórmula."""
    partes = [_normalizar(texto)]
    for f in sorted(excluir, key=len, reverse=True):
        fn = _normalizar(f)
        partes = [x for parte in partes for x in parte.split(fn)] if fn else partes
    return [p.strip() for p in partes if p.strip()]


def fuga_prompt(salida: str, prompt: str, excluir: Sequence[str] = ()) -> bool:
    """¿La salida reproduce un fragmento literal del prompt de `MIN_FUGA` caracteres o más?
    `excluir`: fórmulas cerradas (saludos y despedidas) que no cuentan."""
    salidas = _sin_formulas(salida, excluir)
    for segmento in _sin_formulas(prompt, excluir):
        for i in range(len(segmento) - MIN_FUGA + 1):
            ventana = segmento[i:i + MIN_FUGA]
            if any(ventana in s for s in salidas):
                return True
    return False
