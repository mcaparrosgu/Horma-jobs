import pytest
from sqlalchemy import text

from horma.llm.simulado import ProveedorSimulado
from horma.web.db import sesion_de, sesion_sin_usuaria
from horma.web.queue import cola, worker
from horma.web.services import ofertas as servicio

pytestmark = pytest.mark.bd

TEXTO = ("Se busca camarera en Bar La Marina, Valencia.\nContrato indefinido, presencial.\n"
         "Salario: entre 16000 y 18000 euros brutos anuales.\nSe requiere inglés.")
BUENA = {"titulo": "Camarera", "empresa": "Bar La Marina", "ubicacion": "Valencia",
         "remoto": False, "contrato": "indefinido",
         "salario": {"minimo": 16000, "maximo": 18000, "moneda": "EUR"}, "idiomas": ["inglés"]}


@pytest.fixture
def usuaria(motor_app, bd_limpia):
    with sesion_sin_usuaria(motor_app) as s:
        return s.execute(text("select obtener_o_crear_usuaria('google-A')")).scalar_one()


def _oferta(motor, usuaria, texto=TEXTO, tope_coste=1.0, tope_reintentos=3):
    return servicio.crear_y_encolar(motor, usuaria, texto, tope_coste=tope_coste,
                                    tope_reintentos=tope_reintentos)


def test_la_tarea_guarda_ids_y_no_texto(motor_migrador):
    with motor_migrador.connect() as c:
        cols = {r[0]: r[1] for r in c.execute(text(
            "select column_name, data_type from information_schema.columns "
            "where table_name='tareas'"))}
    assert "entidad_id" in cols
    assert not any(n in cols for n in ("texto", "texto_crudo", "payload", "carga"))


def test_reclamar_entrega_cada_tarea_una_vez_y_none_si_vacia(motor_app, usuaria):
    _oferta(motor_app, usuaria)
    _oferta(motor_app, usuaria)
    t1, t2 = cola.reclamar(motor_app), cola.reclamar(motor_app)
    assert t1["id"] != t2["id"] and t1["estado"] == "en_curso" and t1["intentos"] == 1
    assert cola.reclamar(motor_app) is None


def test_el_worker_procesa_la_oferta_con_origen_y_metricas(motor_app, usuaria):
    oid = _oferta(motor_app, usuaria)
    assert worker.procesar_una(motor_app, ProveedorSimulado([BUENA])) == "hecha"
    with sesion_de(motor_app, usuaria) as s:
        o = s.execute(text("select estado, titulo, empresa, salario_minimo, remoto, idiomas "
                           "from ofertas where id=:i"), {"i": oid}).one()
        origenes = s.execute(text("select campo, fragmento from origen where entidad_id=:i"),
                             {"i": oid}).all()
        t = s.execute(text("select estado, coste_acumulado from tareas")).one()
        n = s.execute(text("select count(*) from llm_llamadas")).scalar_one()
    assert o.estado == "procesada" and o.titulo == "Camarera" and float(o.salario_minimo) == 16000
    assert o.remoto is False and o.idiomas == ["inglés"]
    assert {c for c, _ in origenes} >= {"titulo", "empresa", "salario_minimo", "idiomas"}
    assert all(f for _, f in origenes)  # RT-08: nada sin fragmento de origen
    assert t.estado == "hecha" and float(t.coste_acumulado) > 0 and n == 1


def test_un_dato_sin_origen_en_el_texto_no_se_guarda(motor_app, usuaria):
    oid = _oferta(motor_app, usuaria)
    inventada = dict(BUENA, empresa="Empresa Inventada SA")  # no aparece en el texto
    worker.procesar_una(motor_app, ProveedorSimulado([inventada]))
    with sesion_de(motor_app, usuaria) as s:
        empresa = s.execute(text("select empresa from ofertas where id=:i"), {"i": oid}).scalar_one()
    assert empresa is None


def test_tope_de_reintentos_deja_la_oferta_en_error_con_motivo(motor_app, usuaria):
    oid = _oferta(motor_app, usuaria, tope_reintentos=2)
    mala = ProveedorSimulado([{"mal": 1}] * 10)
    assert worker.procesar_una(motor_app, mala) == "pendiente"  # 1.º intento: se reintenta
    assert worker.procesar_una(motor_app, mala) == "error"      # 2.º: agotados
    with sesion_de(motor_app, usuaria) as s:
        o = s.execute(text("select estado, motivo_error from ofertas where id=:i"),
                      {"i": oid}).one()
        t = s.execute(text("select estado, motivo_error from tareas")).one()
    assert o.estado == "error" and "reintentos" in o.motivo_error
    assert t.estado == "error"


def test_tope_de_coste_detiene_la_tarea(motor_app, usuaria):
    oid = _oferta(motor_app, usuaria, tope_coste=0.0000001, tope_reintentos=5)
    assert worker.procesar_una(motor_app, ProveedorSimulado([{"mal": 1}] * 10)) == "error"
    with sesion_de(motor_app, usuaria) as s:
        o = s.execute(text("select estado, motivo_error from ofertas where id=:i"),
                      {"i": oid}).one()
    assert o.estado == "error" and "coste" in o.motivo_error


def test_worker_sin_tareas_devuelve_none(motor_app, bd_limpia):
    assert worker.procesar_una(motor_app, ProveedorSimulado([])) is None
