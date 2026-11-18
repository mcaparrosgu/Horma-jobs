"""Fase 5 · T02: proyectos, certificaciones y otros datos en el perfil (RF-5.1c)."""
# ruff: noqa: F401, F811  (fixtures importadas de otro módulo)
import pytest
from pydantic import ValidationError
from test_f2_t15_t19_api import (
    _perfil_hecho,
    _propietario,
    _usuaria_id,
    app,
    archivos,
    entrar,
)

from horma.schemas.perfil import Perfil
from horma.tools.componer_cv_maestro import componer_cv_maestro

pytestmark = pytest.mark.bd


def _o(texto: str) -> dict:
    return {"fuente": "usuaria", "fragmento": texto}


def test_el_esquema_acepta_las_tres_secciones_y_prohibe_campos_de_mas():
    p = Perfil.model_validate({
        "proyectos": [{"nombre": "Carta digital", "descripcion": "QR para el bar", "fecha": "2023",
                       "origen": _o("a")}],
        "certificaciones": [{"nombre": "Manipulador de alimentos", "entidad": "Cruz Roja",
                             "fecha": "2022", "origen": _o("b")}],
        "otros": [{"valor": "Carnet de conducir B", "origen": _o("c")}]})
    assert p.proyectos[0].nombre == "Carta digital" and p.otros[0].valor == "Carnet de conducir B"
    with pytest.raises(ValidationError):
        Perfil.model_validate({"proyectos": [{"nombre": "X", "edad": 30, "origen": _o("a")}]})


def test_el_maestro_incluye_las_tres_secciones_al_final():
    p = Perfil.model_validate({
        "habilidades": [{"nombre": "TPV", "origen": _o("h")}],
        "proyectos": [{"nombre": "Carta digital", "descripcion": "QR para el bar", "fecha": "2023",
                       "origen": _o("a")}],
        "certificaciones": [{"nombre": "Manipulador de alimentos", "entidad": "Cruz Roja",
                             "fecha": "2022", "origen": _o("b")}],
        "otros": [{"valor": "Carnet de conducir B", "origen": _o("c")}]})
    texto = componer_cv_maestro(p)
    encabezados = [x for x in texto.splitlines() if x.startswith("## ")]
    assert encabezados == ["## Habilidades", "## Proyectos", "## Certificaciones", "## Otros"]
    assert "Carta digital · 2023\nQR para el bar" in texto
    assert "Manipulador de alimentos · Cruz Roja · 2022" in texto
    assert "Carnet de conducir B" in texto


@pytest.mark.parametrize("campo,dato,corregido,clave", [
    ("proyectos", {"nombre": "Carta digital", "descripcion": "QR"}, {"nombre": "Carta QR"}, "nombre"),
    ("certificaciones", {"nombre": "Manipulador", "entidad": "Cruz Roja"},
     {"nombre": "Manipulador de alimentos", "entidad": "Cruz Roja"}, "nombre"),
    ("otros", {"valor": "Carnet B"}, {"valor": "Carnet B y coche propio"}, "valor"),
])
def test_se_pueden_anadir_corregir_y_quitar_por_la_api(app, motor_app, campo, dato, corregido, clave):
    c, h, _ = entrar(app)
    _perfil_hecho(motor_app, _usuaria_id(motor_app, "google-A"))
    # añadir: sin índice se añade al final de la lista
    r = c.patch("/api/perfil/datos", headers=h, json={"campo": campo, "indice": None, "dato": dato})
    assert r.status_code == 201, r.text
    lista = c.get("/api/perfil").json()["perfil"][campo]
    assert len(lista) == 1 and lista[0]["origen"]["fuente"] == "usuaria"
    r = c.patch("/api/perfil/datos", headers=h, json={"campo": campo, "indice": 0, "dato": corregido})
    assert r.status_code == 201, r.text
    assert c.get("/api/perfil").json()["perfil"][campo][0][clave] == corregido[clave]
    r = c.patch("/api/perfil/datos", headers=h, json={"campo": campo, "indice": 0, "dato": None})
    assert r.status_code == 201 and c.get("/api/perfil").json()["perfil"][campo] == []


def test_un_campo_prohibido_sigue_fallando(app, motor_app):
    c, h, _ = entrar(app)
    _perfil_hecho(motor_app, _usuaria_id(motor_app, "google-A"))
    r = c.patch("/api/perfil/datos", headers=h,
                json={"campo": "proyectos", "indice": None, "dato": {"nombre": "X", "edad": 30}})
    assert r.status_code == 422
    r = c.patch("/api/perfil/datos", headers=h,
                json={"campo": "edad", "indice": None, "dato": {"valor": "30"}})
    assert r.status_code == 422
