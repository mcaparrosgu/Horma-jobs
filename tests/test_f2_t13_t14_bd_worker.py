"""Fase 2 · T13-T14: migración 0003 (tablas, RLS, normalización) y worker de perfil y recomendación
(con la puerta simulada)."""
import importlib
import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from horma.llm.simulado import ProveedorSimulado
from horma.schemas.oferta import Oferta
from horma.web.db import sesion_de, sesion_sin_usuaria, sesion_sistema
from horma.web.queue import worker
from horma.web.repositories import ofertas as repo_ofertas
from horma.web.repositories import tareas

pytestmark = pytest.mark.bd

CV = "Ana Pérez\nCamarera en Bar Sol, 2020-2023\nInglés B2"
TAX = {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior",
       "stack": []}
BUENO = {"contenido": "## Experiencia\nCamarera en Bar Sol, 2020-2023",
         "traza": [{"frase": "Camarera en Bar Sol, 2020-2023",
                    "fragmento": "Camarera en Bar Sol, 2020-2023"}]}
MALO = {"contenido": "## Experiencia\nDirectora en Hotel Ritz, 2010-2015", "traza": []}
EXPLICACION = "Tiene experiencia en sala. La oferta pide camarera con experiencia."


def _usuarias(motor):
    with sesion_sin_usuaria(motor) as s:
        a = s.execute(text("select obtener_o_crear_usuaria('google-A')")).scalar_one()
        b = s.execute(text("select obtener_o_crear_usuaria('google-B')")).scalar_one()
    return a, b


def _cv(motor, u, nombre="CV hostelería", texto=CV, clase="fuente"):
    with sesion_de(motor, u) as s:
        return s.execute(text(
            "insert into cv_archivos (usuaria_id, nombre, nombre_original, ruta, tipo, clase, tamano, texto) "
            "values (:u, :n, 'cv.md', gen_random_uuid()::text, 'md', :c, 10, :t) returning id"),
            {"u": u, "n": nombre, "c": clase, "t": texto}).scalar_one()


def _encolar(motor, u, tipo, entidad_id, tope_coste=1.0, tope_reintentos=3):
    with sesion_de(motor, u) as s:
        tareas.encolar(s, u, tipo, entidad_id, tope_coste, tope_reintentos)


def _perfil_pendiente(motor, u):
    from horma.web.repositories import perfiles
    with sesion_de(motor, u) as s:
        return perfiles.nueva_version(s, u)


def _extraccion(cv_id):
    return {"perfil": {
        "experiencias": [{"puesto": "Camarera", "empresa": "Bar Sol", "inicio": "2020", "fin": "2023",
                          "origen": {"fuente": "cv", "cv_id": cv_id,
                                     "fragmento": "Camarera en Bar Sol, 2020-2023"}}],
        "idiomas": [{"idioma": "en", "nivel": "B2",
                     "origen": {"fuente": "cv", "cv_id": cv_id, "fragmento": "Inglés B2"}}]},
        "cv_maestro": "# Ana Pérez\n\nCamarera en Bar Sol, 2020-2023\n"}


def _perfilar_hecho(motor, u):
    """Una usuaria con un CV y su perfil ya construido por el worker."""
    cv_id = _cv(motor, u)
    pid, _ = _perfil_pendiente(motor, u)
    _encolar(motor, u, "perfilar", pid)
    assert worker.procesar_una(motor, ProveedorSimulado([_extraccion(cv_id), TAX])) == "hecha"
    return pid


