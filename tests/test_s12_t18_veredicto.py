"""Spec 012 · T18 (RF-12.17, RF-12.25, D-026, D-120): veredicto, línea de condiciones y empate."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from horma.llm.simulado import ProveedorSimulado
from horma.schemas.match import veredicto
from horma.schemas.preferencias import Preferencias
from horma.tools.evaluar_condiciones import faltas
from horma.web.db import sesion_de
from horma.web.queue import worker
from horma.web.repositories import perfiles
from horma.web.routers.recomendaciones import _salario
from horma.web.services import recomendaciones
from tests.test_f2_condiciones import oferta
from tests.test_f2_t13_t14_bd_worker import _encolar, _match, _oferta_procesada, _perfilar_hecho, _usuarias

RAIZ = Path(__file__).resolve().parent.parent
ESTATICOS = RAIZ / "horma" / "web" / "static"


@pytest.mark.parametrize("nota, texto", [
    (100, "Muy compatible"), (70, "Muy compatible"), (69, "Compatible"), (50, "Compatible"),
    (49, "Poco compatible"), (30, "Poco compatible"), (29, "No te la recomendamos"),
    (0, "No te la recomendamos")])
def test_el_veredicto_sale_de_la_nota(nota, texto):
    assert veredicto(nota) == texto


def test_sin_condiciones_marcadas_no_falta_nada():
    assert faltas(oferta(salario=None, contrato=None), Preferencias()) == []


@pytest.mark.parametrize("cambios, prefs, esperado", [
    ({"contrato": None}, {"contratos": ["indefinido"]}, ["No dice el contrato"]),
    ({"contrato": "temporal"}, {"contratos": ["indefinido"]}, ["Contrato temporal"]),
    ({"contrato": "prácticas"}, {"contratos": ["indefinido"]}, ["Contrato en prácticas"]),
    ({"ubicacion": None, "remoto": None}, {"paises": ["ES"]}, ["No dice el país"]),
    ({"ubicacion": "Paris"}, {"paises": ["ES"]}, ["En Francia"]),
    ({"idiomas": []}, {"idiomas": ["es"]}, ["No dice el idioma"]),
    ({"idiomas": ["francés", "alemán"]}, {"idiomas": ["es"]}, ["Pide francés y alemán"]),
    ({"modalidad": None, "remoto": None}, {"solo_remoto": True}, ["No dice si es remoto"]),
    ({"modalidad": "hibrido"}, {"solo_remoto": True}, ["No es remoto"]),
    ({"salario": None}, {"sueldo_minimo": 16000}, ["No dice el sueldo"]),
    ({"salario": None}, {"sueldo_minimo": 16000, "solo_salario": True}, ["No dice el sueldo"]),
])
def test_cada_condicion_que_falta_tiene_su_texto(cambios, prefs, esperado):
    assert faltas(oferta(**cambios), Preferencias(**prefs)) == esperado


def test_un_sueldo_por_debajo_del_suyo():
    assert faltas(oferta(), Preferencias(sueldo_minimo=10**7)) == ["El sueldo es inferior a tu mínimo"]


@pytest.mark.parametrize("salario, frase, esperado", [
    ({"minimo": 12, "moneda": "EUR"}, "Pago: 12 €/h", "Sueldo que no se puede comparar: 12 EUR por hora"),
    ({"minimo": 15, "maximo": 18, "moneda": "GBP"}, "£15-18 per hour",
     "Sueldo que no se puede comparar: 15–18 GBP por hora"),
    ({"minimo": 30000, "moneda": "GBP"}, "30,000 GBP per year", "Sueldo que no se puede comparar: 30000 GBP"),
])
def test_un_sueldo_que_no_se_puede_comparar_ensena_moneda_y_hora(salario, frase, esperado):
    assert faltas(oferta(salario=salario), Preferencias(sueldo_minimo=16000), frase) == [esperado]


def test_la_columna_de_salario_dice_por_hora():
    f = {"salario_rango": "12 EUR", "salario_por_hora": True}
    assert _salario(f) == "12 EUR por hora"
    assert _salario({**f, "salario_por_hora": False}) == "12 EUR"


@pytest.mark.bd
def test_la_lista_da_veredicto_y_faltas_sin_tocar_la_nota(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    oid = _oferta_procesada(motor_app, pais="ES")
    pid = _perfilar_hecho(motor_app, a)
    _encolar(motor_app, a, "recomendar", pid)
    assert worker.procesar_una(motor_app, ProveedorSimulado([{"matches": [_match(oid, nota=69)]}])) == "hecha"
    with sesion_de(motor_app, a) as s:  # el CV de ejemplo marca idiomas: se parte sin condiciones
        perfiles.guardar_preferencias(s, a, Preferencias())
    [antes] = recomendaciones.listar(motor_app, a)
    with sesion_de(motor_app, a) as s:
        perfiles.guardar_preferencias(s, a, Preferencias(sueldo_minimo=10**7))
    [fila] = recomendaciones.listar(motor_app, a)
    assert antes["faltas"] == [] and antes["veredicto"] == "Compatible"
    assert fila["faltas"] and fila["nota"] == 69 and fila["veredicto"] == "Compatible"


def test_a_igual_nota_va_antes_la_que_cumple_todo():
    node = shutil.which("node")
    if not node:
        pytest.skip("node no disponible")
    js = (ESTATICOS / "ofertas.js").read_text(encoding="utf-8")
    funciones = "".join(re.search(rf"function {n}\(\w+\) \{{.*?\n\}}", js, re.S).group(0)
                        for n in ("fechaOrden", "notaVista", "ordenar"))
    codigo = funciones + """
let vista = { orden: "compatibles" };
const o = (id, nota, faltas, dia) => ({ id, nota, faltas, creada_en: `2026-11-${dia}` });
console.log(JSON.stringify(ordenar([o(1, 80, ["No dice el sueldo"], 20), o(2, 80, [], 10), o(3, 90, ["x"], 1),
                                    o(4, 80, [], 11)]).map((x) => x.id)));"""
    salida = subprocess.run([node, "-e", codigo], capture_output=True, text=True, check=True).stdout
    assert json.loads(salida) == [3, 4, 2, 1]


def test_la_pantalla_lo_ensena_con_el_componente_de_la_guia():
    js = (ESTATICOS / "ofertas.js").read_text(encoding="utf-8")
    assert "o.veredicto" in js and "o.faltas" in js and "linea-compat" in js
    assert ".linea-compat.veredicto" in (ESTATICOS / "estilo.css").read_text(encoding="utf-8")
    guia = (RAIZ / "specs" / "006-rediseno-2c" / "spec.md").read_text(encoding="utf-8")
    assert "veredicto" in guia.split("**Línea de compatibilidad**")[1].split("\n")[0]
