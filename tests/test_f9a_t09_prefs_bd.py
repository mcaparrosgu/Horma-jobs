"""Fase 9a, T09: una subida nueva no pisa los puestos que marcó ella."""
import pytest
from sqlalchemy import text

from horma.schemas.preferencias import Preferencias
from horma.web.db import sesion_de
from horma.web.repositories import perfiles

pytestmark = pytest.mark.bd

SUG = [{"titulo": "Data Analyst", "dato": "Analista de datos"}, {"titulo": "BI Analyst", "dato": "Excel"}]


def test_subida_nueva_no_pisa_los_puestos_de_ella(motor_app, motor_migrador, bd_limpia):
    with motor_migrador.begin() as c:
        u = c.execute(text("insert into usuarias (google_sub) values ('a') returning id")).scalar_one()
    with sesion_de(motor_app, u) as s:
        perfiles.aplicar_preferencias_del_cv(s, u, Preferencias(
            puestos=["Data Analyst", "BI Analyst"], puestos_sugeridos=SUG, origen={"puestos": "cv"}))
        assert perfiles.preferencias(s).origen["puestos"] == "cv"
    with sesion_de(motor_app, u) as s:  # ella marca solo uno
        p = perfiles.preferencias(s)
        p.puestos, p.origen["puestos"] = ["BI Analyst"], "usuaria"
        perfiles.guardar_preferencias(s, u, p)
    with sesion_de(motor_app, u) as s:  # sube un CV nuevo: sugeridos nuevos
        nuevos = [{"titulo": "Analista BI", "dato": "Excel"}]
        perfiles.aplicar_preferencias_del_cv(s, u, Preferencias(
            puestos=["Analista BI"], puestos_sugeridos=nuevos, origen={"puestos": "cv"}))
        perfiles.aplicar_puestos_del_cv(s, u, nuevos)
    with sesion_de(motor_app, u) as s:
        p = perfiles.preferencias(s)
        assert p.puestos == ["BI Analyst"] and p.origen["puestos"] == "usuaria"
        assert [x.titulo for x in p.puestos_sugeridos] == ["Analista BI"]
