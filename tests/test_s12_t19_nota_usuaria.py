"""Spec 012 · T19 (RF-12.26 a 12.26c, D-027, D-118, D-119, D-121, D-122):
la nota de la usuaria manda en su lista."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text

from horma.web.db import sesion_de, sesion_sistema
from horma.web.services import recomendaciones
from tests.test_f3_t14_t17_api import app, archivos, entrar  # noqa: F401
from tests.test_s9_t51_t53_informacion_nueva import _con_nota

RAIZ = Path(__file__).resolve().parent.parent
ESTATICOS = RAIZ / "horma" / "web" / "static"


def leer(n):
    return (ESTATICOS / n).read_text(encoding="utf-8")


def _fila(motor, u):
    [fila] = recomendaciones.listar(motor, u)
    return fila


def _corregir(motor, u, oferta, nota=None, comentario="", informacion=None):
    return recomendaciones.corregir(motor, u, oferta,
                                    {"nota": nota, "comentario": comentario, "informacion": informacion})


def _version_nueva_con_nota(motor, u, oferta):
    """Una versión más del perfil y su nota recalculada: la corrección queda en la fila anterior."""
    with sesion_de(motor, u) as s:
        s.execute(text(
            "insert into matches (usuaria_id, oferta_id, perfil_version, nota, condiciones, explicacion, "
            "cita_perfil, cita_oferta, retirada, huella_perfil) "
            "select usuaria_id, oferta_id, perfil_version + 1, 75, condiciones, explicacion, cita_perfil, "
            "cita_oferta, retirada, huella_perfil from matches where oferta_id = :o"), {"o": oferta})


@pytest.fixture
def puntuada(app, motor_app):  # noqa: F811
    _, _, u, oferta = _con_nota(app, motor_app)
    with sesion_de(motor_app, u) as s:
        s.execute(text("update matches set nota = 75, explicacion = "
                       "'Te la recomendamos por esto. Tienes sala. Piden sala.'"))
    with sesion_sistema(motor_app) as s:  # para que la lista la enseñe
        s.execute(text("update ofertas set fantasma = false, fraude = false, salario_publicado = false"))
    return u, oferta


@pytest.mark.bd
def test_su_nota_manda_en_el_veredicto_y_ensena_las_dos(motor_app, puntuada):
    a, oferta = puntuada
    _corregir(motor_app, a, oferta, nota=40, comentario="Pide carné y no lo tengo.")
    f = _fila(motor_app, a)
    assert (f["nota"], f["nota_usuaria"], f["veredicto"]) == (75, 40, "Poco compatible")
    assert f["correccion"]["comentario"] == "Pide carné y no lo tengo."
    assert not f["explicacion"].startswith("Te la recomendamos")


@pytest.mark.bd
def test_la_correccion_sigue_tras_otra_version_del_perfil(motor_app, puntuada):
    a, oferta = puntuada
    _corregir(motor_app, a, oferta, nota=40, comentario="Motivo")
    _version_nueva_con_nota(motor_app, a, oferta)
    assert _fila(motor_app, a)["nota_usuaria"] == 40
    assert recomendaciones.exportar(motor_app, a, oferta)["esperado"]["nota"] == 40


@pytest.mark.bd
def test_otra_correccion_sin_numero_conserva_su_nota_y_motivo(motor_app, puntuada):
    a, oferta = puntuada
    _corregir(motor_app, a, oferta, nota=40, comentario="Motivo")
    _version_nueva_con_nota(motor_app, a, oferta)
    guardada = _corregir(motor_app, a, oferta, informacion="Tengo el carné de manipuladora.")
    assert (guardada["nota"], guardada["comentario"]) == (40, "Motivo")
    f = _fila(motor_app, a)
    assert f["nota_usuaria"] == 40 and f["correccion"]["informacion"] == "Tengo el carné de manipuladora."


@pytest.mark.bd
def test_quitar_mi_nota_devuelve_la_de_horma_y_borra_la_correccion_entera(motor_app, puntuada):
    a, oferta = puntuada
    _corregir(motor_app, a, oferta, nota=40, comentario="Motivo", informacion="Algo")
    _version_nueva_con_nota(motor_app, a, oferta)
    _corregir(motor_app, a, oferta, nota=30)
    recomendaciones.quitar_correccion(motor_app, a, oferta)
    f = _fila(motor_app, a)
    assert (f["nota"], f["nota_usuaria"], f["correccion"]) == (75, None, None)
    assert f["veredicto"] == "Muy compatible"
    with pytest.raises(recomendaciones.SinNota):
        recomendaciones.quitar_correccion(motor_app, a, oferta)


@pytest.mark.bd
def test_quitar_por_la_api_pide_csrf_y_no_toca_la_de_otra(app, motor_app):  # noqa: F811
    c, h, _, oferta = _con_nota(app, motor_app)
    otra, h_otra, _ = entrar(app, "google-B")
    url = f"/api/matches/{oferta}/correccion"
    assert c.post(url, headers=h, json={"nota": 40}).status_code == 200
    assert c.delete(url).status_code == 403
    assert otra.delete(url, headers=h_otra).status_code == 404
    assert c.delete(url, headers=h).status_code == 200


def _node(codigo):
    node = shutil.which("node")
    if not node:
        pytest.skip("node no disponible")
    return json.loads(subprocess.run([node, "-e", codigo], capture_output=True, text=True, check=True).stdout)


def test_la_lista_ordena_y_filtra_con_su_nota():
    js = leer("ofertas.js")
    funciones = "".join(re.search(rf"function {n}\(\w+\) \{{.*?\n\}}", js, re.S).group(0)
                        for n in ("fechaOrden", "notaVista", "ordenar", "enRango"))
    codigo = funciones + """
let vista = { orden: "compatibles", min: 40, max: 100 };
const o = (id, nota, nota_usuaria) => ({ id, nota, nota_usuaria, creada_en: "2026-11-01" });
const todas = [o(1, 75, 20), o(2, 60, null), o(3, 10, 90)];
console.log(JSON.stringify([ordenar(todas).map((x) => x.id), todas.filter(enRango).map((x) => x.id)]));"""
    assert _node(codigo) == [[3, 2, 1], [2, 3]]


def test_la_pantalla_ensena_las_dos_notas_quitar_y_el_rotulo_de_horma():
    js, textos = leer("ofertas.js"), leer("textos.js")
    for pieza in ("TEXTOS.tuNota", "TEXTOS.quitarNota", "TEXTOS.loQueVioHorma", "corregidas.has",
                  "corregidas.clear"):
        assert pieza in js
    assert "La tuya: ${tuya} · Horma: ${horma}" in textos and "Quitar la mía" in textos
    assert "Lo que vio Horma (${n})" in textos
    ayuda = textos.split("corregirAyuda:")[1].split("\n")[0]
    assert "tu lista usa la tuya" in ayuda and "no cambian la compatibilidad" not in ayuda
    guia = (RAIZ / "specs" / "006-rediseno-2c" / "spec.md").read_text(encoding="utf-8")
    assert "La tuya" in guia.split("**Línea de compatibilidad**")[1].split("\n")[0]
