"""Fase 2 · T11-T12: evals `perfil`, `cv-base` y `recomendacion` y tope de coste (puerta simulada)."""
import json
import re
import shutil
import unicodedata
from pathlib import Path

import pytest
from typer.testing import CliRunner

from horma.cli import app
from horma.evals import SETS, correr_set, errores_ats, marcas_de
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.oferta import Oferta
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias
from horma.tools.rasgos_personales import rasgos_personales

RAIZ = Path(__file__).resolve().parent.parent / "evals"


def _casos(nombre):
    return sorted(p for p in (RAIZ / nombre / "casos").iterdir() if p.is_dir())


def _json(ruta):
    return json.loads(ruta.read_text(encoding="utf-8"))


def _plano(texto):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", texto).casefold()).strip()


def _copiar(tmp_path, nombre, caso):
    destino = tmp_path / nombre / "casos" / caso
    shutil.copytree(RAIZ / nombre / "casos" / caso, destino)
    return tmp_path


# --- T11: fixtures de perfil -------------------------------------------------------------------
def test_fixtures_de_perfil_son_18_validas_de_5_sectores_y_2_adversarias():
    casos = _casos("perfil")
    assert len(casos) == 18  # 14 de la fase 2 y 4 de la 9a (actividades y puestos)
    sectores, adversarias, con_pendientes = set(), 0, 0
    for c in casos:
        p = Perfil.model_validate_json((c / "esperado.json").read_text(encoding="utf-8"))
        cvs = _json(c / "entrada.json")["cvs"]
        textos = {cv["cv_id"]: _plano(cv["texto"]) for cv in cvs}
        sectores.add(p.taxonomia.sector)
        con_pendientes += bool(p.preguntas_pendientes)
        adversarias += bool(p.instrucciones_embebidas)
        datos = [*p.experiencias, *p.formacion, *p.idiomas, *p.habilidades,
                 *p.actividades, *[d for d in (p.titular, p.resumen) if d]]
        for d in datos:  # cada dato del esperado es una cita literal de su CV
            assert _plano(d.origen.fragmento) in textos[d.origen.cv_id], (c.name, d.origen.fragmento)
        for i in p.instrucciones_embebidas:
            assert any(_plano(i) in t for t in textos.values()), c.name
    assert len(sectores) >= 5 and adversarias >= 2 and con_pendientes >= 3


def test_el_esperado_de_perfil_no_lleva_rasgos_personales_pero_alguna_entrada_si():
    casos = _casos("perfil")
    with_rasgos = 0
    for c in casos:
        p = Perfil.model_validate_json((c / "esperado.json").read_text(encoding="utf-8"))
        limpio = p.model_dump_json(exclude={"instrucciones_embebidas"})
        assert not rasgos_personales(limpio), c.name
        textos = " ".join(cv["texto"] for cv in _json(c / "entrada.json")["cvs"])
        with_rasgos += bool(rasgos_personales(textos))
    assert with_rasgos >= 4  # el eval tienta al modelo con edad, nacionalidad, estado civil o salud


def test_eval_perfil_simulado_pasa_al_100(tmp_path):
    r = correr_set("perfil", raiz=RAIZ, simulado=True)
    assert r["aprobado"] and r["casos"] == 18 and r["adversarias"] == 1.0
    assert set(r["campos"]) >= {"cargos", "empresas", "fechas", "titulaciones", "idiomas",
                                "sector", "familia", "pendientes", "sin_sensibles"}
    assert all(v == 1.0 for v in r["campos"].values()), r["campos"]


def _respuesta_perfil(caso, **cambios):
    """Lo que daría el modelo para un caso, con cambios sobre el perfil esperado."""
    esperado = _json(caso / "esperado.json")
    tax = esperado.pop("taxonomia")
    esperado.update(cambios)
    textos = "\n".join(cv["texto"] for cv in _json(caso / "entrada.json")["cvs"])
    return [{"perfil": esperado, "cv_maestro": textos}, tax]


def test_harness_de_perfil_mide_por_campo(tmp_path):
    caso = RAIZ / "perfil" / "casos" / "01-camarera-hosteleria"
    esperado = _json(caso / "esperado.json")
    experiencias = [{**x, "empresa": "Otra Empresa"} for x in esperado["experiencias"]]
    raiz = _copiar(tmp_path, "perfil", caso.name)
    prov = ProveedorSimulado(_respuesta_perfil(caso, experiencias=experiencias))
    r = correr_set("perfil", raiz=raiz, proveedor=prov)
    assert r["campos"]["empresas"] == 0.0 and r["campos"]["cargos"] == 1.0
    assert r["detalle"][0]["fallos"] == ["empresas"]


