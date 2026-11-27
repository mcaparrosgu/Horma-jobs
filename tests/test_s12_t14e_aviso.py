"""Spec 012 · T14e (RF-12.36, D-081): «Pide menos de lo que tienes», sin cambiar la nota."""
from pathlib import Path

import pytest
from sqlalchemy import text

from horma.llm.simulado import ProveedorSimulado
from horma.tools.nivel_pedido import pide_menos
from horma.web.db import sesion_de
from horma.web.queue import worker
from horma.web.services import recomendaciones
from tests.test_f2_t13_t14_bd_worker import (_encolar, _match, _oferta_procesada, _perfilar_hecho,
                                             _usuarias)

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
TEXTO = "Pide menos de lo que tienes"


@pytest.mark.parametrize("relacion, oferta, perfil, sale", [
    ("mismo_puesto", "junior", "senior", True), ("afin", "practicas", "junior", True),
    ("otro_oficio", "junior", "senior", False), ("mismo_puesto", "senior", "senior", False),
    ("mismo_puesto", "direccion", "senior", False), ("mismo_puesto", "sin_especificar", "senior", False),
    ("mismo_puesto", "junior", None, False), (None, "junior", "senior", False)])
def test_solo_con_nivel_inferior_y_puesto_cercano(relacion, oferta, perfil, sale):
    assert pide_menos(relacion, oferta, perfil) is sale


def test_se_guarda_la_relacion_y_la_lista_lo_avisa_sin_tocar_la_nota(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    oferta = _oferta_procesada(motor_app, pais="ES", nivel="practicas")
    pid = _perfilar_hecho(motor_app, a)
    _encolar(motor_app, a, "recomendar", pid)
    match = {**_match(oferta, nota=85), "relacion": "afin"}
    assert worker.procesar_una(motor_app, ProveedorSimulado([{"matches": [match]}])) == "hecha"
    with sesion_de(motor_app, a) as s:
        m = s.execute(text("select nota, nota_modelo, relacion, marcas from matches")).one()
    assert (m.nota, m.nota_modelo, m.relacion, m.marcas) == (85, 85, "afin", [])
    [fila] = recomendaciones.listar(motor_app, a)
    assert fila["pide_menos"] is True and fila["nota"] == 85


def test_la_pantalla_lo_ensena_con_el_componente_de_la_guia():
    js = (ESTATICOS / "ofertas.js").read_text(encoding="utf-8")
    textos = (ESTATICOS / "textos.js").read_text(encoding="utf-8")
    assert TEXTO in textos and "o.pide_menos" in js and "linea-compat" in js
    assert ".linea-compat" in (ESTATICOS / "estilo.css").read_text(encoding="utf-8")
    guia = (Path(__file__).resolve().parent.parent / "specs" / "006-rediseno-2c" / "spec.md")
    assert "Línea de compatibilidad" in guia.read_text(encoding="utf-8")
