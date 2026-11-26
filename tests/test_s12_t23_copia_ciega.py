"""Spec 012, T23 (RF-12.30, 12.30a, 12.30b, 12.30d; D-044, D-045, D-051): la copia ciega del perfil."""
import json
from pathlib import Path

import pytest

from horma.evals_puestos import _variante
from horma.schemas.perfil import Perfil
from horma.schemas.perfil_ciego import PerfilCiego
from horma.tools.copia_ciega import copia_ciega

ORIGEN = {"fuente": "usuaria", "fragmento": "x"}


def _perfil(**cambios) -> Perfil:
    return Perfil.model_validate(cambios)


def _exp(puesto, descripcion=None, empresa="Hotel Sol", inicio="2019-03", fin="actual"):
    return {"puesto": puesto, "empresa": empresa, "inicio": inicio, "fin": fin,
            "descripcion": descripcion, "origen": ORIGEN}


def test_el_esquema_lleva_solo_la_lista_blanca():
    esquema = PerfilCiego.model_json_schema()
    assert set(esquema["properties"]) == {"experiencias", "formacion", "idiomas", "habilidades", "proyectos",
                                          "certificaciones", "otros", "taxonomia"}
    campos = {n: set(d["properties"]) for n, d in esquema["$defs"].items()
              if n.endswith(("Ciego", "Ciega"))}
    assert campos == {
        "ExperienciaCiega": {"puesto", "empresa", "inicio", "fin", "descripcion"},
        "FormacionCiega": {"titulo", "inicio", "fin"},
        "IdiomaCiego": {"idioma", "nivel"},
        "HabilidadCiega": {"nombre"},
        "ProyectoCiego": {"nombre", "descripcion", "fecha"},
        "CertificacionCiega": {"nombre", "entidad", "fecha"},
        "OtroCiego": {"valor"},
    }
    with pytest.raises(ValueError):
        PerfilCiego.model_validate({"nombre": "Lucía"})


def test_borra_contacto_y_nombre_y_no_toca_fechas_ni_el_original():
    perfil = _perfil(nombre="Lucía Herrero", experiencias=[_exp(
        "Herrero", "Lucía Herrero (lucia.h@correo.es, +34 612 34 56 78, https://lucia.dev/cv, "
                   "linkedin.com/in/lucia) forjó rejas en 2019-2023 con ASP.NET y Node.js")])
    antes = perfil.model_dump_json()
    x = copia_ciega(perfil).experiencias[0]
    assert x.puesto == "Herrero"  # D-051: en el puesto no se borra el apellido
    for fuera in ("Lucía", "Herrero", "correo", "612", "lucia", "linkedin"):
        assert fuera not in x.descripcion
    assert "2019-2023" in x.descripcion and "ASP.NET y Node.js" in x.descripcion
    assert (x.inicio, x.fin) == ("2019-03", "actual")
    assert perfil.model_dump_json() == antes


def test_las_particulas_del_nombre_no_se_borran():
    perfil = _perfil(nombre="María del Carmen San José", experiencias=[_exp(
        "Camarera", "atención en la terraza del hotel y las mesas de San Juan; María del Carmen")])
    d = copia_ciega(perfil).experiencias[0].descripcion
    assert "del hotel" in d and "las mesas" in d and "San Juan" in d
    assert "María" not in d and "Carmen" not in d


def test_la_taxonomia_solo_si_se_pide():
    tax = {"sector": "otros", "familia": "otros", "nivel": "junior", "stack": []}
    perfil = _perfil(taxonomia=tax)
    assert copia_ciega(perfil).taxonomia is None
    assert copia_ciega(perfil, con_taxonomia=True).taxonomia.nivel == "junior"


# Gemelas escritas a mano (no con el léxico): (puesto, descripción, título) en femenino y en masculino.
GEMELAS = [
    (("Secretaria de dirección", "fui la secretaria de las abogadas", "Diplomada en Turismo"),
     ("Secretario de dirección", "fui el secretario de los abogados", "Diplomado en Turismo")),
    (("Asistenta", "como empleada cuidé de la casa", "Graduada en ESO"),
     ("Empleado de hogar", "como empleado cuidé de la casa", "Graduado en ESO")),
    (("Gobernanta de hotel", "una gobernanta con 12 camareras de pisos", "Técnica en Alojamiento"),
     ("Gobernante de hotel", "un gobernante con 12 camareros de pisos", "Técnico en Alojamiento")),
    (("Modista", "la encargada del taller y ayudante de la diseñadora", "Licenciada en Bellas Artes"),
     ("Modisto", "el encargado del taller y ayudante del diseñador", "Licenciado en Bellas Artes")),
    (("Auxiliar administrativa", "apoyo a la directora y a las vendedoras", "Técnica Superior en Finanzas"),
     ("Auxiliar administrativo", "apoyo al director y a los vendedores", "Técnico Superior en Finanzas")),
]


def _gemela(nombre, genero, datos):
    puesto, descripcion, titulo = datos
    return _perfil(nombre=nombre, genero_puestos=genero, titular={"valor": puesto, "origen": ORIGEN},
                   experiencias=[_exp(puesto, f"{nombre.split()[0]}: {descripcion}")],
                   formacion=[{"titulo": titulo, "centro": f"IES {nombre}", "origen": ORIGEN}])


@pytest.mark.parametrize("ella, el", GEMELAS)
def test_gemelas_a_mano_dan_la_misma_copia(ella, el):
    a = copia_ciega(_gemela("Marta Ruiz", "femenino", ella))
    b = copia_ciega(_gemela("Mario Ruiz", "masculino", el))
    assert a.model_dump_json() == b.model_dump_json()


def _parejas_del_set():
    for caso in sorted(Path("evals/puestos/casos").iterdir()):
        datos = json.loads((caso / "entrada.json").read_text(encoding="utf-8"))
        if datos.get("variante"):
            yield pytest.param(datos, id=caso.name)


@pytest.mark.parametrize("datos", list(_parejas_del_set()))
def test_gemelas_del_set_dan_la_misma_copia(datos):
    ella = copia_ciega(Perfil.model_validate(datos["perfil"]))
    el = copia_ciega(Perfil.model_validate(_variante(datos["perfil"], datos["variante"])))
    assert ella.model_dump_json() == el.model_dump_json()


def test_hay_al_menos_diez_gemelas():
    assert len(GEMELAS) + len(list(_parejas_del_set())) >= 10