# --- T13: esquema y RLS ------------------------------------------------------------------------
def test_las_tablas_y_columnas_del_esquema_de_la_fase_2(motor_migrador):
    with motor_migrador.connect() as c:
        def columnas(tabla):
            return {r[0] for r in c.execute(text(
                "select column_name from information_schema.columns where table_name=:t"), {"t": tabla})}
        assert {"usuaria_id", "nombre", "nombre_original", "ruta", "tipo", "clase", "tamano",
                "texto", "creado_en"} <= columnas("cv_archivos")
        assert {"usuaria_id", "version", "datos", "cv_maestro", "preguntas_pendientes",
                "instrucciones_embebidas", "sector", "familia", "nivel", "estado",
                "motivo_error"} <= columnas("perfiles")
        assert {"familias", "sectores", "contratos", "niveles", "paises", "idiomas", "solo_remoto",
                "solo_salario", "sueldo_minimo", "orden", "rango_min", "rango_max",
                "origen"} <= columnas("preferencias")
        assert {"usuaria_id", "perfil_version", "nombre", "sector", "familia", "contenido", "traza",
                "estado", "motivo_error"} <= columnas("cv_base")
        assert {"usuaria_id", "oferta_id", "perfil_version", "nota", "condiciones", "explicacion",
                "cita_perfil", "cita_oferta", "retirada", "correccion",
                "corregido_en"} <= columnas("matches")
        assert {"pais", "tipo_contrato", "idiomas_norm", "salario_anual_eur_min",
                "salario_anual_eur_max"} <= columnas("ofertas")


def test_una_usuaria_no_lee_perfil_cv_ni_matches_de_otra(motor_app, bd_limpia):
    a, b = _usuarias(motor_app)
    cv_id = _cv(motor_app, a)
    pid, _ = _perfil_pendiente(motor_app, a)
    with sesion_sistema(motor_app) as s:
        s.execute(text("insert into ofertas (texto_crudo) values ('x')"))
    with sesion_de(motor_app, a) as s:
        s.execute(text("insert into preferencias (usuaria_id) values (:u)"), {"u": a})
        s.execute(text("insert into cv_base (usuaria_id, perfil_version, nombre) values (:u, 1, 'n')"),
                  {"u": a})
        s.execute(text("insert into matches (usuaria_id, oferta_id, perfil_version, nota, condiciones) "
                       "values (:u, 1, 1, 80, 'alto')"), {"u": a})
    with sesion_de(motor_app, b) as s:
        for tabla in ("cv_archivos", "perfiles", "preferencias", "cv_base", "matches"):
            assert s.execute(text(f"select count(*) from {tabla}")).scalar_one() == 0, tabla
        assert s.execute(text("update perfiles set estado='error'")).rowcount == 0
    with pytest.raises(DBAPIError), sesion_de(motor_app, b) as s:
        s.execute(text("insert into perfiles (usuaria_id, version) values (:u, 5)"), {"u": a})
    assert cv_id and pid


def test_el_nombre_de_cv_es_unico_por_usuaria_pero_no_entre_usuarias(motor_app, bd_limpia):
    a, b = _usuarias(motor_app)
    _cv(motor_app, a, nombre="Mi CV")
    _cv(motor_app, b, nombre="Mi CV")
    with pytest.raises(DBAPIError):
        _cv(motor_app, a, nombre="Mi CV")


def _oferta_procesada(motor, **campos):
    base = {"titulo": "Camarera", "ubicacion": "Valencia", "contrato": "contrato fijo",
            "sector": "hosteleria_turismo", "familia": "hosteleria_restauracion", "nivel": "junior",
            "fantasma": False, "fraude": False, "salario_publicado": False}
    base.update(campos)
    cols = ", ".join(base)
    marcas = ", ".join(f":{k}" for k in base)
    with sesion_sistema(motor) as s:
        return s.execute(text(
            f"insert into ofertas (texto_crudo, estado, {cols}) values ('texto', 'procesada', {marcas}) "
            "returning id"), base).scalar_one()


