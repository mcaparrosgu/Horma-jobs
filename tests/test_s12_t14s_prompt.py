"""Spec 012 · T14s (RF-12.34; D-100 y D-113): el cambio de prompt de D-100, tal como está en el encargo T14m,
y una línea más para que las tareas de un puesto no se junten con otro."""
from horma.agents.matcher.agent import Matcher

TROZOS = (
    "Decide las marcas con todo el perfil: «no consta» es una regla de la explicación, no de las marcas.",
    "MySQL cubre SQL.",
    "“N años” se cubre con las fechas de los puestos",
    "No calcules años de experiencia: copia las fechas. Escribe “desde 2019” solo si el puesto sigue; "
    "si acabó, “de 2015 a 2025”.",
    "No cuentes los requisitos",
    "Las tareas de un puesto se citan solo con ese puesto: no las juntes con otro.",
)


def test_el_prompt_pide_el_cambio_de_d100_y_la_linea_de_d113():
    prompt = " ".join(Matcher.prompt().split())
    for trozo in TROZOS:
        assert trozo in prompt, trozo


def test_ya_no_pide_desde_2019_sin_mas():
    assert "escribe «desde 2019»" not in Matcher.prompt()
