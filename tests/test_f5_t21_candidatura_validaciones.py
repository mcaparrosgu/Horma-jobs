"""Fase 5 · T21: `validar_cv` y `muletillas_ia` dentro del flujo `candidatura` (RF-5.4c, RF-5.7c).

Con respuestas simuladas: un CV largo o con muletilla se rehace una vez; si sigue mal, sale el aviso
en llano; las llamadas al modelo siguen entre 3 y 5. Corre con `plain` y con `langgraph`."""
import pytest

from horma.flows.registry import IMPLEMENTACIONES, crear_flujo
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.oferta import Auditoria, Oferta
from horma.schemas.taxonomia import Taxonomia

pytestmark = pytest.mark.usefixtures("limites_reales")

TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior",
       "stack": ["tpv"]}
OFERTA = Oferta(titulo="Camarera", empresa="Bar Luna", requisitos=["experiencia en sala"],
                auditoria=Auditoria(fantasma=False, fraude=False, salario_publicado=False),
                taxonomia=Taxonomia.model_validate(TAX)).model_dump(mode="json")

PUESTO = "Camarera en Bar Sol, 2020-2023"
RELLENO = " ".join(["atendiendo mesas y cobrando en sala"] * 60)        # 300 palabras
RELLENO_LARGO = " ".join(["atendiendo mesas y cobrando en sala"] * 200)  # 1.000 palabras
MULETILLA = "Apasionada por la atención al cliente"
MAESTRO = "\n".join(["# Ana Pérez", "", "## Experiencia", PUESTO, RELLENO, RELLENO_LARGO, MULETILLA, ""])
BASE = "\n".join(["## Experiencia", PUESTO, RELLENO, RELLENO_LARGO, MULETILLA])
APROBADO = {"veredicto_cv": "aprobado", "veredicto_carta": "aprobado", "problemas": []}


@pytest.fixture(autouse=True, params=IMPLEMENTACIONES)
def impl(request):
    return request.param


def _cv(*lineas):
    cuerpo = ["## Experiencia", PUESTO, *lineas]
    return {"contenido": "\n".join(cuerpo),
            "traza": [{"frase": x, "fragmento": x} for x in cuerpo[1:]], "huecos": []}


CV_BUENO = _cv(RELLENO)                          # 306 palabras, sin muletillas
CV_CORTO = _cv("Servicio de sala.")              # muy corto
CV_CON_MULETILLA = _cv(RELLENO, MULETILLA)
CARTA = {"contenido": "Hola equipo,\nTrabajé en Bar Sol desde 2020.\nUn saludo",
         "traza": [{"frase": "Trabajé en Bar Sol desde 2020.", "fragmento": PUESTO}]}
CARTA_CON_MULETILLA = {"contenido": f"Hola equipo,\n{MULETILLA}.\nUn saludo",
                       "traza": [{"frase": f"{MULETILLA}.", "fragmento": MULETILLA}]}


def _correr(impl, respuestas):
    prov = ProveedorSimulado(respuestas)
    estado = {"usuaria_id": 7, "perfil_version": 2, "oferta": OFERTA, "cv_maestro": MAESTRO,
              "cvs_base": [{"id": 1, "usuaria_id": 7, "nombre": "CV 1", "sector": TAX["sector"],
                            "familia": TAX["familia"], "contenido": BASE, "estado": "hecho",
                            "perfil_version": 2}]}
    return crear_flujo("candidatura", impl, proveedor=prov).run(estado), prov


def _mensajes(r, documento):
    return [a["mensaje"] for a in r["avisos"] if a["documento"] == documento]


def test_un_cv_normal_pasa_con_tres_llamadas(impl):
    r, prov = _correr(impl, [CV_BUENO, CARTA, APROBADO])
    assert len(prov.llamadas) == 3 and r["avisos"] == [] and r["preparacion"] == "lista"


def test_cv_largo_con_muletilla_se_rehace_una_vez_y_queda_limpio(impl):
    r, prov = _correr(impl, [_cv(RELLENO, RELLENO_LARGO, MULETILLA), CARTA, APROBADO, CV_BUENO, CARTA])
    assert len(prov.llamadas) == 5 and r["vuelta_hecha"] and r["redacciones_cv"] == 2
    errores = prov.llamadas[3]["usuario"]  # el segundo CV recibe lo que falló (RF-5.4c)
    assert "demasiado largo" in errores and "apasionada por" in errores
    assert r["avisos"] == [] and r["preparacion"] == "lista"


def test_si_la_muletilla_sigue_tras_la_vuelta_sale_el_aviso(impl):
    r, prov = _correr(impl, [CV_CON_MULETILLA, CARTA, APROBADO, CV_CON_MULETILLA, CARTA])
    assert len(prov.llamadas) == 5
    avisos = _mensajes(r, "cv")
    assert len(avisos) == 1 and "genérico" in avisos[0] and "apasionada por" in avisos[0]
    assert next(a for a in r["avisos"])["frase"] == MULETILLA
    assert r["preparacion"] == "pendiente_de_ti"


def test_cv_corto_se_rehace_y_si_sigue_sale_el_aviso(impl):
    r, prov = _correr(impl, [CV_CORTO, CARTA, APROBADO, CV_CORTO, CARTA])
    assert len(prov.llamadas) == 5 and "demasiado corto" in prov.llamadas[3]["usuario"]
    assert any("demasiado corto" in m for m in _mensajes(r, "cv"))


def test_muletilla_solo_en_la_carta_rehace_solo_la_carta(impl):
    r, prov = _correr(impl, [CV_BUENO, CARTA_CON_MULETILLA, APROBADO, CARTA])
    assert len(prov.llamadas) == 4 and r["redacciones_cv"] == 1 and r["redacciones_carta"] == 2
    assert "apasionada por" in prov.llamadas[3]["usuario"]
    assert r["avisos"] == []


def test_muletilla_persistente_en_la_carta_sale_como_aviso_de_la_carta(impl):
    r, prov = _correr(impl, [CV_BUENO, CARTA_CON_MULETILLA, APROBADO, CARTA_CON_MULETILLA])
    assert len(prov.llamadas) == 4
    assert any("genérico" in m for m in _mensajes(r, "carta")) and _mensajes(r, "cv") == []
