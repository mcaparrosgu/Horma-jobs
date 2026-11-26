"""Spec 012, T22 (RF-12.30c; D-043 y D-049): léxico de género de la copia ciega."""
import json
from pathlib import Path

import pytest

from horma.tools.lexico_genero import a_copia, en_genero

# (en el CV, en la copia, femenino, masculino)
TABLA = [
    ("Secretaria de dirección", "Secretario/a de dirección",
     "Secretaria de dirección", "Secretario de dirección"),
    ("Asistenta", "Empleado/a de hogar", "Empleada de hogar", "Empleado de hogar"),
    ("Asistente de dirección", "Asistente de dirección", "Asistente de dirección", "Asistente de dirección"),
    ("Gobernanta", "Gobernante/a", "Gobernanta", "Gobernante"),
    ("Modista", "Modista", "Modista", "Modista"),
    ("Modisto", "Modista", "Modista", "Modista"),
    ("Licenciada en Derecho", "Licenciado/a en Derecho", "Licenciada en Derecho", "Licenciado en Derecho"),
    ("Enfermera titulada", "Enfermero/a titulado/a", "Enfermera titulada", "Enfermero titulado"),
    ("Actriz", "Actor/actriz", "Actriz", "Actor"),
    ("Jueza", "Juez/a", "Jueza", "Juez"),
    ("Matrona", "Matrón/a", "Matrona", "Matrón"),
    ("Waitress", "Waiter/waitress", "Waitress", "Waiter"),
    ("Técnica de laboratorio", "Técnico/a de laboratorio",
     "Técnica de laboratorio", "Técnico de laboratorio"),
    ("Camarera", "Camarero/a", "Camarera", "Camarero"),
    ("Dependienta", "Dependiente/a", "Dependienta", "Dependiente"),
    ("Jefa de cocina", "Jefe/a de cocina", "Jefa de cocina", "Jefe de cocina"),
]


@pytest.mark.parametrize("cv, copia, femenino, masculino", TABLA)
def test_tabla(cv, copia, femenino, masculino):
    assert a_copia(cv, titulo=True) == copia
    assert en_genero(copia, "femenino") == femenino
    assert en_genero(copia, "masculino") == masculino
    assert en_genero(copia, None) == copia
    # La forma masculina da la misma copia (gemelas), salvo «Asistenta», que no tiene gemelo.
    if cv != "Asistenta":
        assert a_copia(masculino, titulo=True) == copia


@pytest.mark.parametrize("texto", [
    "Secretaría General", "Grado en Química", "Costurera", "Gestión de tareas administrativas",
    "Mejora de la técnica de venta", "Marketing Director", "Photo Editor", "Ingeniería Informática",
    "Atención al cliente", "Cuidado de personas dependientes",
])
def test_no_cambia(texto):
    assert a_copia(texto, titulo=True) == texto


@pytest.mark.parametrize("cv, copia", [
    ("Auxiliar administrativa", "Auxiliar administrativo/a"),
    ("Auxiliar administrativo", "Auxiliar administrativo/a"),
    ("Administrativa de contabilidad", "Administrativo/a de contabilidad"),
    ("Asesora jurídica laboral", "Asesor/a jurídico/a laboral"),
    ("Camarera/o para restaurante", "Camarero/a para restaurante"),
    ("Cajero(a)", "Cajero/a"),
    ("TECNICA de selección", "TÉCNICO/A de selección"),
    ("Director de RRHH", "Director/a de RRHH"),
])
def test_adjetivos_marcas_y_mayusculas(cv, copia):
    assert a_copia(cv, titulo=True) == copia


@pytest.mark.parametrize("femenino, masculino, copia", [
    ("coordiné a 6 camareras como la encargada", "coordiné a 6 camareros como el encargado",
     "coordiné a 6 camareros/as como el/la encargado/a"),
    ("apoyo a las enfermeras de la directora", "apoyo a los enfermeros del director",
     "apoyo a los/a las enfermeros/as del/de la director/a"),
    ("fui una responsable", "fui un responsable", "fui un/una responsable"),
])
def test_descripciones_con_articulos_y_plurales(femenino, masculino, copia):
    assert a_copia(femenino) == copia
    assert a_copia(masculino) == copia
    assert en_genero(copia, "femenino") == femenino
    assert en_genero(copia, "masculino") == masculino


def _textos_de_los_sets():
    def andar(v):
        if isinstance(v, dict):
            for k, x in v.items():
                if k in ("puesto", "titulo", "descripcion") and isinstance(x, str):
                    yield x
                else:
                    yield from andar(x)
        elif isinstance(v, list):
            for x in v:
                yield from andar(x)

    for carpeta in ("evals/puestos/casos", "evals/perfil/casos"):
        for f in sorted(Path(carpeta).rglob("*.json")):
            yield from andar(json.loads(f.read_text(encoding="utf-8")))


def test_copiar_dos_veces_no_cambia_nada():
    textos = list(_textos_de_los_sets())
    assert textos
    for t in textos:
        copia = a_copia(t, titulo=True)
        assert a_copia(copia, titulo=True) == copia, t
