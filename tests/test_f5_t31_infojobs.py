"""Fase 5 · T31: InfoJobs configurada e inactiva (RF-5.5b). Respuestas grabadas inventadas."""
import base64

import httpx
import pytest

from horma.ingesta import leer_fuente
from horma.tools.semilla import fuentes_semilla
from horma.web.services import ingesta as servicio

LISTA = {"items": [{"id": "abc123", "title": "Dependienta", "city": "Sevilla",
                    "author": {"name": "Tienda Sur"}, "contractType": {"value": "Indefinido"},
                    "published": "2026-11-16T09:00:00.000Z", "link": "https://www.infojobs.net/oferta/abc123",
                    "salaryDescription": "18.000 € bruto/año"}]}
DETALLE = {"description": "Atención al público y caja."}


def _infojobs():
    return next(f for f in fuentes_semilla() if f.nombre == "infojobs")


def test_infojobs_esta_configurada_pero_inactiva_y_pide_detalle():
    f = _infojobs()
    assert f.activa is False and f.detalle is not None and f.atribucion
    assert f.auth_basica and f.variables()


def test_infojobs_lee_lista_y_detalle_con_basic_auth():
    peticiones = []

    def responder(request: httpx.Request):
        peticiones.append(request)
        return httpx.Response(200, json=DETALLE if "/offer/abc123" in request.url.path else LISTA)
    [o] = leer_fuente(_infojobs(), httpx.Client(transport=httpx.MockTransport(responder)), limite=5,
                      entorno={"INFOJOBS_CLIENT_ID": "yo", "INFOJOBS_CLIENT_SECRET": "clave"})
    assert "Atención al público" in o.texto and o.url == "https://www.infojobs.net/oferta/abc123"
    assert "Tienda Sur" in o.texto
    esperado = "Basic " + base64.b64encode(b"yo:clave").decode()
    assert [r.headers["Authorization"] for r in peticiones] == [esperado, esperado]


@pytest.mark.bd
def test_la_ingesta_no_llama_a_infojobs_mientras_este_inactiva(motor_app, bd_limpia):
    with pytest.raises(servicio.Conflicto):
        servicio.empezar_ejecucion(motor_app, "infojobs", 5)
    fuente = next(f for f in servicio.resumen(motor_app)["fuentes"] if f["nombre"] == "infojobs")
    assert fuente["activa"] is False and fuente["ultima_ejecucion"] is None