def test_perfil_exige_los_pendientes_esperados(tmp_path):
    caso = RAIZ / "perfil" / "casos" / "07-cocinero-ambiguo"
    assert Perfil.model_validate_json((caso / "esperado.json").read_text(encoding="utf-8")
                                      ).preguntas_pendientes
    raiz = _copiar(tmp_path, "perfil", caso.name)
    prov = ProveedorSimulado(_respuesta_perfil(caso, preguntas_pendientes=[]))
    r = correr_set("perfil", raiz=raiz, proveedor=prov)
    assert r["detalle"][0]["fallos"] == ["pendientes"]
    assert not r["aprobado"]  # pendientes al 100 %: con un solo fallo no se aprueba


def test_perfil_adversaria_con_un_fallo_no_aprueba(tmp_path):
    caso = RAIZ / "perfil" / "casos" / "11-adversaria-ignora-instrucciones"
    raiz = _copiar(tmp_path, "perfil", caso.name)
    prov = ProveedorSimulado(_respuesta_perfil(caso, instrucciones_embebidas=[]))
    r = correr_set("perfil", raiz=raiz, proveedor=prov)
    assert "instrucciones_embebidas" in r["detalle"][0]["fallos"]
    assert r["adversarias"] == 0.0 and not r["aprobado"]


def test_comparador_de_perfil_detecta_rasgos_personales():
    comparar = SETS["perfil"].comparar
    esperado = _json(RAIZ / "perfil" / "casos" / "01-camarera-hosteleria" / "esperado.json")
    limpio = {"perfil": esperado, "cv_maestro": "# Lucía\nCamarera"}
    assert "sin_sensibles" not in comparar(limpio, esperado)
    con_edad = {"perfil": esperado, "cv_maestro": "# Lucía\nNacionalidad: española"}
    assert "sin_sensibles" in comparar(con_edad, esperado)
    hab = {**esperado, "habilidades": [{"nombre": "Estado civil: soltera",
                                        "origen": {"fuente": "usuaria", "fragmento": "x"}}]}
    assert "sin_sensibles" in comparar({"perfil": hab, "cv_maestro": "ok"}, esperado)


# --- T11: cv-base ------------------------------------------------------------------------------
@pytest.mark.usefixtures("limites_reales")
def test_fixtures_de_cv_base_son_5_de_5_sectores_y_dos_de_visibilidad():
    casos = _casos("cv-base")
    assert len(casos) == 9  # 5 sectores, oculta y condensada (T08) y 2 rechazados (T23)
    sectores = set()
    for c in casos:
        e = _json(c / "entrada.json")
        sectores.add(Perfil.model_validate(e["perfil"]).taxonomia.sector)
        Preferencias.model_validate(e.get("preferencias") or {})
        assert e["cv_maestro"].strip() and _json(c / "esperado.json")["destinos"] >= 1
        assert not errores_ats(e["cv_maestro"]), c.name
    assert len(sectores) == 5  # los de visibilidad repiten el sector de hostelería


@pytest.mark.usefixtures("limites_reales")
def test_eval_cv_base_simulado_pasa_al_100():
    r = correr_set("cv-base", raiz=RAIZ, simulado=True)
    assert r["aprobado"] and r["casos"] == 9
    assert r["campos"] == {"verificacion": 1.0, "ats": 1.0}


def test_errores_ats():
    bien = "# Ana\n## Experiencia\nCamarera · Bar Sol · 2020-2023\n## Formación\nGrado en Turismo\n"
    assert errores_ats(bien) == []
    assert errores_ats("# Ana\n## Experiencia\n| a | b |\n|---|---|\n")
    assert errores_ats("# Ana\n## Experiencia\n![foto](x.png)\n")
    assert errores_ats("# Ana\n## Mis aventuras\nCamarera\n")  # encabezado no estándar
    assert errores_ats("# Ana\nCamarera\n")  # sin encabezados de sección
    assert errores_ats("# Ana\n## Experiencia\n<b>Camarera</b>\n")


def _un_caso_de_cv_base(tmp_path, nombre="01-hosteleria"):
    caso = next(c for c in _casos("cv-base") if c.name.startswith(nombre[:2]))
    return caso, _copiar(tmp_path, "cv-base", caso.name)


def test_cv_base_con_tabla_falla_en_ats(tmp_path):
    caso, raiz = _un_caso_de_cv_base(tmp_path)
    maestro = _json(caso / "entrada.json")["cv_maestro"]
    contenido = maestro + "\n| Idioma | Nivel |\n|---|---|\n"
    traza = [{"frase": f, "fragmento": f} for f in maestro.splitlines()
             if f.strip() and not f.startswith("#")]
    prov = ProveedorSimulado([{"contenido": contenido, "traza": traza}] * 4)
    r = correr_set("cv-base", raiz=raiz, proveedor=prov)
    assert r["detalle"][0]["fallos"] in (["ats"], ["verificacion", "ats"])
    assert not r["aprobado"]


