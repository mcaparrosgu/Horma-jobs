"""Spec 012, T05: puerta de puestos por niveles, tope de nivel y genéricos con familia (RF-12.5 a 12.10)."""
import pytest
from sqlalchemy import text

from horma.agents.clasificador_postulante.schemas import PuestoCandidato
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias, PuestoSugerido
from horma.schemas.taxonomia import Taxonomia
from horma.tools.buscar_ofertas import buscar_ofertas
from horma.tools.normalizar_titulo import casa_con_puestos, normalizar_titulo
from horma.tools.puestos_del_perfil import puestos_del_perfil


def _o(t):
    return {"fuente": "cv", "cv_id": 1, "fragmento": t}


def _perfil(experiencias=("Camarera",), formacion=("Grado en Estadística",), certificaciones=(),
            habilidades=("Excel",), titular=None):
    return Perfil.model_validate({
        "experiencias": [{"puesto": p, "origen": _o(p)} for p in experiencias],
        "formacion": [{"titulo": t, "origen": _o(t)} for t in formacion],
        "certificaciones": [{"nombre": c, "origen": _o(c)} for c in certificaciones],
        "habilidades": [{"nombre": h, "origen": _o(h)} for h in habilidades],
        "titular": {"valor": titular, "origen": _o(titular)} if titular else None})


def _puerta(perfil, *puestos, nivel="junior"):
    candidatos = [PuestoCandidato(titulo=t, idioma="es", dato=d) for t, d in puestos]
    return {p.titulo: p for p in puestos_del_perfil(perfil, candidatos, nivel)}


def test_una_habilidad_suelta_el_titular_o_un_trozo_quedan_fuera():
    perfil = _perfil(experiencias=("Camarera de sala",), titular="Controller financiero con Excel")
    salida = _puerta(perfil, ("Controller financiero", "Excel"),
                     ("Controller", "Controller financiero con Excel"), ("Camarera", "Camarera"),
                     ("Estadística", "Estadística"))
    assert set(salida) == {"Camarero/a de sala"}  # solo el que ha tenido (RF-12.6b)


def test_el_puesto_entero_de_una_experiencia_es_nivel_1_y_llega_marcado():
    p = _puerta(_perfil(), ("Sala", "camarera"))["Sala"]
    assert (p.nivel, p.tipo_dato, p.marcado) == (1, "puesto", True)


def test_titulacion_y_certificacion_enteras_son_nivel_2_sin_marcar():
    perfil = _perfil(certificaciones=("Manipulador de alimentos",))
    salida = _puerta(perfil, ("Analista de datos", "Grado en Estadística"),
                     ("Ayudante de cocina", "Manipulador de alimentos"))
    datos = {t: (p.nivel, p.tipo_dato, p.marcado) for t, p in salida.items()}
    assert datos == {"Camarero/a": (1, "puesto", True), "Analista de datos": (2, "titulacion", False),
                     "Ayudante de cocina": (2, "certificacion", False)}


def test_sin_ninguna_experiencia_los_de_titulacion_llegan_marcados():
    perfil = _perfil(experiencias=(), certificaciones=("Manipulador de alimentos",))
    salida = _puerta(perfil, ("Analista de datos", "Grado en Estadística"),
                     ("Ayudante de cocina", "Manipulador de alimentos"))
    assert salida["Analista de datos"].marcado and not salida["Ayudante de cocina"].marcado


def test_nunca_sugiere_por_encima_del_nivel_del_perfil_d038():
    perfil = _perfil()
    titulos = [("Senior Waitress", "Camarera"), ("Jefa de sala", "Camarera"), ("Team Lead", "Camarera"),
               ("Head Waiter", "Camarera"), ("Directora de sala", "Camarera")]
    suyo = {"Camarero/a"}  # va siempre (RF-12.6b)
    assert set(_puerta(perfil, *titulos, nivel="junior")) == suyo
    assert set(_puerta(perfil, *titulos, nivel="intermedio")) == suyo
    senior = {"Senior Waiter/waitress", "Jefe/a de sala", "Team Lead"}
    assert set(_puerta(perfil, *titulos, nivel="senior")) == senior | suyo
    assert len(_puerta(perfil, *titulos, nivel="direccion")) == 6
    assert len(_puerta(perfil, *titulos, nivel="sin_especificar")) == 6  # sin nivel no hay con qué comparar


