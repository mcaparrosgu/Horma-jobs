"""Spec 011 · T08q · «Más recientes» ordena por la llegada a Horma (RF-11.32, D-034).
Antes ordenaba por `fecha_publicacion`; en las añadidas es texto copiado de la web («25/11/2026»,
«hace 23 horas»), `new Date` no lo entiende, contaba como 0 y la oferta caía al final
(la de lifeworq de Mar, la última).
Ejecuta en node la función `ordenar` real de `ofertas.js`."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"


def _fn(src: str, nombre: str) -> str:
    m = re.search(rf"function {nombre}\(.*?\n\}}", src, re.S)
    assert m, f"falta la función {nombre}"
    return m.group(0)


def _orden(orden: str) -> list[int]:
    node = shutil.which("node")
    if not node:
        pytest.skip("node no disponible")
    src = (ESTATICOS / "ofertas.js").read_text(encoding="utf-8")
    codigo = _fn(src, "fechaOrden") + _fn(src, "ordenar") + f"""
const vista = {{ orden: "{orden}" }};
const todas = [
  {{ id: 168, nota: 70, fecha_publicacion: "2026-11-22", creada_en: "2026-11-22T12:02:00+00:00" }},
  {{ id: 174, nota: 70, fecha_publicacion: "2026-11-25", creada_en: "2026-11-22T12:02:00+00:00" }},
  {{ id: 205, nota: 82, propia: true, fecha_publicacion: "25/11/2026",
     creada_en: "2026-11-25T17:23:49+00:00" }},
  {{ id: 199, nota: 82, propia: true, fecha_publicacion: "hace 23 horas",
     creada_en: "2026-11-25T16:36:05+00:00" }},
  {{ id: 206, nota: 75, propia: true, fecha_publicacion: "2026-11-24",
     creada_en: "2026-11-25T20:07:26+00:00" }},
  {{ id: 2, nota: 40, fecha_publicacion: "2026-11-03", creada_en: "2026-11-13T20:27:00+00:00" }},
];
console.log(JSON.stringify(ordenar(todas).map((o) => o.id)));"""
    return json.loads(subprocess.run([node, "-e", codigo], capture_output=True, text=True, check=True).stdout)


def test_mas_recientes_pone_arriba_la_ultima_que_llego_a_horma():
    # la añadida hace menos va primera aunque su fecha de publicación sea texto o anterior
    assert _orden("recientes") == [206, 205, 199, 174, 168, 2]   # a igual llegada (lote), id mayor primero


def test_a_igual_nota_mas_compatibles_desempata_por_llegada():
    assert _orden("compatibles") == [205, 199, 206, 174, 168, 2]
