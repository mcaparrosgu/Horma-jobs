"""Fase 3 · T05-T07: redactor-cv, juez-cv, redactor-carta, juez-carta, clasificador-respuesta,
selector-cv-base (RF-3.1b, RF-3.2, RF-3.4, RF-3.6, RF-3.6b, RF-3.9, RT-01, RT-07, RT-13)."""
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from horma.agents.clasificador_respuesta.agent import ClasificadorRespuesta
from horma.agents.clasificador_respuesta.schemas import (
    EntradaClasificadorRespuesta,
    SalidaClasificadorRespuesta,
)
from horma.agents.juez_carta.agent import JuezCarta
from horma.agents.juez_carta.schemas import EntradaJuezCarta, SalidaJuezCarta
from horma.agents.juez_cv.agent import JuezCv
from horma.agents.juez_cv.schemas import EntradaJuezCv, SalidaJuezCv
from horma.agents.redactor_carta.agent import RedactorCarta
from horma.agents.redactor_carta.schemas import EntradaRedactorCarta, SalidaRedactorCarta
from horma.agents.redactor_cv.agent import RedactorCv
from horma.agents.redactor_cv.schemas import EntradaRedactorCv, SalidaRedactorCv
from horma.agents.registry import AGENTES
from horma.agents.selector_cv_base.agent import SelectorCvBase
from horma.agents.selector_cv_base.schemas import CvBaseOpcion, EntradaSelectorCvBase, SalidaSelectorCvBase
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.oferta import Auditoria, Oferta
from horma.schemas.taxonomia import Taxonomia

RAIZ = Path(__file__).resolve().parents[1]
TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior",
       "stack": ["tpv"]}
OFERTA = Oferta(titulo="Camarera", requisitos=["experiencia en sala"],
                auditoria=Auditoria(fantasma=False, fraude=False, salario_publicado=False),
                taxonomia=Taxonomia.model_validate(TAX))
TRAZA = [{"frase": "Camarera · Bar Sol", "fragmento": "Camarera en Bar Sol"}]
AGENTES_F3 = (RedactorCv, JuezCv, RedactorCarta, JuezCarta, ClasificadorRespuesta, SelectorCvBase)


# --- registro y contrato «independence» (RT-01, RT-13) -----------------------------------------
@pytest.mark.parametrize("agente", AGENTES_F3)
def test_agentes_registrados_y_en_el_contrato_independence(agente):
    assert AGENTES[agente.nombre] is agente
    contratos = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))[
        "tool"]["importlinter"]["contracts"]
    independence = next(c for c in contratos if c["type"] == "independence")
    assert agente.__module__.rsplit(".", 1)[0] in independence["modules"]


@pytest.mark.parametrize("agente", AGENTES_F3)
def test_todos_tratan_el_contenido_como_no_fiable_y_lo_registran(agente):
    p = agente.prompt()
    assert "no fiable" in p and "instrucciones_embebidas" in p and "NO las" in p


def test_modelos_pequeno_y_mayor_segun_el_plan():
    assert ClasificadorRespuesta.modelo == "pequeno" and SelectorCvBase.modelo == "pequeno"
    assert all(a.modelo == "mayor" for a in (RedactorCv, JuezCv, RedactorCarta, JuezCarta))


# --- T05 ---------------------------------------------------------------------------------------
def test_redactor_cv_devuelve_su_esquema_y_recibe_lo_previo():
    prov = ProveedorSimulado([{"contenido": "## Experiencia\nCamarera · Bar Sol", "traza": TRAZA,
                               "huecos": [{"requisito": "inglés B2", "propuesta": "Añade tu nivel."}]}])
    r = RedactorCv.run(EntradaRedactorCv(
        cv_base="Camarera en Bar Sol", cv_maestro="Camarera en Bar Sol", oferta=OFERTA,
        errores_previos=["Frase sin origen: X"],
        problemas_previos=[{"tipo": "inflado", "frase": "Líder de sala", "motivo": "No consta"}],
        palabras_sugeridas=["tpv"]), proveedor=prov)
    assert isinstance(r, SalidaRedactorCv) and r.huecos[0].requisito == "inglés B2"
    u = prov.llamadas[0]["usuario"]
    assert "Frase sin origen: X" in u and "Líder de sala" in u and "tpv" in u


def test_prompt_del_redactor_cv_exige_huecos_traza_y_registrar_instrucciones():
    p = RedactorCv.prompt()
    assert "huecos" in p and "no inventes" in p.lower()
    assert "traza" in p and "errores_previos" in p and "problemas_previos" in p
    assert "palabras_sugeridas" in p and "ATS" in p


def test_juez_cv_devuelve_la_lista_tipada_y_el_prompt_prohibe_reescribir():
    prov = ProveedorSimulado([{"veredicto": "corregir", "problemas": [
        {"tipo": "promesa", "frase": "Garantizo resultados", "motivo": "Promete lo que no consta"}]}])
    r = JuezCv.run(EntradaJuezCv(contenido="x", traza=TRAZA, cv_maestro="a", cv_base="b", oferta=OFERTA),
                   proveedor=prov)
    assert isinstance(r, SalidaJuezCv) and r.problemas[0].tipo == "promesa"
    p = JuezCv.prompt()
    assert "NO reescribas" in p and "sin_origen" in p and "inflado" in p
    assert "promesa" in p and "rasgo_personal" in p


