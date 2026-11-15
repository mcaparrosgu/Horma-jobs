"""Candidatura (fase 3): esquemas y máquina de estados como funciones puras (RF-3.1, RF-3.7, RF-3.9).

Dos campos, dos máquinas (plan): `estado` es el de la candidatura (borrador → aprobada → enviada →
entrevista, y `cerrada` con motivo desde cualquiera) y `preparacion` es el resultado del flujo
(en_curso, lista, pendiente_de_ti, error). El flujo nunca cambia `estado`; solo lo cambian las
funciones `transicion()` y `transicion_por_respuesta()`, que no tocan base de datos ni disco."""
from datetime import date, datetime
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field

Estado = Literal["borrador", "aprobada", "enviada", "entrevista", "cerrada"]
Preparacion = Literal["en_curso", "lista", "pendiente_de_ti", "error"]
Canal = Literal["correo", "web", "linkedin", "otro"]  # lista ampliable (P3)
MotivoCierre = Literal["rechazo", "descartada", "retirada"]
EtiquetaRespuesta = Literal["entrevista", "rechazo", "piden_informacion", "otro"]
TipoProblema = Literal["sin_origen", "inflado", "promesa", "rasgo_personal", "repite_cv"]
TipoEvento = Literal["transicion", "nota", "cv_base_guardado"]
OrigenEvento = Literal["usuaria", "respuesta"]
Documento = Literal["adaptado", "estetico"]

ESTADOS: tuple[str, ...] = get_args(Estado)
CANALES: tuple[str, ...] = get_args(Canal)
MOTIVOS_CIERRE: tuple[str, ...] = get_args(MotivoCierre)
MAX_CANAL_OTRO = 60

# Transiciones permitidas sin contar «cerrada», a la que se llega desde cualquier estado vivo.
_SIGUIENTE: dict[str, str] = {"borrador": "aprobada", "aprobada": "enviada", "enviada": "entrevista"}


class TrazaFrase(BaseModel):
    frase: str = Field(min_length=1, description="Línea del documento, tal cual.")
    fragmento: str = Field(min_length=1, description="Cita literal de la fuente de la que sale.")


class Hueco(BaseModel):
    requisito: str = Field(min_length=1, description="Lo que la oferta pide y el perfil no tiene.")
    propuesta: str = Field(min_length=1, description="Qué puede hacer la usuaria al respecto.")


class Problema(BaseModel):
    tipo: TipoProblema
    frase: str = Field(description="Frase afectada del documento.")
    motivo: str


class Candidatura(BaseModel):
    """Fila de `candidaturas` (migración 0006)."""

    id: int | None = None
    usuaria_id: int
    oferta_id: int
    cv_base_id: int | None = None  # nulo hasta que lo elige el flujo
    cv_base_motivo: str | None = None
    perfil_version: int | None = None
    estado: Estado = "borrador"
    motivo_cierre: MotivoCierre | None = None
    preparacion: Preparacion = "en_curso"
    motivo_error: str | None = None
    cv_contenido: str = ""
    cv_traza: list[TrazaFrase] = Field(default_factory=list)
    carta_contenido: str = ""
    carta_traza: list[TrazaFrase] = Field(default_factory=list)
    huecos: list[Hueco] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)
    cobertura_ats: float | None = Field(default=None, ge=0, le=1)
    vueltas_cv: int = Field(default=0, ge=0)
    vueltas_carta: int = Field(default=0, ge=0)
    instrucciones_embebidas: list[str] = Field(default_factory=list)
    documento: Documento | None = None
    cv_estetico_id: int | None = None
    canal: Canal | None = None
    canal_otro: str | None = Field(default=None, max_length=MAX_CANAL_OTRO)
    enviada_en: date | None = None
    creado_en: datetime | None = None
    actualizado_en: datetime | None = None


class EventoCandidatura(BaseModel):
    """Fila de `candidatura_eventos`: historial de la candidatura."""

    id: int | None = None
    usuaria_id: int | None = None
    candidatura_id: int
    de: Estado | None = None
    a: Estado | None = None
    motivo: str | None = None
    canal: Canal | None = None
    origen: OrigenEvento = "usuaria"
    tipo: TipoEvento = "transicion"
    etiqueta_respuesta: EtiquetaRespuesta | None = None
    creado_en: datetime | None = None


