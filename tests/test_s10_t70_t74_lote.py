# ruff: noqa: F811
"""S10, T70-T74: subir varios documentos a la vez (RF-10.18 a 10.18i)."""
import re
from pathlib import Path

import pytest
from sqlalchemy import text

from horma.config import ajustes
from horma.web.db import sesion_de
from horma.web.services import cv as servicio_cv
from tests.test_f2_t15_t19_api import app, archivos, entrar  # noqa: F401  (fixtures y ayudante)
from tests.test_s8_t43_clasificar_documento import CARTA, CV

CV_B = CV.replace("Lucía Ferrer", "Marta Gil").replace("Bar Sol", "Café Mar")
CV_C = CV.replace("Lucía Ferrer", "Rosa Peña").replace("La Barca", "El Faro")
DUDOSO_1 = "Notas\nde la reunión\ndel lunes"
DUDOSO_2 = "Apuntes\nde la visita\ndel martes"
ESTATICOS = Path(__file__).resolve().parent.parent / "horma" / "web" / "static"
pytestmark = pytest.mark.bd


def _lote(c, h, docs, clases=None, **datos):
    """`docs`: [(nombre, texto)]; `clases`: una por archivo (o ninguna)."""
    ficheros = [("archivos", (n, t.encode() if isinstance(t, str) else t)) for n, t in docs]
    if clases is not None:
        datos["clases"] = clases
    return c.post("/api/cv/lote", headers=h, files=ficheros, data=datos)


def _filas(motor):
    with motor.connect() as cx:
        return cx.execute(text("select nombre, clase from cv_archivos order by id")).all()


def _tareas_perfilar(motor):
    with motor.connect() as cx:
        return cx.execute(text("select count(*) from tareas where tipo='perfilar'")).scalar_one()


def _versiones(motor):
    with motor.connect() as cx:
        return cx.execute(text("select count(*) from perfiles")).scalar_one()


# --- T70: hasta 5, válidos guardados, fallidos con su motivo --------------------------------------
def test_tres_validos_dan_tres_filas_y_un_solo_perfilar(app, motor_migrador):
    c, h, _ = entrar(app)
    r = _lote(c, h, [("a.md", CV), ("b.md", CV_B), ("c.md", CV_C)])
    assert r.status_code == 201
    d = r.json()
    assert [x["nombre"] for x in d["subidos"]] == ["a", "b", "c"]
    assert d["fallidos"] == [] and d["repetidos"] == [] and d["dudosos"] == []
    assert d["perfil"] == "en_marcha"
    assert len(_filas(motor_migrador)) == 3 and _tareas_perfilar(motor_migrador) == 1
    assert _versiones(motor_migrador) == 1                                  # RF-10.18f: una sola versión


def test_los_fallidos_traen_nombre_y_motivo_y_no_impiden_los_demas(app, motor_migrador, monkeypatch):
    monkeypatch.setattr(ajustes(), "max_cv_bytes", 2000)
    c, h, _ = entrar(app)
    r = _lote(c, h, [("bien.md", CV), ("raro.exe", "x"), ("grande.md", CV + "x" * 5000),
                     ("roto.pdf", b"no soy un pdf")])
    assert r.status_code == 201
    d = r.json()
    assert [x["nombre"] for x in d["subidos"]] == ["bien"]
    motivos = {f["nombre"]: f["motivo"] for f in d["fallidos"]}
    assert motivos["raro.exe"] == "formato no admitido"
    assert re.fullmatch(r"pesa más de \d+(,\d+)? MB", motivos["grande.md"]) or "pesa más de" in motivos["grande.md"]
    assert motivos["roto.pdf"] == "no se ha podido leer"
    assert len(_filas(motor_migrador)) == 1


def test_cinco_archivos_grandes_caben_en_la_peticion(app, motor_migrador, monkeypatch):
    monkeypatch.setattr(ajustes(), "max_cv_bytes", 20_000)
    c, h, _ = entrar(app)
    docs = [(f"{i}.md", CV.replace("Lucía", f"Lucía{i}") + "\n" + "x" * 18_800) for i in range(5)]
    r = _lote(c, h, docs)                 # unos 95 kB: más que un solo archivo y su margen
    assert r.status_code == 201 and len(r.json()["subidos"]) == 5


def test_mas_de_cinco_no_sube_ninguno(app, motor_migrador):
    c, h, _ = entrar(app)
    r = _lote(c, h, [(f"{i}.md", CV.replace("Lucía", f"Lucía{i}")) for i in range(6)])
    assert r.status_code == 422
    assert r.json()["detail"] == "Puedes subir hasta 5 archivos a la vez. Elige 5 o menos."
    assert _filas(motor_migrador) == [] and _tareas_perfilar(motor_migrador) == 0


