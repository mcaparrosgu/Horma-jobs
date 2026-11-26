"""Spec 012, T02: set `puestos` (RF-12.1 a 12.3) y sus métricas, con respuestas simuladas (0 USD)."""
import json
from pathlib import Path

from horma.evals import SETS, cargar_umbrales, casos_de, correr_set
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.perfil import Perfil

RAIZ = Path(__file__).resolve().parent.parent / "evals"


def _origen(texto):
    return {"fuente": "cv", "cv_id": 1, "fragmento": texto}


def _perfil(experiencias=("Camarera",), formacion=("Grado en Turismo",), habilidades=("Excel",)):
    return {"nombre": "Lucía Ferrer",
            "experiencias": [{"puesto": p, "origen": _origen(p)} for p in experiencias],
            "formacion": [{"titulo": t, "origen": _origen(t)} for t in formacion],
            "habilidades": [{"nombre": h, "origen": _origen(h)} for h in habilidades]}


def _caso(raiz, nombre, perfil, etiquetas, imprescindibles=(), variante=None):
    carpeta = raiz / "puestos" / "casos" / nombre
    carpeta.mkdir(parents=True)
    entrada = {"perfil": perfil, **({"variante": variante} if variante else {})}
    esperado = {"etiquetas": {t: {"final": e, "votos": [e, e, e]} for t, e in etiquetas.items()},
                "imprescindibles": [list(i) for i in imprescindibles]}
    (carpeta / "entrada.json").write_text(json.dumps(entrada), encoding="utf-8")
    (carpeta / "esperado.json").write_text(json.dumps(esperado), encoding="utf-8")


def _respuesta(*puestos):
    return {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior",
            "stack": [], "puestos": [{"titulo": t, "idioma": "es", "dato": d} for t, d in puestos]}


def _correr(tmp_path, *respuestas):
    return correr_set("puestos", raiz=tmp_path, proveedor=ProveedorSimulado(list(respuestas)))


def test_todo_bien_aprueba_y_mide_cada_metrica(tmp_path):
    _caso(tmp_path, "uno", _perfil(), {"Camarera": "lo_ha_sido", "Recepcionista": "afin"},
          imprescindibles=[("Camarera", "Waitress"), ("Ayudante de cocina",)])
    r = _correr(tmp_path, _respuesta(("Camarera", "Camarera"), ("Recepcionista", "Camarera")))
    m = r["metricas"]
    # Los dos salen de su puesto y llegan marcados: de dos, uno «lo ha sido».
    assert m["ajenos_marcados"] == 0 and m["precision_marcados"] == 0.5
    assert m["cobertura"] == 0.5  # falta «Ayudante de cocina»
    assert m["precision_sin_marcar"] is None and m["equidad"] is None and m["kappa"] == 1.0
    assert m["sin_etiquetar"] == []
    assert not r["aprobado"]


def test_un_ajeno_marcado_hace_fallar_el_set(tmp_path):
    _caso(tmp_path, "uno", _perfil(), {"Camarera": "lo_ha_sido", "Controller financiero": "ajeno"})
    r = _correr(tmp_path, _respuesta(("Camarera", "Camarera"), ("Controller financiero", "Camarera")))
    assert r["metricas"]["ajenos_marcados"] == 1 and not r["aprobado"]
    assert "ajenos" in r["detalle"][0]["fallos"]


def test_solo_lo_ha_sido_marcado_aprueba(tmp_path):
    _caso(tmp_path, "uno", _perfil(), {"Camarera": "lo_ha_sido"}, imprescindibles=[("Camarero",)])
    r = _correr(tmp_path, _respuesta(("Camarera", "Camarera")))
    assert r["metricas"]["precision_marcados"] == 1.0 and r["metricas"]["cobertura"] == 1.0
    assert r["aprobado"]


def test_sin_experiencia_un_marcado_afin_acierta_d036(tmp_path):
    _caso(tmp_path, "junior", _perfil(experiencias=()), {"Guía turístico": "afin"})
    r = _correr(tmp_path, _respuesta(("Guía turístico", "Grado en Turismo")))
    assert r["metricas"]["precision_marcados"] == 1.0 and r["aprobado"]


def test_un_puesto_sin_etiquetar_no_aprueba(tmp_path):
    _caso(tmp_path, "uno", _perfil(), {})
    r = _correr(tmp_path, _respuesta(("Camarera", "Camarera")))
    assert r["metricas"]["sin_etiquetar"] == ["uno: Camarero/a"] and not r["aprobado"]


