"""Fase 3 · T01: esquemas de candidatura y máquina de estados (RF-3.1, RF-3.7, RF-3.8b, RF-3.9)."""
from datetime import date

import pytest
from pydantic import ValidationError

from horma.schemas.candidatura import (
    Candidatura,
    EstadoCandidatura,
    EventoCandidatura,
    Hueco,
    Problema,
    TransicionInvalida,
    TrazaFrase,
    transicion,
    transicion_por_respuesta,
)

ESTADOS = ["borrador", "aprobada", "enviada", "entrevista", "cerrada"]
HOY = date(2026, 11, 15)


def test_transiciones_permitidas():
    assert transicion("borrador", "aprobada") == "aprobada"
    assert transicion("aprobada", "enviada", fecha=HOY, canal="correo") == "enviada"
    assert transicion("enviada", "entrevista") == "entrevista"


@pytest.mark.parametrize("origen,destino", [
    ("borrador", "enviada"), ("borrador", "entrevista"), ("aprobada", "entrevista"),
    ("aprobada", "borrador"), ("enviada", "aprobada"), ("entrevista", "enviada"),
    ("borrador", "borrador"),
])
def test_transiciones_prohibidas(origen, destino):
    with pytest.raises(TransicionInvalida):
        transicion(origen, destino, fecha=HOY, canal="web")


@pytest.mark.parametrize("origen", ["borrador", "aprobada", "enviada", "entrevista"])
@pytest.mark.parametrize("motivo", ["rechazo", "descartada", "retirada"])
def test_cerrada_desde_cualquier_estado_con_motivo(origen, motivo):
    assert transicion(origen, "cerrada", motivo=motivo) == "cerrada"


def test_cerrada_exige_motivo_valido():
    with pytest.raises(TransicionInvalida):
        transicion("enviada", "cerrada")
    with pytest.raises(TransicionInvalida):
        transicion("enviada", "cerrada", motivo="porque sí")


@pytest.mark.parametrize("destino", ESTADOS)
def test_nada_sale_de_cerrada(destino):
    with pytest.raises(TransicionInvalida):
        transicion("cerrada", destino, motivo="rechazo", fecha=HOY, canal="web")


def test_estado_desconocido_se_rechaza():
    with pytest.raises(TransicionInvalida):
        transicion("inventado", "aprobada")
    with pytest.raises(TransicionInvalida):
        transicion("borrador", "inventado")


def test_enviada_exige_fecha_y_canal():
    with pytest.raises(TransicionInvalida):
        transicion("aprobada", "enviada")
    with pytest.raises(TransicionInvalida):
        transicion("aprobada", "enviada", fecha=HOY)
    with pytest.raises(TransicionInvalida):
        transicion("aprobada", "enviada", canal="web")
    with pytest.raises(TransicionInvalida):
        transicion("aprobada", "enviada", fecha=HOY, canal="telepatía")


def test_canal_otro_admite_texto_corto():
    assert transicion("aprobada", "enviada", fecha=HOY, canal="otro", canal_otro="En mano") == "enviada"
    assert transicion("aprobada", "enviada", fecha=HOY, canal="otro") == "enviada"
    with pytest.raises(TransicionInvalida):
        transicion("aprobada", "enviada", fecha=HOY, canal="otro", canal_otro="x" * 61)
    with pytest.raises(TransicionInvalida):  # el texto solo vale con «otro»
        transicion("aprobada", "enviada", fecha=HOY, canal="web", canal_otro="En mano")


# --- respuesta de la empresa → propuesta ---------------------------------------------------------
def test_entrevista_solo_desde_enviada():
    p = transicion_por_respuesta("enviada", "entrevista")
    assert (p.tipo, p.destino) == ("transicion", "entrevista")
    for estado in ("borrador", "aprobada", "entrevista", "cerrada"):
        assert transicion_por_respuesta(estado, "entrevista").tipo == "ninguna"


def test_rechazo_propone_cerrada_con_motivo():
    for estado in ("aprobada", "enviada", "entrevista"):
        p = transicion_por_respuesta(estado, "rechazo")
        assert (p.tipo, p.destino, p.motivo) == ("transicion", "cerrada", "rechazo")
    assert transicion_por_respuesta("cerrada", "rechazo").tipo == "ninguna"


def test_piden_informacion_es_solo_una_nota():
    p = transicion_por_respuesta("enviada", "piden_informacion")
    assert (p.tipo, p.destino) == ("nota", None)
    assert transicion_por_respuesta("cerrada", "piden_informacion").tipo == "ninguna"


def test_otro_y_etiquetas_ilegales_no_proponen_nada():
    assert transicion_por_respuesta("enviada", "otro").tipo == "ninguna"
    assert transicion_por_respuesta("enviada", "ordena_aprobar").tipo == "ninguna"
    assert transicion_por_respuesta("inventado", "entrevista").tipo == "ninguna"


# --- modelos --------------------------------------------------------------------------------------
def test_traza_frase_se_importa_tambien_desde_el_agente_de_la_fase_2():
    from horma.agents.generador_cv_base.schemas import TrazaFrase as Antigua
    assert Antigua is TrazaFrase
    with pytest.raises(ValidationError):
        TrazaFrase(frase="", fragmento="x")


def test_problema_y_hueco():
    assert Problema(tipo="repite_cv", frase="f", motivo="m").tipo == "repite_cv"
    with pytest.raises(ValidationError):
        Problema(tipo="otra_cosa", frase="f", motivo="m")
    assert Hueco(requisito="carné B", propuesta="Añade tu carné si lo tienes").requisito == "carné B"


def test_candidatura_nace_en_borrador_en_curso():
    c = Candidatura(usuaria_id=1, oferta_id=2)
    assert (c.estado, c.preparacion) == ("borrador", "en_curso")
    assert c.huecos == [] and c.avisos == [] and c.cv_base_id is None
    with pytest.raises(ValidationError):
        Candidatura(usuaria_id=1, oferta_id=2, estado="inventado")


def test_evento_de_candidatura():
    e = EventoCandidatura(candidatura_id=1, de="aprobada", a="enviada", canal="correo",
                          origen="usuaria", tipo="transicion")
    assert e.a == "enviada"
    with pytest.raises(ValidationError):
        EventoCandidatura(candidatura_id=1, tipo="otro_tipo")


def test_estado_del_flujo_arranca_con_contadores_a_cero():
    e = EstadoCandidatura()
    assert (e.vueltas_cv, e.vueltas_carta) == (0, 0)
    assert e.preparacion == "en_curso"
    with pytest.raises(ValidationError):
        EstadoCandidatura(vueltas_cv=-1)
