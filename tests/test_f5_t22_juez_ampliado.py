"""Fase 5 · T22: juez ampliado y CV base (RF-5.4b, RF-5.4d, RF-5.7b, RF-5.7d)."""
import re
from pathlib import Path

import pytest

from horma.agents.juez_candidatura.schemas import (
    EntradaJuezCandidatura,
    SalidaJuezCandidatura,
    sin_carta,
)
from horma.flows.generar_cv_base import crear as crear_generar
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.candidatura import TEXTOS_PROBLEMA, Problema, aviso_de_problema
from horma.schemas.perfil import Perfil

pytestmark = pytest.mark.usefixtures("limites_reales")

TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior", "stack": []}
PUESTO = "Camarera en Bar Sol, 2020-2023"
RELLENO = " ".join(["atendiendo mesas y cobrando en sala"] * 60)
MAESTRO = f"# Ana Pérez\n\n## Experiencia\n{PUESTO}\n{RELLENO}\n"


def _borrador(*lineas):
    cuerpo = ["## Experiencia", *lineas]
    return {"contenido": "\n".join(cuerpo), "traza": [{"frase": x, "fragmento": x} for x in cuerpo[1:]]}


BUENO = _borrador(PUESTO, RELLENO)
FECHAS_AL_REVES = _borrador("Camarera en Bar Sol, 2023-2020", RELLENO)
APROBADO = {"veredicto_cv": "aprobado", "veredicto_carta": "aprobado", "problemas": []}


def _estado():
    perfil = Perfil.model_validate({"taxonomia": TAX, "experiencias": [{
        "puesto": "Camarera", "empresa": "Bar Sol",
        "origen": {"fuente": "cv", "cv_id": 1, "fragmento": PUESTO}}]})
    maestro = MAESTRO + "Camarera en Bar Sol, 2023-2020\n"
    return {"perfil": perfil.model_dump(mode="json"), "cv_maestro": maestro}


def _juez_corrige(tipo, frase=PUESTO):
    return {"veredicto_cv": "corregir", "veredicto_carta": "aprobado",
            "problemas": [{"documento": "cv", "tipo": tipo, "frase": frase, "motivo": f"motivo {tipo}"}]}


# --- esquemas ----------------------------------------------------------------------------------
def test_los_dos_tipos_nuevos_existen_y_tienen_texto_en_llano():
    for tipo in ("incoherente", "suena_a_ia"):
        p = Problema(documento="cv", tipo=tipo, frase="x", motivo="y")
        assert aviso_de_problema(p).mensaje == TEXTOS_PROBLEMA[tipo]


def test_el_juez_acepta_solo_el_cv_sin_carta_ni_oferta():
    e = EntradaJuezCandidatura(cv="## Experiencia\nx", cv_maestro="m")
    assert e.carta == "" and e.oferta is None and e.cv_base == ""


def test_sin_carta_el_veredicto_de_la_carta_es_aprobado():
    s = SalidaJuezCandidatura.model_validate({
        "veredicto_cv": "aprobado", "veredicto_carta": "corregir",
        "problemas": [{"documento": "carta", "tipo": "suena_a_ia", "frase": "x", "motivo": "y"}]})
    limpia = sin_carta(s)
    assert (limpia.veredicto_cv, limpia.veredicto_carta, limpia.problemas) == ("aprobado", "aprobado", [])


def test_el_prompt_del_juez_explica_los_tipos_nuevos_y_el_caso_sin_carta():
    prompt = Path("horma/agents/juez_candidatura/prompt.md").read_text(encoding="utf-8")
    assert "`incoherente`" in prompt and "`suena_a_ia`" in prompt and "llega vacía" in prompt


# --- CV base: tools y juez (RF-5.4d) ------------------------------------------------------------
def test_un_cv_base_correcto_cuesta_dos_llamadas_generador_y_juez():
    prov = ProveedorSimulado([BUENO, APROBADO])
    e = crear_generar(proveedor=prov).run(_estado())
    assert len(e["cv_base"]["guardados"]) == 1 and len(prov.llamadas) == 2


def test_el_juez_recibe_solo_el_cv_base_sin_carta():
    prov = ProveedorSimulado([BUENO, APROBADO])
    crear_generar(proveedor=prov).run(_estado())
    juez = prov.llamadas[1]["usuario"]
    assert '"carta":""' in juez and '"oferta":null' in juez


def test_un_cv_base_con_incoherencia_vuelve_al_segundo_intento_con_el_problema():
    prov = ProveedorSimulado([BUENO, _juez_corrige("incoherente"), BUENO, APROBADO])
    e = crear_generar(proveedor=prov).run(_estado())
    assert len(e["cv_base"]["guardados"]) == 1 and e["cv_base"]["guardados"][0]["intentos"] == 2
    assert len(prov.llamadas) == 4
    assert "motivo incoherente" in prov.llamadas[2]["usuario"]  # el generador recibe el problema


def test_si_el_juez_sigue_corrigiendo_no_se_guarda_y_deja_el_motivo():
    prov = ProveedorSimulado([BUENO, _juez_corrige("suena_a_ia"), BUENO, _juez_corrige("suena_a_ia")])
    r = crear_generar(proveedor=prov).run(_estado())["cv_base"]
    assert r["guardados"] == [] and "motivo suena_a_ia" in r["rechazados"][0]["motivo"]


def test_el_codigo_manda_antes_que_el_juez_fechas_al_reves_no_gastan_llamada_al_juez():
    prov = ProveedorSimulado([FECHAS_AL_REVES, BUENO, APROBADO])
    e = crear_generar(proveedor=prov).run(_estado())
    assert len(prov.llamadas) == 3 and "antes de empezar" in prov.llamadas[1]["usuario"]
    assert len(e["cv_base"]["guardados"]) == 1


def test_un_cv_base_con_muletilla_se_reintenta():
    mala = _borrador(PUESTO, RELLENO, "Apasionada por la sala")
    prov = ProveedorSimulado([mala, BUENO, APROBADO])
    estado = _estado()
    estado["cv_maestro"] += "Apasionada por la sala\n"
    e = crear_generar(proveedor=prov).run(estado)
    assert len(e["cv_base"]["guardados"]) == 1 and "apasionada por" in prov.llamadas[1]["usuario"]


# --- RF-5.7d: ningún detector externo ------------------------------------------------------------
def test_ninguna_llamada_sale_a_un_detector_de_ia_externo():
    detectores = re.compile(r"gptzero|originality\.ai|copyleaks|zerogpt|turnitin|sapling\.ai|winston\s?ai|"
                            r"contentatscale|crossplag|writer\.com/ai-content-detector", re.IGNORECASE)
    for ruta in Path("horma").rglob("*"):
        if ruta.suffix in {".py", ".json", ".md"} and ruta.is_file():
            assert not detectores.search(ruta.read_text(encoding="utf-8")), ruta
