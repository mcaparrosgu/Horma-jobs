"""Simplificación · S3: indicador de avance en la cabecera y subida al elegir archivo (T13-T14, spec 010)."""
import re
from pathlib import Path

import pytest
from sqlalchemy import text

from tests.test_f8_b_datos_api import app, entrar, tarea, usuaria  # noqa: F401  (fixtures y ayudas)

RAIZ = Path(__file__).resolve().parent.parent
ESTATICOS = RAIZ / "horma" / "web" / "static"
PROHIBIDAS = re.compile(r"\b(match|ATS|trazabilidad)\b", re.IGNORECASE)


def leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


# --- T13 · API ------------------------------------------------------------------------------------------
@pytest.mark.bd
def test_activas_sin_tipo_da_las_tareas_de_la_usuaria_con_su_url(app, motor_migrador):  # noqa: F811
    ana, _ = entrar(app, "google-A")
    berta, _ = entrar(app, "google-B")
    a, b = usuaria(motor_migrador, "google-A"), usuaria(motor_migrador, "google-B")
    t_cv = tarea(motor_migrador, a, tipo="perfilar", entidad=7, estado="en_curso")
    t_of = tarea(motor_migrador, a, tipo="recomendar", entidad=a)
    t_can = tarea(motor_migrador, a, tipo="candidatura", entidad=42)
    tarea(motor_migrador, a, tipo="candidatura", entidad=43, estado="hecha")
    t_berta = tarea(motor_migrador, b, tipo="puntuar_una", entidad=5)
    with motor_migrador.begin() as c:   # una tarea de la ingesta (sin usuaria) no sale a nadie
        c.execute(text("insert into tareas (usuaria_id, tipo, entidad_id, tope_coste) "
                       "values (null, 'procesar_oferta', 1, 1)"))
    r = {x["id"]: x for x in ana.get("/api/tareas/activas").json()["tareas"]}
    assert set(r) == {t_cv, t_of, t_can}
    assert r[t_cv]["url"] == "/perfil" and r[t_of]["url"] == "/ofertas"
    assert r[t_can]["url"] == "/candidaturas/42"
    assert {"tipo", "progreso", "estado"} <= set(r[t_cv])
    assert [x["id"] for x in berta.get("/api/tareas/activas").json()["tareas"]] == [t_berta]


@pytest.mark.bd
def test_el_indicador_desaparece_al_terminar(app, motor_migrador):  # noqa: F811
    ana, _ = entrar(app, "google-A")
    a = usuaria(motor_migrador, "google-A")
    t = tarea(motor_migrador, a, tipo="perfilar", estado="en_curso")
    assert [x["id"] for x in ana.get("/api/tareas/activas").json()["tareas"]] == [t]
    with motor_migrador.begin() as c:
        c.execute(text("update tareas set estado='hecha' where id=:i"), {"i": t})
    assert ana.get("/api/tareas/activas").json() == {"tareas": []}


# --- T13 · una sola barra, en la pantalla de la acción (RF-10.8, reescrito en S7) -------------------------
def test_ninguna_pagina_pinta_el_indicador_de_la_cabecera():
    for archivo in ("comun.js", "estilo.css", "textos.js", "perfil.js", "ofertas.js", "candidatura.js"):
        texto = leer(archivo)
        assert "indicador-avance" not in texto and "indicadorAvance" not in texto, archivo
    assert "FRASES_AVANCE" not in leer("textos.js")


def test_perfil_usa_la_barra_con_porcentaje_al_leer_el_cv():
    js = leer("perfil.js")
    assert "/api/tareas/activas?tipo=perfilar" in js
    assert 'barraAvance(estado, "Estamos leyendo tu CV").poner(progreso)' in js
    assert "innerHTML" not in leer("comun.js")


# --- T14 · subida al elegir el archivo ------------------------------------------------------------------
def test_no_hay_boton_subir_cv_y_el_cambio_del_archivo_sube():
    html, js = leer("perfil.html"), leer("perfil.js")
    assert "Subir CV</button>" not in html and 'id="escrito-por-ella"' not in html
    assert 'id="clase-cv"' not in html
    assert '$("archivo").addEventListener("change"' in js
    assert '$("archivo"), $("archivo-nombre"), "fuente")' in js
