"""S9, correcciones de la prueba manual del 22-nov (RF-10.16)."""
from horma.schemas.candidatura import aviso_de_error, texto_de_formato
from horma.schemas.perfil import Perfil
from horma.tools.componer_cv_maestro import componer_cv_maestro
from horma.tools.medir_ats import errores_ats


def test_el_maestro_no_lleva_titulos_que_el_propio_horma_marque_como_raros():
    """RF-10.16a: «Otros» pasa a «Información adicional» y ningún título del maestro da aviso."""
    o = {"fuente": "usuaria", "fragmento": "x"}
    perfil = Perfil.model_validate({
        "nombre": "Ana",
        "experiencias": [{"puesto": "Camarera", "empresa": "Bar Sol", "inicio": "2020", "origen": o}],
        "proyectos": [{"nombre": "Web del bar", "origen": o}],
        "actividades": [{"descripcion": "Voluntaria en Cruz Roja", "origen": o}],
        "otros": [{"valor": "Carné de conducir B", "origen": o}]})
    maestro = componer_cv_maestro(perfil)
    assert "## Información adicional" in maestro and "## Otros" not in maestro
    assert errores_ats(maestro) == []


def test_el_aviso_de_titulo_raro_se_entiende_sin_saber_que_es_un_filtro():
    """RF-10.16b: dice qué sección, por qué importa y cómo arreglarlo; sin «ATS» ni «encabezado»."""
    m = aviso_de_error("cv", "Formato del CV para ATS: encabezado no estándar: «Cosas mías»").mensaje
    assert "«Cosas mías»" in m and "Información adicional" in m
    assert "ATS" not in m and "encabezado" not in m and "estándar" not in m
    assert "ATS" not in texto_de_formato("algo nuevo")