def test_equidad_dos_gemelas_dan_la_misma_copia_sin_llamar_dos_veces(tmp_path):
    variante = {"nombre": "Lucas Ferrer", "genero_puestos": "masculino",
                "reemplazos": {"Camarera": "Camarero"}}
    _caso(tmp_path, "uno", _perfil(), {"Camarera": "lo_ha_sido"}, variante=variante)
    prov = ProveedorSimulado([_respuesta(("Camarera", "Camarera"))])
    r = correr_set("puestos", raiz=tmp_path, proveedor=prov)
    assert r["metricas"]["equidad"] == 1.0 and r["aprobado"] and len(prov.llamadas) == 1
    assert "Ferrer" not in prov.llamadas[0]["usuario"]


def test_una_gemela_con_una_palabra_fuera_del_lexico_hace_fallar_la_equidad(tmp_path):
    variante = {"nombre": "Lucas Ferrer", "genero_puestos": "masculino",
                "reemplazos": {"Costurera": "Costurero"}}
    _caso(tmp_path, "uno", _perfil(experiencias=("Costurera",)), {"Costurera": "lo_ha_sido"},
          variante=variante)
    r = _correr(tmp_path, _respuesta(("Costurera", "Costurera")))
    assert r["metricas"]["equidad"] == 0.0 and not r["aprobado"]
    assert "equidad" in r["detalle"][0]["fallos"]


def test_tres_pasadas_distintas_bajan_la_estabilidad_sin_suspender(tmp_path):
    _caso(tmp_path, "uno", _perfil(), {"Camarera": "lo_ha_sido", "Barman": "lo_ha_sido"})
    prov = ProveedorSimulado([_respuesta(("Camarera", "Camarera"), ("Barman", "Camarera")),
                              _respuesta(("Camarera", "Camarera")),
                              _respuesta(("Camarera", "Camarera"))])
    r = correr_set("puestos", raiz=tmp_path, proveedor=prov, veces=3)
    assert r["metricas"]["estabilidad"] == 0.5 and r["aprobado"]
    repetido = correr_set("puestos", raiz=tmp_path, grabadas=True, veces=3)
    assert repetido["metricas"]["estabilidad"] == 0.5 and repetido["coste"] == 0


def test_un_ajeno_marcado_en_cualquier_pasada_cuenta(tmp_path):
    _caso(tmp_path, "uno", _perfil(), {"Camarera": "lo_ha_sido", "Barman": "ajeno"})
    prov = ProveedorSimulado([_respuesta(("Camarera", "Camarera")),
                              _respuesta(("Camarera", "Camarera"), ("Barman", "Camarera"))])
    r = correr_set("puestos", raiz=tmp_path, proveedor=prov, veces=2)
    assert r["metricas"]["ajenos_marcados"] == 1


def test_las_respuestas_reales_se_guardan_y_se_repiten_sin_llamar_al_modelo(tmp_path):
    _caso(tmp_path, "uno", _perfil(), {"Camarera": "lo_ha_sido"})
    _correr(tmp_path, _respuesta(("Camarera", "Camarera")))
    assert (tmp_path / "puestos" / "respuestas" / "uno.json").exists()
    r = correr_set("puestos", raiz=tmp_path, grabadas=True)
    assert r["aprobado"] and r["coste"] == 0 and r["metricas"]["precision_marcados"] == 1.0


def test_los_umbrales_son_los_de_rf_12_3():
    assert cargar_umbrales("puestos")["metricas"] == {
        "ajenos_marcados": 0, "precision_marcados": 0.95, "precision_sin_marcar": 0.85,
        "cobertura": 0.8, "equidad": 1.0}  # la estabilidad solo se informa (D-052)


def test_el_set_tiene_30_cv_los_18_de_perfil_y_12_dificiles_con_10_parejas():
    casos = casos_de(RAIZ, "puestos")
    assert len(casos) == 30
    assert {c.name for c in casos_de(RAIZ, "perfil")} <= {c.name for c in casos}
    parejas = 0
    for c in casos:
        entrada = SETS["puestos"].entrada(c)
        p = Perfil.model_validate(entrada["perfil"])
        assert p.taxonomia is None and not p.instrucciones_embebidas, c.name  # como llega al clasificador
        parejas += "variante" in entrada
        SETS["puestos"].esperado.model_validate_json((c / "esperado.json").read_text(encoding="utf-8"))
    assert parejas == 10