def test_una_oferta_nueva_queda_normalizada_al_guardarse(motor_app, bd_limpia):
    with sesion_sistema(motor_app) as s:
        oid = s.execute(text(
            "insert into ofertas (texto_crudo) values ('Camarera en Berlin, Germany. 2.000 €/mes') "
            "returning id")).scalar_one()
        o = Oferta.model_validate({
            "titulo": "Camarera", "ubicacion": "Berlin, Germany", "contrato": "contrato fijo",
            "idiomas": ["inglés", "alemán"], "salario": {"minimo": 2000, "maximo": 2000, "moneda": "EUR"},
            "auditoria": {"fantasma": False, "fraude": False, "salario_publicado": True},
            "taxonomia": TAX})
        repo_ofertas.guardar(s, oid, o, [])
        f = s.execute(text("select pais, tipo_contrato, idiomas_norm, salario_anual_eur_min, "
                           "salario_anual_eur_max from ofertas where id=:i"), {"i": oid}).one()
    assert f.pais == "DE" and f.tipo_contrato == "indefinido" and f.idiomas_norm == ["en", "de"]
    assert float(f.salario_anual_eur_min) == 24000 and float(f.salario_anual_eur_max) == 24000


def test_una_oferta_ya_existente_se_normaliza_en_la_migracion(motor_migrador, bd_limpia):
    with motor_migrador.begin() as c:
        oid = c.execute(text(
            "insert into ofertas (texto_crudo, estado, titulo, ubicacion, contrato, salario_minimo, "
            "salario_maximo, salario_moneda, idiomas) values ('Pagamos 1.500-1.800 € al mes', "
            "'procesada', 'Dev', 'Lisboa, Portugal', 'Full-time', 1500, 1800, 'EUR', "
            "cast('[\"inglés\"]' as jsonb)) returning id")).scalar_one()
        migracion = importlib.import_module("horma.web.migrations.versions.0003_fase2_perfil_recomendacion")
        migracion._rellenar_ofertas(c)
        f = c.execute(text("select pais, tipo_contrato, idiomas_norm, salario_anual_eur_min, "
                           "salario_anual_eur_max from ofertas where id=:i"), {"i": oid}).one()
    assert f.pais == "PT" and f.tipo_contrato == "jornada_completa" and f.idiomas_norm == ["en"]
    assert float(f.salario_anual_eur_min) == 18000 and float(f.salario_anual_eur_max) == 21600


