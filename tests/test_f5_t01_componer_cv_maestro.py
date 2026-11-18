"""Fase 5 · T01: `componer_cv_maestro` convierte el perfil en el CV maestro, siempre igual (RF-5.1)."""
from horma.schemas.perfil import Perfil
from horma.tools.componer_cv_maestro import componer_cv_maestro
from horma.tools.rasgos_personales import rasgos_personales


def _o(texto: str) -> dict:
    return {"fuente": "usuaria", "fragmento": texto}


def _perfil(**cambios) -> Perfil:
    datos = {
        "nombre": "Ana Ferrer",
        "titular": {"valor": "Camarera con 7 años de sala", "origen": _o("titular")},
        "resumen": {"valor": "Siete años en hostelería y comercio.", "origen": _o("resumen")},
        "experiencias": [
            {"puesto": "Camarera", "empresa": "Bar Sol", "inicio": "2021", "fin": "2024",
             "descripcion": "Atención de mesas y barra en un bar de 40 plazas", "origen": _o("x")},
            {"puesto": "Dependienta", "empresa": "Moda Sur", "inicio": "2018", "fin": "2019",
             "origen": _o("y")},
        ],
        "formacion": [{"titulo": "Técnico en Restauración", "centro": "IES Ausiàs March",
                       "inicio": "2017", "fin": "2019", "origen": _o("z")}],
        "idiomas": [{"idioma": "en", "nivel": "B1", "origen": _o("i")},
                    {"idioma": "ca", "nivel": "nativo", "origen": _o("j")}],
        "habilidades": [{"nombre": "Manejo de TPV", "origen": _o("h")},
                        {"nombre": "Gestión de caja", "origen": _o("h2")}],
    }
    return Perfil.model_validate({**datos, **cambios})


def test_el_mismo_perfil_da_el_mismo_texto():
    assert componer_cv_maestro(_perfil()) == componer_cv_maestro(_perfil())


def test_cada_dato_aparece_en_su_seccion():
    texto = componer_cv_maestro(_perfil())
    secciones = {}
    actual = ""
    for linea in texto.splitlines():
        if linea.startswith("## "):
            actual = linea[3:]
            secciones[actual] = []
        elif actual:
            secciones[actual].append(linea)
    assert list(secciones) == ["Resumen", "Experiencia", "Formación", "Idiomas", "Habilidades"]
    assert texto.startswith("# Ana Ferrer")
    assert "Camarera con 7 años de sala" in texto
    assert "Siete años en hostelería y comercio." in "\n".join(secciones["Resumen"])
    exp = "\n".join(secciones["Experiencia"])
    assert "Camarera · Bar Sol · 2021-2024" in exp
    assert "Atención de mesas y barra en un bar de 40 plazas" in exp
    assert "Dependienta · Moda Sur · 2018-2019" in exp
    assert "Técnico en Restauración · IES Ausiàs March · 2017-2019" in "\n".join(secciones["Formación"])
    assert "Inglés B1" in "\n".join(secciones["Idiomas"])
    assert "Catalán nativo" in "\n".join(secciones["Idiomas"])
    assert "Manejo de TPV" in "\n".join(secciones["Habilidades"])
    assert "Gestión de caja" in "\n".join(secciones["Habilidades"])


def test_un_dato_quitado_no_aparece_y_su_seccion_vacia_tampoco():
    p = _perfil(experiencias=[], idiomas=[])
    texto = componer_cv_maestro(p)
    assert "Bar Sol" not in texto and "Moda Sur" not in texto
    assert "## Experiencia" not in texto and "## Idiomas" not in texto
    assert "## Formación" in texto


def test_un_fin_vacio_no_deja_guion_suelto_y_actual_se_respeta():
    p = _perfil(experiencias=[
        {"puesto": "Camarera", "empresa": "Bar Sol", "inicio": "2021", "fin": "actual", "origen": _o("x")},
        {"puesto": "Cocinera", "inicio": "2019", "origen": _o("y")},
        {"puesto": "Ayudante", "empresa": "La Barca", "origen": _o("w")},
    ])
    lineas = componer_cv_maestro(p).splitlines()
    assert "Camarera · Bar Sol · 2021-actual" in lineas
    assert "Cocinera · 2019" in lineas
    assert "Ayudante · La Barca" in lineas


def test_sin_rasgos_personales_ni_genero():
    texto = componer_cv_maestro(_perfil(genero_puestos="femenino"))
    assert rasgos_personales(texto) == []
    assert "femenino" not in texto.lower()