def test_un_puesto_que_ya_ha_tenido_nunca_se_bloquea_d038():
    perfil = _perfil(experiencias=("Jefe de cocina",))
    assert "Jefe/a de cocina" in _puerta(perfil, ("Jefa de cocina", "Jefe de cocina"), nivel="junior")


def test_los_puestos_guardados_sin_nivel_son_de_nivel_2():
    p = PuestoSugerido(titulo="Data Analyst", dato="Analista")
    assert (p.nivel, p.tipo_dato) == (2, None)


@pytest.mark.parametrize("generico", ["Manager", "Técnico", "Técnica", "Responsable", "Especialista",
                                      "Consultor", "Engineer", "Developer", "Director", "Consultant"])
def test_un_generico_solo_casa_con_la_familia_del_perfil_o_sin_familia(generico):
    titulo = f"{generico} de proyectos"

    def casa(familia):
        return casa_con_puestos(titulo, [generico], familia_perfil="atencion_cliente",
                                familia_oferta=familia)

    assert casa("atencion_cliente") and casa(None) and not casa("marketing_comunicacion")


def test_un_puesto_concreto_casa_con_cualquier_familia():
    assert casa_con_puestos("Product Manager", ["Product Manager"], familia_perfil="atencion_cliente",
                            familia_oferta="marketing_comunicacion")


def test_el_filtro_sql_aplica_la_familia_solo_a_los_genericos(motor_migrador, bd_limpia):
    ofertas = [("Manager de ventas", "ventas_comercial"), ("Manager de soporte", "atencion_cliente"),
               ("Manager de tienda", None), ("Camarera", "hosteleria_restauracion")]
    tax = Taxonomia(sector="otros", familia="atencion_cliente", nivel="senior")
    with motor_migrador.begin() as c:
        for i, (t, f) in enumerate(ofertas):
            c.execute(text("insert into ofertas (texto_crudo, huella, titulo, titulo_norm, familia, estado, "
                           "fantasma, fraude) values ('t', :h, :t, :n, :f, 'procesada', false, false)"),
                      {"h": f"h{i}", "t": t, "n": normalizar_titulo(t), "f": f})
        consulta = buscar_ofertas(Preferencias(puestos=["Manager", "Camarera"]), tax)
        ids = [f.id for f in c.execute(text(consulta.sql), consulta.parametros)]
        titulos = {r for (r,) in c.execute(text("select titulo from ofertas where id = any(:i)"), {"i": ids})}
    assert titulos == {"Manager de soporte", "Manager de tienda", "Camarera"}


# --- T06: `relacion` (S1) solo baja de nivel ---------------------------------------------------
def test_un_titulo_afin_a_un_puesto_que_tuvo_es_nivel_2_sin_marcar():
    candidatos = [PuestoCandidato(titulo="Recepcionista", idioma="es", dato="Camarera", relacion="afin")]
    _, p = puestos_del_perfil(_perfil(), candidatos, "junior")
    assert (p.nivel, p.tipo_dato, p.marcado) == (2, "puesto", False)


def test_decir_mismo_no_sube_una_titulacion_a_nivel_1():
    candidatos = [PuestoCandidato(titulo="Estadística", idioma="es", dato="Grado en Estadística",
                                  relacion="mismo")]
    assert puestos_del_perfil(_perfil(), candidatos, "junior")[-1].nivel == 2  # el primero es el suyo


def test_el_clasificador_pide_relacion_y_no_propone_desde_una_habilidad():
    from pathlib import Path

    prompt = (Path(__file__).parent.parent / "horma/agents/clasificador_postulante/prompt.md").read_text(
        encoding="utf-8")
    assert "`relacion`" in prompt and "«mismo»" in prompt and "«afin»" in prompt
    assert "una habilidad no justifica" in prompt
    assert "relacion" in PuestoCandidato.model_json_schema()["properties"]
