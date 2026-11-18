"""Siembra la tabla `fuentes` desde config/endpoints.json (RF-1.1). No pisa fuentes existentes."""
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

from horma.tools.semilla import RUTA, fuentes_semilla


def sembrar_fuentes(conexion: Connection, ruta: Path = RUTA, *, campos_fase5: bool = True) -> int:
    """Inserta las fuentes que falten (las nuevas, siempre inactivas). Devuelve cuántas insertó.

    `campos_fase5=False` es para la migración 0002, cuando la tabla aún no tiene los campos de la
    fase 5 (auth_basica, detalle, cada_horas, atribucion)."""
    n = 0
    for f in fuentes_semilla(ruta):
        columnas = "nombre, web, url, metodo, parametros, cabeceras, variable_clave, mapeo, activa"
        valores = (":nombre, :web, :url, :metodo, cast(:parametros as jsonb), "
                   "cast(:cabeceras as jsonb), :variable_clave, cast(:mapeo as jsonb), false")
        if campos_fase5:
            columnas += ", auth_basica, detalle, cada_horas, atribucion"
            valores += (", cast(:auth_basica as jsonb), cast(:detalle as jsonb), :cada_horas, "
                        ":atribucion")
        n += conexion.execute(text(
            f"insert into fuentes ({columnas}) values ({valores}) on conflict (nombre) do nothing"),
            {**f.model_dump(), "parametros": json.dumps(f.parametros),
             "cabeceras": json.dumps(f.cabeceras), "mapeo": json.dumps(f.mapeo),
             "auth_basica": json.dumps(f.auth_basica) if f.auth_basica else None,
             "detalle": json.dumps(f.detalle.model_dump()) if f.detalle else None}).rowcount
    return n
