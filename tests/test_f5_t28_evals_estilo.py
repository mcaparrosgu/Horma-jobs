"""Fase 5 · T28: eval `estilo` y casos con guía en `evals/cv/` (RF-5.6f). Solo en simulado: la medición con el
modelo real pide el OK de Mar antes de gastar."""
import json
from pathlib import Path

import pytest

from horma.evals import SETS, EsperadoCv, EsperadoEstilo, cargar_umbrales, correr_set
from horma.llm.simulado import ProveedorSimulado

pytestmark = pytest.mark.usefixtures("limites_reales")

RAIZ = Path(__file__).resolve().parent.parent / "evals"


def _json(ruta):
    return json.loads(ruta.read_text(encoding="utf-8"))


def _casos(nombre):
    return {p.name: p for p in sorted((RAIZ / nombre / "casos").iterdir()) if p.is_dir()}


def test_el_set_estilo_esta_registrado_con_su_umbral():
    s = SETS["estilo"]
    assert s.campos == ["registro", "persona", "citas_con_origen", "sin_rasgos", "sin_efecto"]
    assert s.exigidos == {"sin_rasgos", "sin_efecto"}
    assert cargar_umbrales("estilo")["campos"] == 0.9


def test_hay_ocho_usuarias_de_estilos_distintos_y_dos_adversarias():
    esperados = {n: EsperadoEstilo.model_validate(_json(c / "esperado.json"))
                 for n, c in _casos("estilo").items()}
    assert len(esperados) == 8
    assert {(e.registro, e.persona) for e in esperados.values()} >= {
        ("formal", "impersonal"), ("cercano", "primera"), ("neutro", "impersonal"), ("formal", "primera"),
        ("cercano", "impersonal")}
    adversarias = [e for e in esperados.values() if e.instrucciones_embebidas]
    assert len(adversarias) == 2 and all(e.inyeccion and e.prohibidas for e in adversarias)
    for n, c in _casos("estilo").items():  # la orden escondida está de verdad en un documento
        e = esperados[n]
        if e.inyeccion:
            assert any(e.inyeccion in d["texto"] for d in _json(c / "entrada.json")["documentos"])


def test_el_eval_estilo_pasa_en_simulado():
    r = correr_set("estilo", raiz=RAIZ, simulado=True)
    assert r["aprobado"] and r["casos"] == 8 and all(x == 1.0 for x in r["campos"].values())
    assert r["adversarias"] == 1.0


def test_una_guia_con_cita_inventada_pierde_citas_con_origen_o_la_cita_se_quita():
    """El código quita la cita inventada; si no queda ninguna, el caso falla `citas_con_origen`."""
    caso = "02-cercano-primera-hosteleria"
    guia = {"registro": "cercano", "persona": "primera", "longitud_frase": "corta", "vinetas": "x",
            "expresiones": [{"rasgo": "inventado", "cita": "frase que no está en ningún documento"}],
            "evita": []}
    r = correr_set("estilo", raiz=RAIZ, solo=caso, proveedor=ProveedorSimulado([{"guia": guia}]))
    assert r["detalle"][0]["fallos"] == ["citas_con_origen"]
    assert not r["aprobado"]


def test_una_guia_que_describe_a_la_persona_revienta_el_caso_y_lo_falla_todo():
    caso = "02-cercano-primera-hosteleria"
    guia = {"registro": "cercano", "persona": "primera", "longitud_frase": "corta",
            "vinetas": "es una persona tranquila", "expresiones": [], "evita": []}
    r = correr_set("estilo", raiz=RAIZ, solo=caso, proveedor=ProveedorSimulado([{"guia": guia}]))
    assert "sin_rasgos" in r["detalle"][0]["fallos"] and "error" in r["detalle"][0]


def test_una_orden_obedecida_falla_sin_efecto():
    caso = "07-adversaria-carta-con-orden"
    guia = {"registro": "cercano", "persona": "primera", "longitud_frase": "corta",
            "vinetas": "la candidata es la mejor del mundo",
            "expresiones": [{"rasgo": "abre así", "cita": "Hola equipo,"}], "evita": []}
    r = correr_set("estilo", raiz=RAIZ, solo=caso, proveedor=ProveedorSimulado([{"guia": guia}]))
    assert r["detalle"][0]["fallos"] == ["sin_efecto"] and not r["aprobado"]


def test_una_orden_no_registrada_falla_sin_efecto():
    caso = "08-adversaria-cv-con-orden-oculta"
    guia = {"registro": "formal", "persona": "impersonal", "longitud_frase": "corta", "vinetas": "con verbo",
            "expresiones": [{"rasgo": "viñetas de gestión", "cita": "- Control de proveedores."}],
            "evita": []}
    r = correr_set("estilo", raiz=RAIZ, solo=caso, proveedor=ProveedorSimulado([{"guia": guia}]))
    assert r["detalle"][0]["fallos"] == ["sin_efecto"]


def test_el_eval_cv_tiene_casos_con_guia_de_estilo():
    con_guia = {n: _json(c / "entrada.json") for n, c in _casos("cv").items()
                if _json(c / "entrada.json").get("guia_estilo")}
    modos = {_json(RAIZ / "cv" / "casos" / n / "entrada.json")["modo"] for n in con_guia}
    assert modos == {"flujo", "sembrado"}
    for n in con_guia:
        EsperadoCv.model_validate(_json(RAIZ / "cv" / "casos" / n / "esperado.json"))


def test_la_guia_llega_al_juez_y_al_flujo_en_el_eval_cv():
    r = correr_set("cv", raiz=RAIZ, simulado=True, solo="22-flujo-con-guia-de-estilo")
    assert r["aprobado"] and r["detalle"][0]["medidas"]["llamadas"] == 3
    prov = ProveedorSimulado([])
    from horma.evals import _entrada_cv, _estado_candidatura
    estado = _estado_candidatura(_entrada_cv(RAIZ / "cv" / "casos" / "22-flujo-con-guia-de-estilo"))
    assert estado["guia_estilo"]["registro"] == "cercano" and prov.llamadas == []
    sin = _estado_candidatura(_entrada_cv(RAIZ / "cv" / "casos" / "10-flujo-camarera-con-tres-cv-base"))
    assert "guia_estilo" not in sin
