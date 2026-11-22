"""Fase 7 · ajustes de pantalla (spec 007)."""
import importlib
from pathlib import Path

import pytest
from sqlalchemy import text

from horma.schemas.oferta import OfertaExtraida

RAIZ = Path(__file__).resolve().parent.parent
ESTATICOS = RAIZ / "horma" / "web" / "static"


def leer(nombre: str) -> str:
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


# --- T02 · modalidad -------------------------------------------------------------------------------
def test_remoto_se_deriva_de_la_modalidad():
    assert OfertaExtraida(titulo="x", modalidad="remoto").remoto is True
    assert OfertaExtraida(titulo="x", modalidad="hibrido", remoto=True).remoto is False
    assert OfertaExtraida(titulo="x", modalidad="presencial").remoto is False
    assert OfertaExtraida(titulo="x").remoto is None
    assert OfertaExtraida(titulo="x", remoto=True).remoto is True  # sin modalidad se respeta


def test_modalidad_invalida_se_rechaza():
    with pytest.raises(ValueError):
        OfertaExtraida(titulo="x", modalidad="semi")


@pytest.mark.bd
def test_la_migracion_crea_la_columna_con_su_check(motor_migrador):
    with motor_migrador.begin() as c:
        tipo = c.execute(text("select data_type from information_schema.columns "
                              "where table_name='ofertas' and column_name='modalidad'")).scalar()
        assert tipo == "text"
        c.execute(text("insert into ofertas (texto_crudo, huella) values ('a','h1')"))
        with pytest.raises(Exception, match="modalidad"):
            with c.begin_nested():
                c.execute(text("update ofertas set modalidad='semi' where huella='h1'"))
        c.execute(text("update ofertas set modalidad='hibrido' where huella='h1'"))


def test_la_migracion_0019_encadena_con_la_0018():
    m = importlib.import_module("horma.web.migrations.versions.0019_fase7_modalidad")
    assert (m.revision, m.down_revision) == ("0019", "0018")


# --- T03 · extractor y origen --------------------------------------------------------------------
def test_el_prompt_del_extractor_define_la_modalidad():
    prompt = (RAIZ / "horma/agents/extractor_oferta/prompt.md").read_text(encoding="utf-8")
    assert "`modalidad`" in prompt and "hibrido" in prompt and "un día al mes" in prompt
    assert "residencia" in prompt


def test_origen_conserva_la_modalidad_si_esta_en_el_texto():
    from horma.tools.origen_oferta import con_origen
    texto = "Analista\nRemoto, con un día al mes en la oficina de Sevilla."
    o, origenes = con_origen(texto, OfertaExtraida(titulo="Analista", modalidad="hibrido"))
    assert o.modalidad == "hibrido" and o.remoto is False
    assert any(campo == "modalidad" for campo, _ in origenes)
    o2, _ = con_origen("Analista\nSin más datos.", OfertaExtraida(titulo="Analista", modalidad="remoto"))
    assert o2.modalidad is None  # no localizable en el texto: se descarta


def test_los_casos_nuevos_de_evals_de_ofertas_existen():
    casos = sorted(p.name for p in (RAIZ / "evals/ofertas/casos").iterdir())
    assert len(casos) == 29
    import json
    mods = {json.loads((RAIZ / "evals/ofertas/casos" / c / "esperado.json")
                       .read_text(encoding="utf-8")).get("modalidad") for c in casos[25:]}
    assert mods == {"hibrido", "remoto", "presencial", None}


# --- T04 · pantalla de modalidad -------------------------------------------------------------------
def test_la_casilla_solo_remoto_explica_que_es_estricto():
    frase = "Solo ofertas 100 % en remoto. Si piden ir a la oficina alguna vez, no salen."
    assert frase in leer("ofertas.html")


def test_donde_se_enseñaba_remoto_se_enseña_la_modalidad():
    assert "nombreModalidad(o.modalidad)" in leer("ofertas.js")
    assert "o.remoto" not in leer("ofertas.js") and "o.remoto" not in leer("catalogo.js")
    assert "Híbrido" in leer("comun.js") and "Presencial" in leer("comun.js")


# --- T05 · ofertas propias sin fecha ---------------------------------------------------------------
def _flujo(propia: bool):
    from horma.flows.procesar_oferta import crear
    from horma.llm.simulado import ProveedorSimulado
    from horma.schemas.oferta import Oferta
    texto = "Camarera de sala en Hotel Mar. Contrato indefinido."
    extraida = {"titulo": "Camarera de sala", "empresa": "Hotel Mar"}
    tax = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion",
           "nivel": "sin_especificar", "stack": []}
    flujo = crear(proveedor=ProveedorSimulado([extraida, {"generica": False, "fraude": False}, tax]),
                  resolver=None)
    return Oferta.model_validate(flujo.run({"texto": texto, "propia": propia})["oferta"])


