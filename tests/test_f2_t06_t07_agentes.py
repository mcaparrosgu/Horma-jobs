"""Fase 2 · T06-T07: agentes extractor-perfil, clasificador-postulante, generador-cv-base, matcher."""
import pytest

from horma.agents.clasificador_postulante.agent import ClasificadorPostulante
from horma.agents.clasificador_postulante.schemas import EntradaClasificadorPostulante
from horma.agents.extractor_perfil.agent import ExtractorPerfil
from horma.agents.extractor_perfil.schemas import CvEntrada, EntradaExtractorPerfil, SalidaExtractorPerfil
from horma.agents.generador_cv_base.agent import GeneradorCvBase
from horma.agents.generador_cv_base.schemas import (
    Destino,
    EntradaGeneradorCvBase,
    SalidaGeneradorCvBase,
)
from horma.agents.matcher.agent import Matcher
from horma.agents.matcher.schemas import EntradaMatcher, OfertaCandidata, SalidaMatcher
from horma.agents.registry import AGENTES
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.oferta import Auditoria, Oferta
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias
from horma.schemas.taxonomia import Taxonomia

TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior",
       "stack": ["tpv"]}
ORIGEN = {"fuente": "cv", "cv_id": 1, "fragmento": "Camarera en Bar Sol"}
PERFIL = {"experiencias": [{"puesto": "Camarera", "empresa": "Bar Sol", "origen": ORIGEN}]}


# --- T06 ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("agente", [ExtractorPerfil, ClasificadorPostulante])
def test_agentes_de_perfil_registrados_y_con_prompt_seguro(agente):
    assert AGENTES[agente.nombre] is agente
    p = agente.prompt()
    assert "no fiable" in p and "edad" in p and "nacionalidad" in p


def test_extractor_pide_pendientes_ante_la_ambiguedad_y_registra_instrucciones():
    p = ExtractorPerfil.prompt()
    assert "preguntas_pendientes" in p and "contradi" in p
    assert "instrucciones_embebidas" in p and "origen" in p
    assert ExtractorPerfil.modelo == "mayor" and ClasificadorPostulante.modelo == "pequeno"


def test_extractor_devuelve_su_esquema_y_recibe_todos_los_cv():
    prov = ProveedorSimulado([{"perfil": PERFIL, "cv_maestro": "# Ana\nCamarera en Bar Sol"}])
    r = ExtractorPerfil.run(EntradaExtractorPerfil(cvs=[
        CvEntrada(cv_id=1, nombre="CV hostelería", texto="Camarera en Bar Sol"),
        CvEntrada(cv_id=2, nombre="CV ventas", texto="Dependienta")]), proveedor=prov)
    assert isinstance(r, SalidaExtractorPerfil) and r.perfil.experiencias[0].origen.cv_id == 1
    assert "Dependienta" in prov.llamadas[0]["usuario"] and prov.llamadas[0]["modelo"]


def test_extractor_rechaza_una_salida_con_edad_o_sin_origen():
    malo = {"perfil": {"edad": 34}, "cv_maestro": "x"}
    sin_origen = {"perfil": {"experiencias": [{"puesto": "Camarera"}]}, "cv_maestro": "x"}
    for salida in (malo, sin_origen):
        with pytest.raises(Exception):  # noqa: B017 - SalidaInvalida tras el reintento
            ExtractorPerfil.run(EntradaExtractorPerfil(cvs=[CvEntrada(cv_id=1, nombre="a", texto="x")]),
                                proveedor=ProveedorSimulado([salida, salida]))


def test_clasificador_postulante_devuelve_la_misma_taxonomia():
    r = ClasificadorPostulante.run(EntradaClasificadorPostulante(perfil=Perfil.model_validate(PERFIL)),
                                   proveedor=ProveedorSimulado([TAX]))
    assert isinstance(r, Taxonomia) and r.familia == "hosteleria_restauracion"


# --- T07 ---------------------------------------------------------------------------------------
def test_generador_cv_base_devuelve_contenido_y_traza():
    prov = ProveedorSimulado([{"contenido": "## Experiencia\nCamarera · Bar Sol",
                               "traza": [{"frase": "Camarera · Bar Sol",
                                          "fragmento": "Camarera en Bar Sol"}]}])
    r = GeneradorCvBase.run(EntradaGeneradorCvBase(
        cv_maestro="Camarera en Bar Sol", perfil=Perfil.model_validate(PERFIL),
        destino=Destino(sector="hosteleria_turismo", familia="hosteleria_restauracion"),
        errores_previos=["Frase sin origen"]), proveedor=prov)
    assert isinstance(r, SalidaGeneradorCvBase) and r.traza[0].fragmento
    assert "Frase sin origen" in prov.llamadas[0]["usuario"]


def test_prompt_del_generador_exige_traza_ats_y_no_inventar():
    p = GeneradorCvBase.prompt()
    assert AGENTES["generador-cv-base"] is GeneradorCvBase and GeneradorCvBase.modelo == "mayor"
    assert "traza" in p and "ATS" in p and "errores_previos" in p and "no fiable" in p


def _oferta(titulo="Camarera") -> Oferta:
    return Oferta(titulo=titulo, auditoria=Auditoria(fantasma=False, fraude=False,
                                                     salario_publicado=False),
                  taxonomia=Taxonomia.model_validate(TAX))


def test_matcher_devuelve_matches_y_el_prompt_exige_citas_y_prohibe_rasgos():
    prov = ProveedorSimulado([{"matches": [{
        "oferta_id": 7, "nota": 82, "condiciones": "medio",
        "explicacion": "Tiene dos años de camarera en Bar Sol. La oferta pide experiencia en sala.",
        "cita_perfil": "Camarera en Bar Sol", "cita_oferta": "experiencia en sala"}]}])
    r = Matcher.run(EntradaMatcher(perfil=Perfil.model_validate(PERFIL), condiciones=Preferencias(),
                                   ofertas=[OfertaCandidata(oferta_id=7, oferta=_oferta())]),
                    proveedor=prov)
    assert isinstance(r, SalidaMatcher) and r.matches[0].nota == 82
    p = Matcher.prompt()
    assert AGENTES["matcher"] is Matcher and Matcher.modelo == "mayor"
    assert "2 o 3 frases" in p and "cita_perfil" in p and "cita_oferta" in p
    assert "edad" in p and "nacionalidad" in p and "no fiable" in p


def test_matcher_no_admite_mas_de_30_ofertas_ni_explicaciones_de_una_frase():
    with pytest.raises(ValueError):
        EntradaMatcher(perfil=Perfil(), condiciones=Preferencias(),
                       ofertas=[OfertaCandidata(oferta_id=i, oferta=_oferta()) for i in range(31)])
    with pytest.raises(ValueError):
        SalidaMatcher.model_validate({"matches": [{"oferta_id": 1, "nota": 50, "condiciones": "bajo",
                                                   "explicacion": "Solo una frase."}]})