# --- T14: worker -------------------------------------------------------------------------------
def test_perfilar_guarda_version_origenes_y_preferencias_del_cv(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    pid = _perfilar_hecho(motor_app, a)
    with sesion_de(motor_app, a) as s:
        p = s.execute(text("select version, estado, cv_maestro, sector, familia, datos "
                           "from perfiles where id=:i"), {"i": pid}).one()
        origenes = s.execute(text("select campo, fragmento from origen where entidad='perfil' "
                                  "and entidad_id=:i order by campo"), {"i": pid}).all()
        prefs = s.execute(text("select familias, sectores, idiomas, origen from preferencias")).one()
        t = s.execute(text("select estado, coste_acumulado from tareas")).one()
    assert p.version == 1 and p.estado == "hecha" and p.cv_maestro.startswith("# Ana")
    assert p.familia == "hosteleria_restauracion" and p.datos["experiencias"][0]["puesto"] == "Camarera"
    assert dict(origenes) == {"experiencias.0": "Camarera en Bar Sol, 2020-2023",
                              "idiomas.0": "Inglés B2"}
    assert prefs.familias == ["hosteleria_restauracion"] and prefs.idiomas == ["en"]
    assert prefs.origen["familias"] == "cv"
    assert t.estado == "hecha" and float(t.coste_acumulado) > 0


def test_las_preferencias_que_escribio_la_usuaria_no_se_pisan(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    with sesion_de(motor_app, a) as s:
        s.execute(text("insert into preferencias (usuaria_id, familias, origen) values "
                       "(:u, '{ventas_comercial}', cast('{\"familias\": \"usuaria\"}' as jsonb))"),
                  {"u": a})
    _perfilar_hecho(motor_app, a)
    with sesion_de(motor_app, a) as s:
        prefs = s.execute(text("select familias, sectores, origen from preferencias")).one()
    assert prefs.familias == ["ventas_comercial"] and prefs.sectores == ["hosteleria_turismo"]
    assert prefs.origen == {"familias": "usuaria", "sectores": "cv", "idiomas": "cv"}


def test_perfilar_sin_cv_falla_con_motivo(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    pid, _ = _perfil_pendiente(motor_app, a)
    _encolar(motor_app, a, "perfilar", pid, tope_reintentos=1)
    assert worker.procesar_una(motor_app, ProveedorSimulado([])) == "error"
    with sesion_de(motor_app, a) as s:
        p = s.execute(text("select estado, motivo_error from perfiles")).one()
    assert p.estado == "error" and "ningún CV" in p.motivo_error


def test_error_con_paso_y_motivo_en_la_version_del_perfil(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    _cv(motor_app, a)
    pid, _ = _perfil_pendiente(motor_app, a)
    _encolar(motor_app, a, "perfilar", pid, tope_reintentos=1)
    assert worker.procesar_una(motor_app, ProveedorSimulado([{"mal": 1}] * 5)) == "error"
    with sesion_de(motor_app, a) as s:
        p = s.execute(text("select estado, motivo_error from perfiles")).one()
        t = s.execute(text("select estado, motivo_error from tareas")).one()
    assert p.estado == "error" and "reintentos" in p.motivo_error and "extraer" in p.motivo_error
    assert t.estado == "error"


def test_un_tope_de_coste_bajo_detiene_la_tarea(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    _cv(motor_app, a)
    pid, _ = _perfil_pendiente(motor_app, a)
    _encolar(motor_app, a, "perfilar", pid, tope_coste=0.0000001, tope_reintentos=5)
    assert worker.procesar_una(motor_app, ProveedorSimulado([{"mal": 1}] * 5)) == "error"
    with sesion_de(motor_app, a) as s:
        p = s.execute(text("select estado, motivo_error from perfiles")).one()
    assert p.estado == "error" and "coste" in p.motivo_error


def test_clasificar_perfil_rellena_la_taxonomia_de_la_version_copiada(motor_app, bd_limpia):
    from horma.web.repositories import perfiles
    a, _ = _usuarias(motor_app)
    pid1 = _perfilar_hecho(motor_app, a)
    with sesion_de(motor_app, a) as s:
        fila = perfiles.perfil_fila(s, pid1)
        pid2, v2 = perfiles.nueva_version(s, a)
        s.execute(text("update perfiles set datos = cast(:d as jsonb) where id = :i"),
                  {"d": json.dumps(fila["datos"]), "i": pid2})
    assert v2 == 2
    _encolar(motor_app, a, "clasificar_perfil", pid2)
    nueva = dict(TAX, familia="ventas_comercial", nivel="intermedio")
    assert worker.procesar_una(motor_app, ProveedorSimulado([nueva])) == "hecha"
    with sesion_de(motor_app, a) as s:
        filas = s.execute(text("select version, estado, familia, nivel from perfiles order by version")).all()
    assert [tuple(f) for f in filas] == [(1, "hecha", "hosteleria_restauracion", "junior"),
                                         (2, "hecha", "ventas_comercial", "intermedio")]


def test_generar_cv_base_guarda_los_verificados_y_deja_el_motivo_de_los_rechazados(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    pid = _perfilar_hecho(motor_app, a)
    with sesion_de(motor_app, a) as s:  # dos destinos: taxonomía y una familia marcada
        s.execute(text("update preferencias set familias = '{hosteleria_restauracion,ventas_comercial}'"))
    _encolar(motor_app, a, "generar_cv_base", pid)
    assert worker.procesar_una(motor_app, ProveedorSimulado([BUENO, MALO, MALO])) == "hecha"
    with sesion_de(motor_app, a) as s:
        filas = s.execute(text("select estado, familia, contenido, motivo_error, perfil_version "
                               "from cv_base order by id")).all()
    assert [f.estado for f in filas] == ["hecho", "rechazado"]
    assert filas[0].contenido.startswith("## Experiencia") and filas[0].perfil_version == 1
    assert filas[1].familia == "ventas_comercial" and filas[1].motivo_error and filas[1].contenido == ""


def test_generar_cv_base_con_el_perfil_aun_pendiente_falla(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    pid, _ = _perfil_pendiente(motor_app, a)
    _encolar(motor_app, a, "generar_cv_base", pid, tope_reintentos=1)
    assert worker.procesar_una(motor_app, ProveedorSimulado([])) == "error"
    with sesion_de(motor_app, a) as s:
        fila = s.execute(text("select estado, motivo_error from cv_base")).one()
    assert fila.estado == "error" and "no está listo" in fila.motivo_error


def _match(i, nota=80):
    return {"oferta_id": i, "nota": nota, "condiciones": "medio", "explicacion": EXPLICACION,
            "cita_perfil": "Camarera en Bar Sol", "cita_oferta": "camarera"}


def test_recomendar_filtra_puntua_guarda_y_no_repite_lo_ya_puntuado(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    buena = _oferta_procesada(motor_app, pais="ES")
    otra_pais = _oferta_procesada(motor_app, pais="DE")
    fantasma = _oferta_procesada(motor_app, pais="ES", fantasma=True)
    pid = _perfilar_hecho(motor_app, a)
    with sesion_de(motor_app, a) as s:
        s.execute(text("update preferencias set paises = '{ES}'"))
    _encolar(motor_app, a, "recomendar", pid)
    prov = ProveedorSimulado([{"matches": [_match(buena)]}])
    assert worker.procesar_una(motor_app, prov) == "hecha"
    assert len(prov.llamadas) == 1
    assert f'"oferta_id":{otra_pais}' not in prov.llamadas[0]["usuario"]
    assert f'"oferta_id":{fantasma}' not in prov.llamadas[0]["usuario"]
    with sesion_de(motor_app, a) as s:
        m = s.execute(text("select oferta_id, perfil_version, nota, condiciones, retirada "
                           "from matches")).all()
    assert [tuple(x) for x in m] == [(buena, 1, 80, "medio", False)]
    # Segunda vez: lo ya puntuado no se vuelve a pedir al modelo.
    _encolar(motor_app, a, "recomendar", pid)
    prov2 = ProveedorSimulado([])
    assert worker.procesar_una(motor_app, prov2) == "hecha" and prov2.llamadas == []


def test_recomendar_se_detiene_con_un_tope_de_coste_bajo(motor_app, bd_limpia):
    a, _ = _usuarias(motor_app)
    _oferta_procesada(motor_app, pais="ES")
    pid = _perfilar_hecho(motor_app, a)
    _encolar(motor_app, a, "recomendar", pid, tope_coste=0.0000001, tope_reintentos=5)
    assert worker.procesar_una(motor_app, ProveedorSimulado([{"mal": 1}] * 5)) == "error"
    with sesion_de(motor_app, a) as s:
        t = s.execute(text("select estado, motivo_error from tareas order by id desc limit 1")).one()
    assert t.estado == "error" and "coste" in t.motivo_error


def test_una_usuaria_no_puede_ejecutar_la_tarea_sobre_el_perfil_de_otra(motor_app, bd_limpia):
    a, b = _usuarias(motor_app)
    pid_a = _perfilar_hecho(motor_app, a)
    _encolar(motor_app, b, "recomendar", pid_a, tope_reintentos=1)
    assert worker.procesar_una(motor_app, ProveedorSimulado([])) == "error"
    with sesion_de(motor_app, b) as s:
        t = s.execute(text("select motivo_error from tareas")).scalar_one()
    assert "no existe el perfil" in t