def test_una_propia_sin_fecha_no_es_fantasma_por_sin_fecha():
    o = _flujo(True)
    assert "sin_fecha" not in o.auditoria.motivos_fantasma and not o.auditoria.fantasma


def test_una_de_catalogo_sin_fecha_sigue_siendo_fantasma():
    o = _flujo(False)
    assert "sin_fecha" in o.auditoria.motivos_fantasma and o.auditoria.fantasma


def test_para_procesar_pasa_propia():
    assert "o.usuaria_id is not null as propia" in (
        RAIZ / "horma/web/repositories/ofertas.py").read_text(encoding="utf-8")


def test_la_pantalla_no_enseña_la_fecha_de_alta_de_una_propia_como_publicada():
    js = leer("ofertas.js")
    assert "No consta fecha de publicación" in js
    assert "o.propia && !o.fecha_publicacion" in js


# --- T07 · nombres enteros -------------------------------------------------------------------------
def test_nombres_de_pais_e_idioma_solo_viven_en_comun_js():
    import re
    assert "function nombrePais" in leer("comun.js") and "function nombreIdioma" in leer("comun.js")
    for f in ESTATICOS.glob("*.js"):
        if f.name not in ("comun.js", "sw.js"):
            texto = f.read_text(encoding="utf-8")
            assert not re.search(r"function nombre(Pais|Idioma)|Intl\.DisplayNames", texto), f.name
    assert "Remoto (cualquier país)" in leer("comun.js")
    assert "nombreOpcion(clave, o.valor)" in leer("comun.js")
    assert "nombreIdioma(d.idioma)" in leer("perfil.js")


# --- T06 · segunda persona -------------------------------------------------------------------------
def test_el_prompt_del_matcher_pide_segunda_persona():
    prompt = (RAIZ / "horma/agents/matcher/prompt.md").read_text(encoding="utf-8")
    assert "segunda persona" in prompt and "tienes experiencia" in prompt


def test_el_comprobador_suspende_el_nombre_y_la_tercera_persona_y_aprueba_la_segunda():
    from horma.evals import habla_de_tu
    assert not habla_de_tu("Lucía tiene experiencia en sala.", "Lucía Ferrer")
    assert not habla_de_tu("Ferrer encaja con el puesto.", "Lucía Ferrer")
    assert not habla_de_tu("La candidata tiene experiencia en sala.", "Lucía Ferrer")
    assert habla_de_tu("Tienes experiencia en sala y la oferta tiene turnos.", "Lucía Ferrer")


def test_el_set_recomendacion_mide_la_segunda_persona():
    from horma.evals import SETS, _comparar_recomendacion
    assert "segunda_persona" in SETS["recomendacion"].campos
    base = {"nota": 80, "condiciones": "medio", "explicacion": "Lucía tiene experiencia.",
            "_nombre_perfil": "Lucía Ferrer"}
    assert _comparar_recomendacion(base, {"nota": 80, "condiciones": "medio"}) == ["segunda_persona"]


# --- T08-T09 · Perfil ------------------------------------------------------------------------------
def test_perfil_en_el_orden_de_p3_con_el_texto_de_p4():
    html = leer("perfil.html")
    orden = [html.index(x) for x in ('id="t-perfil"', 'id="pendientes"', 'id="estilo"')]
    assert orden == sorted(orden)
    assert 'id="pendientes" class="panel-desplegado"' in html and "<details id=\"estilo\"" in html
    assert 'id="estilo" class="panel-desplegado" hidden>' in html
    assert "open" not in html.split('id="estilo"')[1][:60]
    assert 'data-explicacion="perfil"' in html   # el texto vive en la ayuda «?» (RF-10.14m)
    assert 'id="n-pendientes"' in html


def test_perfil_pendientes_abierto_solo_si_hay():
    js = leer("perfil.js")
    # RF-9.5 (spec 009): el número suma preguntas y avisos
    assert '$("n-pendientes").textContent = String(total)' in js and "preguntas.length + items.length" in js
    assert '$("pendientes").open = true' in js and '$("pendientes").open = false' in js


def test_estilo_es_un_parrafo_corto_sin_ver_detalle():
    """Fase 7 · T18 (RF-7.5c): frase de tono, «Usas: …» y «Evitas: …» con 5 como máximo, sin detalle."""
    js = leer("perfil.js")
    assert "function resumirEstilo" in js and "MAX_RASGOS = 5" in js
    assert "rasgos.slice(0, MAX_RASGOS)" in js and '"ul"' in js   # S8 (RF-10.14l): una viñeta por rasgo
    assert '"Usas"' in js and '"Evitas"' in js and "TEXTOS.evitasVacio" in js
    assert "Ver detalle" not in js and "function rasgos(" not in js
    assert "Editar guía" in leer("perfil.html") and "Volver a analizar mi estilo" in leer("perfil.html")