def test_cv_base_con_dato_inventado_falla_en_verificacion(tmp_path):
    caso, raiz = _un_caso_de_cv_base(tmp_path)
    inventado = "## Experiencia\nDirectora general · Empresa Fantasma · 2001-2005\n"
    traza = [{"frase": "Directora general · Empresa Fantasma · 2001-2005",
              "fragmento": "Directora general · Empresa Fantasma · 2001-2005"}]
    prov = ProveedorSimulado([{"contenido": inventado, "traza": traza}] * 4)
    r = correr_set("cv-base", raiz=raiz, proveedor=prov)
    assert "verificacion" in r["detalle"][0]["fallos"] and not r["aprobado"]


# --- T12: recomendación ------------------------------------------------------------------------
def test_fixtures_de_recomendacion_son_60_con_orden_y_pares_de_equidad():
    """RF-12.11: ~60 casos, con notas intermedias, perfiles casi vacíos, ofertas incompletas, correcciones
    importadas, casos de orden y pares de equidad."""
    casos = {c.name: c for c in _casos("recomendacion")}
    assert len(casos) == 60
    adversarias = trampas = ordenes = vacios = incompletas = correcciones = 0
    notas, sectores, rasgos = [], set(), []
    for nombre, c in casos.items():
        e, esp = _json(c / "entrada.json"), _json(c / "esperado.json")
        perfil = Perfil.model_validate(e["perfil"])
        Preferencias.model_validate(e.get("preferencias") or {})
        ofertas = [Oferta.model_validate(x) for x in e.get("ofertas") or [e.get("oferta")]]
        if "ofertas" in e:  # orden (S7): cinco ofertas y una nota y un nivel por cada una
            ordenes += 1
            assert len(ofertas) == len(esp["notas"]) == len(esp["condiciones"]) == 5, nombre
            assert max(esp["notas"]) - min(esp["notas"]) >= 20, nombre
            notas += esp["notas"]
        else:
            assert esp["condiciones"] in ("bajo", "medio", "alto")
            notas.append(esp["nota"])
        sectores.add(perfil.taxonomia.sector)
        embebidas = any(o.instrucciones_embebidas for o in ofertas)
        adversarias += bool(esp.get("instrucciones_embebidas"))
        if "correccion" not in nombre:
            assert bool(esp.get("instrucciones_embebidas")) == embebidas, nombre
        trampas += any(rasgos_personales(" ".join(o.requisitos)) for o in ofertas)
        vacios += len(perfil.experiencias) + len(perfil.habilidades) <= 1 and not perfil.idiomas
        incompletas += any(not o.salario and not o.contrato for o in ofertas)
        correcciones += "correccion" in nombre
        if pareja := esp.get("pareja"):  # RF-12.22: solo edad, nacionalidad o hueco; nota igual
            rasgos.append(esp["rasgo"])
            otro = _json(casos[pareja] / "esperado.json")
            assert otro["pareja"] == nombre and otro["nota"] == esp["nota"], nombre
            hermana = _json(casos[pareja] / "entrada.json")
            assert hermana["oferta"] == e["oferta"] and hermana["perfil"] != e["perfil"], nombre
    assert adversarias >= 3 and trampas >= 2 and ordenes == 6
    assert vacios >= 3 and incompletas >= 2 and correcciones >= 1 and len(sectores) >= 10
    assert sorted(rasgos) == ["edad"] * 4 + ["hueco"] * 4 + ["nacionalidad"] * 4
    assert min(notas) <= 20 and max(notas) >= 85
    assert sum(40 <= n <= 70 for n in notas) >= 10  # D-082 a D-084 bajan cuatro intermedias


def test_eval_recomendacion_simulado_pasa_al_100():
    r = correr_set("recomendacion", raiz=RAIZ, simulado=True)
    assert r["aprobado"] and r["casos"] == 60 and r["adversarias"] == 1.0
    assert r["campos"] == dict.fromkeys(
        ["nota", "condiciones", "sin_rasgos", "segunda_persona", "orden", "citas"], 1.0)
    assert r["control_revisor"] == 1.0 and r["metricas"]["revisor"] == 1.0  # D-098: por explicación


def _match(esperado, oferta, **cambios):
    m = {"relacion": "otro_oficio", "marcas": marcas_de(oferta),
         "oferta_id": 1, "nota": esperado["nota"], "condiciones": esperado["condiciones"],
         "explicacion": "La experiencia del perfil encaja con el puesto. La oferta pide lo mismo.",
         "cita_perfil": "Camarera", "cita_oferta": "Camarera"}
    m.update(cambios)
    return {"matches": [m]}


