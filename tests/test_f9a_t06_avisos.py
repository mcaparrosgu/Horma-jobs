"""Fase 9a, T06: avisos_perfil."""
from horma.schemas.perfil import Perfil
from horma.tools.avisos_perfil import avisos_perfil

ORIG = {"fuente": "usuaria", "fragmento": "x"}


def perfil(descripcion="Atendía a 40 clientes al día", resumen=True, puesto="Camarera"):
    return Perfil.model_validate({
        "resumen": {"valor": "Resumen", "origen": ORIG} if resumen else None,
        "experiencias": [{"puesto": puesto, "empresa": "Hotel Mar", "inicio": "2020",
                          "descripcion": descripcion, "origen": ORIG}]})


def claves(**kw):
    return {a.clave.split(":")[0] for a in avisos_perfil(**kw)}


def test_perfil_completo_no_da_avisos():
    assert avisos_perfil(perfil(), "corto", {1: "ana@x.es"}) == []


def test_los_cinco_avisos():
    p = perfil(descripcion=None, resumen=False)
    k = claves(perfil=p, cv_maestro="palabra " * 1200, textos_cv={1: "sin datos"})
    assert k == {"largo", "sin_resumen", "sin_descripcion", "sin_contacto"}
    assert claves(perfil=perfil("Atendía a los clientes")) == {"sin_cifras"}


def test_contacto_por_correo_o_telefono():
    assert claves(perfil=perfil(), textos_cv={1: "Tel. 612 345 678"}) == set()
    assert claves(perfil=perfil(), textos_cv={1: "ana@correo.es"}) == set()
    a = avisos_perfil(perfil(), "", {7: "nada"})
    assert a[0].clave == "sin_contacto:7"


def test_la_huella_cambia_con_la_descripcion_y_la_clave_no():
    a = avisos_perfil(perfil("Atendía clientes"))[0]
    b = avisos_perfil(perfil("Atendía a todos los clientes"))[0]
    assert a.clave == b.clave and a.huella != b.huella
    assert avisos_perfil(perfil("Atendía clientes"))[0].huella == a.huella