def test_secciones_de_perfil_son_desplegables_cerrados_con_su_numero():
    """Fase 7 · T19 (RF-7.5d); la 009 añade «Otras actividades» (RF-9.1d) y, a petición de Mar (21-nov),
    habilidades, certificaciones, otros y la lista de CV subidos."""
    js = leer("perfil.js")
    assert ('const PLEGABLES = ["experiencias", "formacion", "idiomas", "habilidades", "proyectos", '
            '"certificaciones",\n'
            '                   "actividades", "otros"]') in js
    assert 'id="cvs-subidos"' in leer("perfil.html") and 'id="n-cvs"' in leer("perfil.html")
    assert 'nodo(plegable ? "details" : "section"' in js
    assert 'nodo("span", String(hijos.length), "estado")' in js
    assert "s.open = abiertas.has(clave)" in js   # cerrados salvo que ella los abriera
    assert 'addEventListener("toggle"' in js
    assert "abiertas.add(clave)" in js and "abiertas.delete(clave)" in js


# --- T10 · Ingesta ---------------------------------------------------------------------------------
def test_ingesta_con_buscador_y_cinco_opciones():
    html = leer("ingesta.html")
    assert 'id="buscar-fuente"' in html and 'id="sin-fuentes"' in html and "Ninguna fuente coincide" in html
    opciones = [o for o in ("Todas", "Activas", "Inactivas", "No aptas", "Sin calificar")
                if f">{o}</option>" in html]
    assert len(opciones) == 5
    js = leer("ingesta.js")
    assert 'normalize("NFD")' in js and "pintarFuentes" in js


# --- T11 · Admin -----------------------------------------------------------------------------------
def test_admin_no_esta_fijo_en_las_pestanas_y_se_pinta_solo_para_admin():
    js = leer("comun.js")
    pestanas = js[js.index("const PESTANAS"):js.index("];", js.index("const PESTANAS"))]
    assert "Admin" not in pestanas and "Ingesta" not in pestanas and "Costes" not in pestanas
    assert "if (yo.admin)" in js and '"Admin"' in js
    assert js.index('"Admin"') > js.index("for (const [etiqueta, ruta] of PESTANAS)")


def test_ingesta_y_costes_llevan_subpestañas_y_no_se_ven_sin_admin():
    for nombre, activa in (("ingesta.html", "/ingesta"), ("costes.html", "/costes")):
        html = leer(nombre)
        assert 'class="subpestanas"' in html and ">Ingesta</a>" in html and ">Costes</a>" in html
        assert f'class="pestana activa" href="{activa}" aria-current="page"' in html.split("subpestanas")[1]


def test_lugar_une_modalidad_y_municipio():
    js = leer("ofertas.js")
    assert "o.ubicacion ||" in js and "nombreModalidad(o.modalidad) || null, sitio" in js


# --- T20 · Condiciones simétricas y totales de Costes ----------------------------------------------
def test_cada_casilla_de_condiciones_va_con_su_ayuda_en_su_celda():
    html = leer("ofertas.html")
    bloques = html.split('<div class="casilla-con-ayuda">')[1:]
    assert len(bloques) == 2
    celdas = [b.split("</div>")[0] for b in bloques]
    assert 'id="solo-remoto"' in celdas[0] and "Solo ofertas 100 % en remoto." in celdas[0]
    assert 'id="solo-salario"' in celdas[1] and "Solo ofertas que dicen cuánto pagan." in celdas[1]
    assert ".casilla-con-ayuda" in leer("estilo.css") and "p.ayuda" in leer("estilo.css")


def _totales_en_node(filas):
    import json
    import re
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node no está instalado")
    js = leer("costes.js")
    fn = re.search(r"function totales\(filas\) \{.*?\n\}\n", js, re.S).group(0)
    salida = subprocess.run([node, "-e", fn + f"console.log(JSON.stringify(totales({json.dumps(filas)})))"],
                            capture_output=True, text=True, check=True).stdout
    return json.loads(salida)


def test_totales_suman_y_ponderan_por_llamadas():
    t = _totales_en_node([
        {"llamadas": 1, "coste": 0.5, "tokens_entrada": 10, "tokens_salida": 1, "latencia_media_ms": 100,
         "tasa_errores": 0},
        {"llamadas": 3, "coste": 1.5, "tokens_entrada": 30, "tokens_salida": 3, "latencia_media_ms": 200,
         "tasa_errores": 1}])
    assert t["llamadas"] == 4 and t["coste"] == 2 and t["tokens_entrada"] == 40 and t["tokens_salida"] == 4
    assert t["latencia_media_ms"] == 175 and t["tasa_errores"] == 0.75


def test_tabla_pinta_total_solo_con_filas():
    js = leer("costes.js")
    assert 'nodo("tfoot")' in js and '"Total"' in js
    assert "if (filas.length) {" in js and "const total = totales(filas);" in js
    assert "tfoot th" in leer("estilo.css") and "tfoot td" in leer("estilo.css")