def test_un_lote_de_uno_funciona_y_un_nombre_usado_va_a_fallidos(app, motor_migrador):
    c, h, _ = entrar(app)
    assert _lote(c, h, [("a.md", CV)]).status_code == 201
    r = _lote(c, h, [("a.md", CV_B), ("b.md", CV_C)])           # mismo nombre, otro contenido (regla de hoy)
    d = r.json()
    assert [x["nombre"] for x in d["subidos"]] == ["b"]
    assert d["fallidos"] == [{"nombre": "a.md", "motivo": "ya tienes un documento con ese nombre"}]


def test_sin_archivos_no_vale_y_otra_usuaria_no_ve_los_documentos(app, motor_migrador):
    c, h, _ = entrar(app)
    assert c.post("/api/cv/lote", headers=h).status_code == 422
    assert _lote(c, h, [("a.md", CV)]).status_code == 201
    otra, h2, _ = entrar(app, "google-B")
    assert otra.get("/api/cv").json() == []


# --- T71: repetidos por contenido -----------------------------------------------------------------
def test_dos_identicos_en_el_lote_dan_una_fila_y_un_repetido(app, motor_migrador):
    c, h, _ = entrar(app)
    d = _lote(c, h, [("a.md", CV), ("copia.md", CV)]).json()
    assert [x["nombre"] for x in d["subidos"]] == ["a"]
    assert d["repetidos"] == [{"nombre": "copia.md", "motivo": "ya estaba subido"}]
    assert len(_filas(motor_migrador)) == 1


def test_uno_identico_a_otro_ya_subido_no_se_guarda_ni_encola(app, motor_migrador):
    c, h, _ = entrar(app)
    assert _lote(c, h, [("a.md", CV)]).status_code == 201
    antes = (_tareas_perfilar(motor_migrador), _versiones(motor_migrador))
    d = _lote(c, h, [("otro-nombre.md", CV)]).json()
    assert d["subidos"] == [] and d["perfil"] is None
    assert d["repetidos"] == [{"nombre": "otro-nombre.md", "motivo": "ya estaba subido"}]
    assert len(_filas(motor_migrador)) == 1
    assert (_tareas_perfilar(motor_migrador), _versiones(motor_migrador)) == antes


# --- T72: un solo perfilar por lote; sin presupuesto, guardados ------------------------------------
def test_solo_cartas_no_rehace_el_perfil(app, motor_migrador):
    c, h, _ = entrar(app)
    d = _lote(c, h, [("c1.md", CARTA), ("c2.md", CARTA.replace("Lucía", "Lucía M."))]).json()
    assert [x["clase"] for x in d["subidos"]] == ["carta", "carta"] and d["perfil"] is None
    assert _tareas_perfilar(motor_migrador) == 0 and _versiones(motor_migrador) == 0


def test_cv_y_carta_juntos_encolan_un_perfilar(app, motor_migrador):
    c, h, _ = entrar(app)
    d = _lote(c, h, [("cv.md", CV), ("carta.md", CARTA)]).json()
    assert d["perfil"] == "en_marcha" and _tareas_perfilar(motor_migrador) == 1


def test_sin_presupuesto_se_guarda_todo_y_el_perfil_queda_aplazado(app, motor_app, motor_migrador, monkeypatch):
    c, h, _ = entrar(app)
    monkeypatch.setattr(ajustes(), "presupuesto_diario_usd", 0.0)
    d = _lote(c, h, [("a.md", CV), ("b.md", CV_B)]).json()
    assert d["perfil"] == "aplazado" and len(d["subidos"]) == 2
    assert len(_filas(motor_migrador)) == 2 and _tareas_perfilar(motor_migrador) == 0
    assert len(list(ajustes_carpeta().iterdir())) == 2                       # los archivos siguen en disco
    assert servicio_cv.rehacer_aplazados(motor_app) == 0                    # sigue sin presupuesto
    monkeypatch.setattr(ajustes(), "presupuesto_diario_usd", 1.0)
    assert servicio_cv.rehacer_aplazados(motor_app) == 1
    assert _tareas_perfilar(motor_migrador) == 1 and _versiones(motor_migrador) == 1


def test_un_solo_cv_sin_presupuesto_tambien_se_guarda(app, motor_migrador, monkeypatch):
    c, h, _ = entrar(app)
    monkeypatch.setattr(ajustes(), "presupuesto_diario_usd", 0.0)
    d = _lote(c, h, [("a.md", CV)]).json()
    assert d["perfil"] == "aplazado" and len(_filas(motor_migrador)) == 1


def ajustes_carpeta() -> Path:
    return Path(ajustes().ruta_archivos)