class EstadoCandidatura(BaseModel):
    """Estado tipado del flujo `candidatura` (RF-3.1); cada paso lo valida con este modelo.

    Las entradas del flujo (oferta, perfil, CV maestro, CV base) viajan en el `dict` del estado y no se
    tipan aquí: son los contratos de cada agente."""

    model_config = ConfigDict(extra="allow")

    cv_base_id: int | None = None
    cv_base_motivo: str | None = None
    cv_contenido: str = ""
    cv_traza: list[TrazaFrase] = Field(default_factory=list)
    carta_contenido: str = ""
    carta_traza: list[TrazaFrase] = Field(default_factory=list)
    huecos: list[Hueco] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)
    errores: list[str] = Field(default_factory=list)
    problemas: list[Problema] = Field(default_factory=list)
    cobertura_ats: float | None = Field(default=None, ge=0, le=1)
    vueltas_cv: int = Field(default=0, ge=0)
    vueltas_carta: int = Field(default=0, ge=0)
    instrucciones_embebidas: list[str] = Field(default_factory=list)
    preparacion: Preparacion = "en_curso"
    motivo_error: str | None = None


class Propuesta(BaseModel):
    """Lo que Horma propone tras clasificar la respuesta de una empresa; la usuaria confirma o descarta."""

    tipo: Literal["transicion", "nota", "ninguna"]
    destino: Estado | None = None
    motivo: MotivoCierre | None = None


class TransicionInvalida(ValueError):
    """La transición no está permitida o le faltan datos."""


def transicion(estado: str, destino: str, motivo: str | None = None, *, fecha: date | None = None,
               canal: str | None = None, canal_otro: str | None = None) -> str:
    """Valida el paso de `estado` a `destino` y devuelve `destino`; si no es legal, lanza
    `TransicionInvalida`. `cerrada` exige un motivo y es final; `enviada` exige fecha y canal."""
    if estado not in ESTADOS or destino not in ESTADOS:
        raise TransicionInvalida(f"Estado desconocido: «{estado}» → «{destino}»")
    if estado == "cerrada":
        raise TransicionInvalida("Una candidatura cerrada no admite más cambios")
    if destino == "cerrada":
        if motivo not in MOTIVOS_CIERRE:
            raise TransicionInvalida(f"Para cerrarla hace falta un motivo: {', '.join(MOTIVOS_CIERRE)}")
        return destino
    if _SIGUIENTE.get(estado) != destino:
        raise TransicionInvalida(f"No se puede pasar de «{estado}» a «{destino}»")
    if destino == "enviada":
        if fecha is None or canal is None:
            raise TransicionInvalida("Para marcarla como enviada hacen falta la fecha y el canal")
        if canal not in CANALES:
            raise TransicionInvalida(f"Canal desconocido: «{canal}»")
        if canal_otro is not None and canal != "otro":
            raise TransicionInvalida("El texto del canal solo vale con «otro»")
        if canal_otro is not None and len(canal_otro) > MAX_CANAL_OTRO:
            raise TransicionInvalida(f"El texto del canal admite {MAX_CANAL_OTRO} caracteres como máximo")
    return destino


def transicion_por_respuesta(estado: str, etiqueta: str) -> Propuesta:
    """Propuesta para una respuesta clasificada. Solo si es legal desde `estado`; si no, «ninguna»."""
    ninguna = Propuesta(tipo="ninguna")
    if estado not in ESTADOS or estado == "cerrada":
        return ninguna
    if etiqueta == "entrevista":
        return Propuesta(tipo="transicion", destino="entrevista") if estado == "enviada" else ninguna
    if etiqueta == "rechazo":
        return Propuesta(tipo="transicion", destino="cerrada", motivo="rechazo")
    if etiqueta == "piden_informacion":
        return Propuesta(tipo="nota")
    return ninguna
