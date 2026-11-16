"""Fase 3 · T01 y T23: esquemas de candidatura, avisos y máquina de estados (RF-3.1, RF-3.4, RF-3.6c,
RF-3.7, RF-3.8b, RF-3.9)."""
from datetime import date

import pytest
from pydantic import ValidationError

from horma.schemas.candidatura import (
    TEXTOS_ERROR,
    TEXTOS_PROBLEMA,
    Aviso,
    Candidatura,
    EstadoCandidatura,
    EventoCandidatura,
    Hueco,
    Problema,
    TransicionInvalida,
    TrazaFrase,
    aviso_de_error,
    aviso_de_problema,
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
    assert Problema(documento="carta", tipo="repite_cv", frase="f", motivo="m").tipo == "repite_cv"
    with pytest.raises(ValidationError):
        Problema(documento="carta", tipo="otra_cosa", frase="f", motivo="m")
    with pytest.raises(ValidationError):  # el documento es obligatorio
        Problema(tipo="inflado", frase="f", motivo="m")
    assert Hueco(requisito="carné B", propuesta="Añade tu carné si lo tienes").requisito == "carné B"


def test_un_repite_cv_en_el_cv_no_valida():
    with pytest.raises(ValidationError):
        Problema(documento="cv", tipo="repite_cv", frase="f", motivo="m")
    assert Problema(documento="cv", tipo="inflado", frase="f", motivo="m").documento == "cv"


PREFIJOS_TECNICOS = ("CV:", "Carta:", "juez", "Juez", "(", "sin_origen", "repite_cv", "rasgo_personal",
                     "Frase sin origen", "ATS")


@pytest.mark.parametrize("tipo", list(TEXTOS_PROBLEMA))
def test_cada_tipo_de_problema_da_un_aviso_en_llano(tipo):
    documento = "carta" if tipo == "repite_cv" else "cv"
    a = aviso_de_problema(Problema(documento=documento, tipo=tipo, frase="Una frase", motivo="x"))
    assert isinstance(a, Aviso) and (a.documento, a.frase) == (documento, "Una frase")
    assert not any(p in a.mensaje for p in PREFIJOS_TECNICOS) and a.mensaje.endswith((".", ";"))


def test_la_tabla_de_problemas_cubre_todos_los_tipos():
    from typing import get_args

    from horma.schemas.candidatura import TipoProblema
    assert set(TEXTOS_PROBLEMA) == set(get_args(TipoProblema))


@pytest.mark.parametrize("error, clave, frase", [
    ("Fecha que no está en ninguna de las fuentes: 2019", "fecha", "Camarera · Bar Sol · 2019"),
    ("Frase sin origen en la traza: «Dirigí un hotel»", "sin_traza", "Dirigí un hotel"),
    ("El fragmento no está en ninguna de las fuentes: «Otra cosa» (frase «Mi frase»)", "fragmento",
     "Mi frase"),
    ("«jefa» no aparece en el fragmento de origen de la frase «Fui jefa de sala»", "dato_nuevo",
     "Fui jefa de sala"),
    ("Rasgo personal en el CV: edad: joven", "rasgo", None),
    ("Rasgo personal en la carta: sexo: mujer", "rasgo", None),
    ("Formato del CV para ATS: lleva una tabla", "formato", None),
    ("Algo que nadie previó", "otro", None),
])
def test_cada_error_de_comprobar_da_un_aviso_en_llano_junto_a_su_frase(error, clave, frase):
    contenido = "## Experiencia" + chr(10) + "Camarera · Bar Sol · 2019" + chr(10)
    a = aviso_de_error("cv", error, contenido)
    assert a.frase == frase and a.documento == "cv"
    dato = {"fecha": "2019", "dato_nuevo": "jefa", "rasgo": error.split(": ", 1)[-1],
            "formato": "lleva una tabla"}.get(clave, "")
    assert a.mensaje == TEXTOS_ERROR[clave].format(dato=dato)
    assert not any(p in a.mensaje.replace("(" + dato + ")", "") for p in PREFIJOS_TECNICOS)


def test_los_errores_reales_de_las_herramientas_se_reconocen():
    """Acopla el clasificador a los mensajes que producen `verificar_trazabilidad` y `medir_ats`."""
    from horma.tools.medir_ats import errores_ats
    from horma.tools.verificar_trazabilidad import verificar_trazabilidad
    cv = "## Experiencia" + chr(10) + "Directora en Hotel Ritz, 2010-2015"
    traza = [{"frase": "Directora", "fragmento": "Camarera"}]
    errores = verificar_trazabilidad(cv, [], "Camarera")
    errores += verificar_trazabilidad("Directora", traza, ["Camarera"])
    errores += verificar_trazabilidad("Directora", [{"frase": "Directora", "fragmento": "Camarera"}],
                                      ["Camarera en Bar Sol"])
    assert errores
    for e in errores:
        assert aviso_de_error("cv", e).mensaje != TEXTOS_ERROR["otro"], e
    assert all(aviso_de_error("cv", f"Formato del CV para ATS: {x}").mensaje != TEXTOS_ERROR["otro"]
               for x in errores_ats("| a | b |"))


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


def test_estado_del_flujo_arranca_sin_vuelta_ni_redacciones():
    e = EstadoCandidatura()
    assert (e.vuelta_hecha, e.redacciones_cv, e.redacciones_carta) == (False, 0, 0)
    assert e.preparacion == "en_curso" and e.avisos == [] and e.problemas_juez == []
    assert not hasattr(e, "vueltas_cv") and not hasattr(e, "vueltas_carta")
    with pytest.raises(ValidationError):
        EstadoCandidatura(redacciones_cv=-1)
    with pytest.raises(ValidationError):  # cada documento se redacta como máximo 2 veces
        EstadoCandidatura(redacciones_carta=3)


def test_el_estado_del_flujo_guarda_avisos_estructurados_y_problemas_del_juez():
    e = EstadoCandidatura(avisos=[{"documento": "carta", "frase": "x", "mensaje": "Revisa esto."}],
                          problemas_juez=[{"documento": "cv", "tipo": "inflado", "frase": "f",
                                           "motivo": "m"}])
    assert e.avisos[0].documento == "carta" and e.problemas_juez[0].tipo == "inflado"
    with pytest.raises(ValidationError):
        EstadoCandidatura(avisos=["texto suelto"])