def test_juez_cv_esquema_coherente():
    with pytest.raises(ValidationError):  # corregir sin problemas
        SalidaJuezCv(veredicto="corregir", problemas=[])
    with pytest.raises(ValidationError):  # aprobar con problemas
        SalidaJuezCv(veredicto="aprobado", problemas=[{"tipo": "inflado", "frase": "a", "motivo": "b"}])
    with pytest.raises(ValidationError):  # «repite_cv» es solo de la carta
        SalidaJuezCv(veredicto="corregir", problemas=[{"tipo": "repite_cv", "frase": "a", "motivo": "b"}])
    assert SalidaJuezCv(veredicto="aprobado").problemas == []


# --- T06 ---------------------------------------------------------------------------------------
def test_redactor_carta_devuelve_su_esquema():
    prov = ProveedorSimulado([{"contenido": "Hola equipo,\nTengo experiencia en sala.\nUn saludo",
                               "traza": [{"frase": "Tengo experiencia en sala.",
                                          "fragmento": "experiencia en sala"}]}])
    r = RedactorCarta.run(EntradaRedactorCarta(
        cv_maestro="a", cv_adaptado="b", oferta=OFERTA, sector="hosteleria_turismo",
        problemas_previos=[{"tipo": "repite_cv", "frase": "Camarera · Bar Sol", "motivo": "Copia el CV"}]),
        proveedor=prov)
    assert isinstance(r, SalidaRedactorCarta) and r.traza[0].fragmento
    assert "Copia el CV" in prov.llamadas[0]["usuario"]


def test_prompt_del_redactor_carta_prohibe_repetir_el_cv_y_usa_formulas_cerradas():
    from horma.tools.verificar_trazabilidad import FORMULAS_CORTESIA
    p = " ".join(RedactorCarta.prompt().split())  # los saltos de línea del prompt no cuentan
    assert "no repitas el cv" in p.lower() and "traza" in p and "problemas_previos" in p
    assert all(f in p for f in FORMULAS_CORTESIA)
    assert "oferta" in p and "sector" in p


def test_juez_carta_tiene_repite_cv_y_no_reescribe():
    prov = ProveedorSimulado([{"veredicto": "corregir", "problemas": [
        {"tipo": "repite_cv", "frase": "Camarera · Bar Sol", "motivo": "Copia una línea del CV"}]}])
    r = JuezCarta.run(EntradaJuezCarta(contenido="x", traza=TRAZA, cv_maestro="a", cv_adaptado="b",
                                       oferta=OFERTA), proveedor=prov)
    assert isinstance(r, SalidaJuezCarta) and r.problemas[0].tipo == "repite_cv"
    p = JuezCarta.prompt()
    assert "repite_cv" in p and "NO reescribas" in p and "rasgo_personal" in p


# --- T07 ---------------------------------------------------------------------------------------
def test_clasificador_respuesta_devuelve_una_de_las_cuatro_etiquetas():
    for etiqueta in ("entrevista", "rechazo", "piden_informacion", "otro"):
        r = ClasificadorRespuesta.run(EntradaClasificadorRespuesta(texto="Hola"),
                                      proveedor=ProveedorSimulado([{"etiqueta": etiqueta}]))
        assert isinstance(r, SalidaClasificadorRespuesta) and r.etiqueta == etiqueta
    with pytest.raises(Exception):  # noqa: B017 - SalidaInvalida tras el reintento
        malo = {"etiqueta": "contratada"}
        ClasificadorRespuesta.run(EntradaClasificadorRespuesta(texto="Hola"),
                                  proveedor=ProveedorSimulado([malo, malo]))


def test_prompt_del_clasificador_respuesta_no_obedece_el_correo():
    p = ClasificadorRespuesta.prompt()
    assert all(e in p for e in ("entrevista", "rechazo", "piden_informacion", "otro"))
    assert "NO las" in p


def _opciones():
    return [CvBaseOpcion(id=1, nombre="Hostelería", sector="hosteleria_turismo",
                         familia="hosteleria_restauracion", contenido="Camarera en Bar Sol"),
            CvBaseOpcion(id=2, nombre="Ventas", sector="comercio_retail", familia="ventas_comercial",
                         contenido="Dependienta")]


def test_selector_devuelve_id_y_motivo_y_recibe_todos_los_cv_base():
    prov = ProveedorSimulado([{"cv_base_id": 1, "motivo": "La oferta es de sala y el CV es de hostelería."}])
    r = SelectorCvBase.run(EntradaSelectorCvBase(oferta=OFERTA, cvs_base=_opciones()), proveedor=prov)
    assert isinstance(r, SalidaSelectorCvBase) and r.cv_base_id == 1 and r.motivo
    assert "Dependienta" in prov.llamadas[0]["usuario"]


def test_selector_pide_un_motivo_de_una_frase_y_exige_cv_base():
    with pytest.raises(ValidationError):
        SalidaSelectorCvBase(cv_base_id=1, motivo="")
    with pytest.raises(ValidationError):
        EntradaSelectorCvBase(oferta=OFERTA, cvs_base=[])
    p = SelectorCvBase.prompt()
    assert "cv_base_id" in p and "una frase" in p and "motivo" in p
