"""Siembra la tabla `fuentes` desde config/endpoints.json (RF-1.1). No pisa fuentes existentes."""
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

from horma.tools.semilla import RUTA, fuentes_semilla


def sembrar_fuentes(conexion: Connection, ruta: Path = RUTA) -> int:
    """Inserta las fuentes que falten (las nuevas, siempre inactivas). Devuelve cuántas insertó."""
    n = 0
    for f in fuentes_semilla(ruta):
        n += conexion.execute(text(
            "insert into fuentes (nombre, web, url, metodo, parametros, cabeceras, variable_clave, "
            "mapeo, activa) values (:nombre, :web, :url, :metodo, cast(:parametros as jsonb), "
            "cast(:cabeceras as jsonb), :variable_clave, cast(:mapeo as jsonb), false) "
            "on conflict (nombre) do nothing"),
            {**f.model_dump(), "parametros": json.dumps(f.parametros),
             "cabeceras": json.dumps(f.cabeceras), "mapeo": json.dumps(f.mapeo)}).rowcount
    return n
