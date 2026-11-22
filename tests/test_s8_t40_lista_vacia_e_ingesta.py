"""S8, T40: lista vacía con motivo (RF-10.14q) e ingesta atascada (RF-10.14r)."""
from pathlib import Path

from sqlalchemy import text

from horma.web.db import sesion_sistema
from horma.web.repositories import ingesta as repo

ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"


def _fuente(c) -> int:
    return c.execute(text(
        "insert into fuentes (nombre, web, url, mapeo) values ('prueba-s8', 'https://x.es', "
        "'https://x.es/api', '{}') returning id")).scalar_one()


def _en_curso(c, fuente_id: int, hace: str) -> int:
    return c.execute(text(
        "insert into ejecuciones_ingesta (fuente_id, estado, iniciada_en) values "
        f"(:f, 'en_curso', now() - interval '{hace}') returning id"), {"f": fuente_id}).scalar_one()


def test_una_ejecucion_en_curso_de_31_min_se_cierra_y_una_de_5_no(motor_app, motor_migrador, bd_limpia):
    with motor_migrador.begin() as c:
        f = _fuente(c)
        vieja, reciente = _en_curso(c, f, "31 minutes"), _en_curso(c, f, "5 minutes")
        nueva = c.execute(text("insert into ejecuciones_ingesta (fuente_id) values (:f) returning id"),
                          {"f": f}).scalar_one()
    with sesion_sistema(motor_app) as s:
        reclamada = repo.reclamar_ejecucion(s)
        assert reclamada["id"] == nueva
        v, r = repo.ejecucion(s, vieja), repo.ejecucion(s, reciente)
    assert v["estado"] == "error" and v["motivo_error"] == "Se cortó sin terminar" and v["terminada_en"]
    assert r["estado"] == "en_curso" and r["motivo_error"] is None


def test_ofertas_dice_por_que_la_lista_esta_vacia():
    textos = (ESTATICOS / "textos.js").read_text(encoding="utf-8")
    js = (ESTATICOS / "ofertas.js").read_text(encoding="utf-8")
    assert "Ninguna oferta casa ahora con los puestos que marcaste. Desmarca alguno o añade una oferta." in textos
    assert "TEXTOS.listaVaciaPorPuestos" in js and "puestos.some((p) => p.marcado)" in js