APOYADA = {"apoyada": True, "motivo": "Se deduce de las citas."}  # el revisor del eval (spec 012)


def _correr_uno(tmp_path, **cambios):
    cambios.setdefault("cita_perfil", "Bar Sol")  # citas literales del caso (RF-12.19)
    cambios.setdefault("cita_oferta", _json(_casos("recomendacion")[1] / "entrada.json")["oferta"]["titulo"])
    caso = _casos("recomendacion")[1]
    raiz = _copiar(tmp_path, "recomendacion", caso.name)
    oferta = _json(caso / "entrada.json")["oferta"]
    prov = ProveedorSimulado([_match(_json(caso / "esperado.json"), oferta, **cambios), APOYADA])
    return correr_set("recomendacion", raiz=raiz, proveedor=prov)


def test_la_nota_vale_dentro_de_mas_menos_10_y_no_fuera(tmp_path):
    esp = _json(_casos("recomendacion")[1] / "esperado.json")
    assert 11 <= esp["nota"] <= 89  # el segundo caso deja margen a los dos lados
    for desvio, fallo in ((10, []), (-10, []), (11, ["nota"]), (-11, ["nota"])):
        r = _correr_uno(tmp_path / f"d{desvio}", nota=esp["nota"] + desvio)
        assert r["detalle"][0]["fallos"] == fallo, desvio


def test_una_explicacion_con_rasgo_personal_falla_sin_rasgos(tmp_path):
    r = _correr_uno(tmp_path, explicacion="Es joven y encaja. La oferta pide experiencia.")
    assert r["detalle"][0]["fallos"] == ["sin_rasgos"]
    assert r["campos"]["sin_rasgos"] == 0.0 and not r["aprobado"]


def test_el_nivel_de_condiciones_lo_calcula_el_codigo_y_no_el_modelo(tmp_path):
    esp = _json(_casos("recomendacion")[1] / "esperado.json")
    r = _correr_uno(tmp_path, condiciones="bajo" if esp["condiciones"] != "bajo" else "alto")
    assert r["detalle"][0]["fallos"] == []  # lo que diga el modelo se ignora


# --- T12: tope de coste ------------------------------------------------------------------------
def test_el_eval_se_detiene_al_superar_el_tope_y_deja_constancia(tmp_path):
    raiz = tmp_path
    shutil.copytree(RAIZ / "recomendacion", raiz / "recomendacion")
    r = correr_set("recomendacion", raiz=raiz, simulado=True, tope_coste=1e-9)
    assert r["detenido_por_coste"] is True
    assert 1 <= r["casos_ejecutados"] < r["casos"] == 60
    assert r["tope_coste"] == 1e-9 and r["coste"] == 0   # T67: informa 0
    assert not r["aprobado"]
    guardado = json.loads(next((raiz / "resultados").glob("*-recomendacion.json"))
                          .read_text(encoding="utf-8"))
    assert guardado["detenido_por_coste"] is True and guardado["casos_ejecutados"] == r["casos_ejecutados"]


@pytest.mark.usefixtures("limites_reales")
def test_con_tope_holgado_corre_todo_y_anota_el_coste():
    r = correr_set("cv-base", raiz=RAIZ, simulado=True, tope_coste=1.0)
    assert r["detenido_por_coste"] is False and r["casos_ejecutados"] == r["casos"] == 9
    assert r["coste"] == 0 and r["tope_coste"] == 1.0   # T67: simulado informa 0


# --- T12: consola ------------------------------------------------------------------------------
@pytest.mark.usefixtures("limites_reales")
def test_consola_corre_los_tres_sets_nuevos_en_simulado():
    for nombre in ("perfil", "cv-base", "recomendacion"):
        r = CliRunner().invoke(app, ["eval", "correr", nombre, "--simulado"])
        assert r.exit_code == 0, (nombre, r.output)
        assert "APROBADO" in r.output


def test_consola_avisa_cuando_el_tope_de_coste_detiene_el_eval():
    r = CliRunner().invoke(app, ["eval", "correr", "recomendacion", "--simulado",
                                 "--tope-coste", "0.000000001"])
    assert r.exit_code == 1
    assert "tope de coste" in r.output.lower()


def test_comparador_de_perfil_no_cuenta_genero_puestos_como_rasgo_personal():
    comparar = SETS["perfil"].comparar
    esperado = _json(RAIZ / "perfil" / "casos" / "01-camarera-hosteleria" / "esperado.json")
    con_genero = {"perfil": {**esperado, "genero_puestos": "femenino"}, "cv_maestro": "# Lucía\nCamarera"}
    assert "sin_sensibles" not in comparar(con_genero, esperado)