# --- T73: dudosos, una sola pregunta al final -------------------------------------------------------
def test_dos_claros_y_dos_dudosos_una_pregunta_y_un_perfilar(app, motor_app, motor_migrador):
    c, h, _ = entrar(app)
    d = _lote(c, h, [("cv.md", CV), ("carta.md", CARTA), ("d1.md", DUDOSO_1), ("d2.md", DUDOSO_2)]).json()
    assert [x["nombre"] for x in d["subidos"]] == ["cv", "carta"]
    assert d["dudosos"] == [{"indice": 2, "nombre": "d1.md"}, {"indice": 3, "nombre": "d2.md"}]
    assert d["perfil"] == "pendiente_de_respuesta"
    assert _tareas_perfilar(motor_migrador) == 0                              # no encola hasta responder
    r = _lote(c, h, [("d1.md", DUDOSO_1), ("d2.md", DUDOSO_2)], clases=["carta", "fuente"])
    d2 = r.json()
    assert r.status_code == 201 and [x["clase"] for x in d2["subidos"]] == ["carta", "fuente"]
    assert d2["perfil"] == "en_marcha" and d2["dudosos"] == []
    assert _tareas_perfilar(motor_migrador) == 1 and _versiones(motor_migrador) == 1   # una sola versión
    assert len(_filas(motor_migrador)) == 4


def test_cerrar_la_pregunta_encola_con_los_claros_y_no_guarda_los_dudosos(app, motor_migrador):
    c, h, _ = entrar(app)
    _lote(c, h, [("cv.md", CV), ("d1.md", DUDOSO_1)])
    assert _tareas_perfilar(motor_migrador) == 0
    r = c.post("/api/cv/lote", headers=h, data={"cerrar": "true"})
    assert r.status_code == 200 and r.json()["perfil"] == "en_marcha"
    assert _tareas_perfilar(motor_migrador) == 1 and _versiones(motor_migrador) == 1
    assert [f[0] for f in _filas(motor_migrador)] == ["cv"]
    assert c.post("/api/cv/lote", headers=h, data={"cerrar": "true"}).json()["perfil"] is None   # nada que rehacer


def test_si_ella_se_va_sin_responder_el_worker_no_rehace_antes_de_tiempo_pero_si_despues(
        app, motor_app, motor_migrador):
    c, h, _ = entrar(app)
    _lote(c, h, [("cv.md", CV), ("d1.md", DUDOSO_1)])
    assert servicio_cv.rehacer_aplazados(motor_app) == 0                      # aún puede responder
    with motor_migrador.begin() as cx:                                        # pasan 20 minutos
        cx.execute(text("update perfiles set creado_en = now() - interval '20 minutes'"))
    assert servicio_cv.rehacer_aplazados(motor_app) == 1
    assert _tareas_perfilar(motor_migrador) == 1
    assert servicio_cv.rehacer_aplazados(motor_app) == 0                      # y no se rehace dos veces


def test_una_clase_invalida_es_un_error_de_la_peticion(app, motor_migrador):
    c, h, _ = entrar(app)
    assert _lote(c, h, [("d1.md", DUDOSO_1)], clases=["otra"]).status_code == 422
    assert _filas(motor_migrador) == []


def test_sesion_de_usuaria_sigue_aislada(app, motor_app):    # el servicio no se salta la RLS
    c, h, u = entrar(app)
    _lote(c, h, [("a.md", CV)])
    with sesion_de(motor_app, 999999) as s:
        assert s.execute(text("select count(*) from cv_archivos")).scalar_one() == 0


# --- T74: pantalla ------------------------------------------------------------------------------------
def _leer(nombre):
    return (ESTATICOS / nombre).read_text(encoding="utf-8")


def test_los_dos_selectores_son_multiples_y_dicen_hasta_5():
    html = _leer("perfil.html")
    for ident in ("archivo", "archivo-doc"):
        entrada = re.search(rf'<input id="{ident}"[^>]*>', html).group(0)
        assert " multiple" in entrada
    assert html.lower().count("hasta 5 archivos") >= 2


def test_perfil_js_envia_todo_en_una_llamada_con_una_barra_y_un_mensaje():
    js = _leer("perfil.js")
    assert "/api/cv/lote" in js and 'datos.append("archivos"' in js
    assert "entrada.files" in js and "TEXTOS.maxLote" in js                   # comprueba el máximo antes
    assert "TEXTOS.leyendoArchivos" in js and "if (!barraLectura && archivos.length)" in js   # la barra se crea una vez
    assert "!subiendoLote && barraLectura" in js                              # y `cargarPerfil` no la quita
    assert "preguntarClases" in js and "elegidos.map" in js and js.count("\"Continuar\"") == 1
    assert 'api("/api/cv", { metodo: "POST"' not in js                       # ya no sube de uno en uno


def test_los_textos_estan_en_textos_js():
    t = _leer("textos.js")
    for clave in ("maxLote", "leyendoArchivos", "perfilAplazado", "dudososSinResponder"):
        assert clave in t
    assert "Puedes subir hasta 5 archivos a la vez. Elige 5 o menos." in t
