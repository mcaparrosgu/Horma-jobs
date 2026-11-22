"""Fase 5 · T04: el extractor y el flujo `perfilar` cubren proyectos, certificaciones y otros (RF-5.1c)."""
import shutil
from pathlib import Path

from test_f2_t08_t10_flujos import _o, _perfilar

from horma.evals import correr_set
from horma.schemas.perfil import Perfil

RAIZ = Path(__file__).resolve().parent.parent
CV = ("Marta Gil\nCamarera en Café Central, 2020-2024\nCarta digital con códigos QR, 2023\n"
      "Carnet de conducir B")


def _flujo(extraccion):
    return _perfilar(extraccion, cvs=[{"cv_id": 1, "nombre": "CV", "texto": CV}])[1]


def test_las_tres_secciones_pasan_con_su_cita_y_entran_en_el_maestro():
    e = _flujo({"perfil": {
        "proyectos": [{"nombre": "Carta digital con códigos QR", "fecha": "2023",
                       "origen": _o(1, "Carta digital con códigos QR, 2023")}],
        "otros": [{"valor": "Carnet de conducir B", "origen": _o(1, "Carnet de conducir B")}]}})
    p = Perfil.model_validate(e["perfil"])
    assert p.proyectos[0].nombre.startswith("Carta digital") and p.otros[0].valor == "Carnet de conducir B"
    assert "## Proyectos" in e["cv_maestro"] and "## Información adicional" in e["cv_maestro"]


def test_un_proyecto_con_cita_inventada_va_a_pendientes():
    e = _flujo({"perfil": {"proyectos": [
        {"nombre": "Premio nacional", "origen": _o(1, "Premio nacional de hostelería")}]}})
    p = Perfil.model_validate(e["perfil"])
    assert p.proyectos == [] and "Premio nacional" in p.preguntas_pendientes[0].pregunta


def test_un_otro_dato_con_rasgo_personal_se_descarta():
    cv = "Marta Gil\nCasada y con dos hijos"
    _, e = _perfilar({"perfil": {"otros": [{"valor": "Casada y con dos hijos",
                                            "origen": _o(1, "Casada y con dos hijos")}]}},
                     cvs=[{"cv_id": 1, "nombre": "CV", "texto": cv}])
    assert Perfil.model_validate(e["perfil"]).otros == []
    assert "hijos" not in e["cv_maestro"]


def test_el_eval_perfil_simulado_pasa_con_los_casos_nuevos(tmp_path):
    destino = tmp_path / "evals"
    shutil.copytree(RAIZ / "evals", destino, ignore=shutil.ignore_patterns("resultados"))
    r = correr_set("perfil", raiz=destino, simulado=True)
    nuevos = [c for c in r["detalle"] if c["caso"].startswith(("13-", "14-"))]
    assert len(nuevos) == 2 and all(not c["fallos"] and "error" not in c for c in nuevos), nuevos
    assert r["aprobado"], r
