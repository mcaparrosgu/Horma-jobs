"""S8, T42: borrar un CV rehace el perfil con los que quedan (RF-10.14)."""
from pathlib import Path

import pytest
from sqlalchemy import text

from horma.llm.simulado import ProveedorSimulado
from horma.web.db import sesion_de
from horma.web.queue import worker
from horma.web.repositories import cv as repo_cv
from horma.web.repositories import perfiles
from horma.web.services import cv as servicio_cv
from horma.web.services import perfil as servicio_perfil
from tests.test_f2_t13_t14_bd_worker import CV, TAX, _cv, _usuarias

pytestmark = [pytest.mark.bd, pytest.mark.usefixtures("juez_automatico")]
CV_B = "Ana Pérez\nDependienta en Moda Sur, 2015-2018"
ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"


def _extraccion(cv_id, texto, puesto, empresa):
    return {"perfil": {"experiencias": [{"puesto": puesto, "empresa": empresa, "origen": {
        "fuente": "cv", "cv_id": cv_id, "fragmento": texto.split("\n")[1].split(",")[0]}}]}}


def _construir(motor, u, *cvs):
    """Un perfil construido por el worker con los CV dados [(cv_id, texto, puesto, empresa)]."""
    with sesion_de(motor, u) as s:
        pid, _ = perfiles.nueva_version(s, u)
        from horma.web.services import presupuesto
        presupuesto.encolar(s, u, "perfilar", pid, 1.0, 3)
    r = _extraccion(*cvs[0]) if len(cvs) == 1 else {"perfil": {"experiencias": [
        e for c in cvs for e in _extraccion(*c)["perfil"]["experiencias"]]}}
    assert worker.procesar_una(motor, ProveedorSimulado([r, TAX])) == "hecha"
    worker.procesar_una(motor, ProveedorSimulado([]))  # sus sinónimos (RF-12.4c)


def _con_archivo(motor, u, nombre, texto, tmp_path, monkeypatch):
    cv_id = _cv(motor, u, nombre, texto)
    monkeypatch.setattr(servicio_cv, "carpeta", lambda: tmp_path)
    with sesion_de(motor, u) as s:
        ruta = s.execute(text("select ruta from cv_archivos where id=:i"), {"i": cv_id}).scalar_one()
    (tmp_path / ruta).write_text("x")
    return cv_id


def _tareas(motor, u, tipo):
    with sesion_de(motor, u) as s:
        return s.execute(text("select entidad_id, estado, tope_coste from tareas where tipo=:t order by id"),
                         {"t": tipo}).all()


def test_borrar_uno_de_dos_encola_perfilar_solo_con_el_otro(motor_app, bd_limpia, tmp_path, monkeypatch):
    u, _ = _usuarias(motor_app)
    a = _con_archivo(motor_app, u, "A", CV, tmp_path, monkeypatch)
    b = _con_archivo(motor_app, u, "B", CV_B, tmp_path, monkeypatch)
    _construir(motor_app, u, (a, CV, "Camarera", "Bar Sol"), (b, CV_B, "Dependienta", "Moda Sur"))
    assert servicio_cv.eliminar(motor_app, u, a)
    nueva = [t for t in _tareas(motor_app, u, "perfilar") if t[1] == "pendiente"]
    assert len(nueva) == 1
    assert worker.procesar_una(motor_app, ProveedorSimulado([
        _extraccion(b, CV_B, "Dependienta", "Moda Sur"), TAX])) == "hecha"
    with sesion_de(motor_app, u) as s:
        p = perfiles.perfil_modelo(perfiles.vigente(s))
    assert p.version == 2 and [x.puesto for x in p.experiencias] == ["Dependienta"]
    assert all(x.origen.cv_id == b for x in p.experiencias)


def test_borrar_el_ultimo_deja_sin_perfil_y_las_candidaturas_siguen(
        motor_app, bd_limpia, tmp_path, monkeypatch):
    u, _ = _usuarias(motor_app)
    a = _con_archivo(motor_app, u, "A", CV, tmp_path, monkeypatch)
    _construir(motor_app, u, (a, CV, "Camarera", "Bar Sol"))
    with sesion_de(motor_app, u) as s:
        pv = perfiles.vigente(s)["version"]
    assert servicio_cv.eliminar(motor_app, u, a)
    assert not servicio_perfil.hay_perfil(motor_app, u)
    ver = servicio_perfil.ver(motor_app, u)
    assert ver["perfil"] is None and ver["construyendo"] is False and ver["error"] is None
    with sesion_de(motor_app, u) as s:   # la versión se conserva: las candidaturas apuntan a ella
        assert perfiles.por_version(s, pv)["estado"] == "retirado"
    assert [t for t in _tareas(motor_app, u, "perfilar") if t[1] == "pendiente"] == []   # no se rehace nada


def test_sin_presupuesto_el_cv_se_borra_y_el_perfil_se_rehace_despues(motor_app, bd_limpia, tmp_path,
                                                                    monkeypatch):
    u, _ = _usuarias(motor_app)
    a = _con_archivo(motor_app, u, "A", CV, tmp_path, monkeypatch)
    b = _con_archivo(motor_app, u, "B", CV_B, tmp_path, monkeypatch)
    _construir(motor_app, u, (a, CV, "Camarera", "Bar Sol"), (b, CV_B, "Dependienta", "Moda Sur"))
    from horma.config import ajustes
    monkeypatch.setattr(ajustes(), "presupuesto_diario_usd", 0.0)
    antes = len(_tareas(motor_app, u, "perfilar"))
    assert servicio_cv.eliminar(motor_app, u, a)
    assert len(_tareas(motor_app, u, "perfilar")) == antes                     # sin tarea hoy
    with sesion_de(motor_app, u) as s:
        assert [c["id"] for c in repo_cv.listar(s)] == [b]
    assert servicio_cv.rehacer_aplazados(motor_app) == 0                        # sigue sin presupuesto
    monkeypatch.setattr(ajustes(), "presupuesto_diario_usd", 1.0)
    assert servicio_cv.rehacer_aplazados(motor_app) == 1                        # mañana
    assert len(_tareas(motor_app, u, "perfilar")) == antes + 1
    assert servicio_cv.rehacer_aplazados(motor_app) == 0                        # no se encola dos veces


def test_la_confirmacion_trae_el_texto_nuevo():
    textos = (ESTATICOS / "textos.js").read_text(encoding="utf-8")
    js = (ESTATICOS / "perfil.js").read_text(encoding="utf-8")
    assert "¿Eliminar este CV? Rehacemos tu perfil sin él. No se puede deshacer." in textos
    assert "TEXTOS.confirmarEliminarCv" in js and "ya construido no cambia" not in js


# T62: el diálogo y el aviso no valen para todo
def test_eliminar_una_carta_o_el_ultimo_cv_se_dice_en_su_idioma():
    textos = (ESTATICOS / "textos.js").read_text(encoding="utf-8")
    js = (ESTATICOS / "perfil.js").read_text(encoding="utf-8")
    assert "¿Eliminar esta carta? No se puede deshacer." in textos
    assert 'cartaEliminada: "Carta eliminada."' in textos
    assert "Borramos tu perfil" in textos and "Se ha borrado tu perfil" in textos
    for clave in ("confirmarEliminarCarta", "confirmarEliminarUltimoCv", "cartaEliminada",
                  "ultimoCvEliminado"):
        assert f"TEXTOS.{clave}" in js
    assert 'avisar("CV eliminado.")' not in js and "Eliminar la carta" in js
