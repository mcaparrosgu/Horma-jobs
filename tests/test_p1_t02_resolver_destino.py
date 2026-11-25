"""Paso 1 · T02 (spec 011, parte 1): `resolver_destino` reconoce el portal por su dirección (RF-11.1b)."""
import httpx
import pytest

from horma.tools.descargar import seguir_redireccion
from horma.tools.resolver_destino import Destino, resolver_destino


def _sin_red(url: str) -> str:
    raise AssertionError(f"No debía seguir redirecciones: {url}")


@pytest.mark.parametrize("url,portal", [
    ("https://empresa.teamtailor.com/jobs/123-dev", "Teamtailor"),
    ("https://jobs.personio.de/job/456", "Personio"),
    ("https://boards.greenhouse.io/acme/jobs/789", "Greenhouse"),
    ("https://jobs.lever.co/acme/abc", "Lever"),
    ("https://jobs.ashbyhq.com/acme/abc", "Ashby"),
    ("https://apply.workable.com/acme/j/ABC/", "Workable"),
    ("https://jobs.smartrecruiters.com/Acme/123", "SmartRecruiters"),
    ("https://acme.recruitee.com/o/dev", "Recruitee"),
    ("https://acme.wd3.myworkdayjobs.com/es/jobs/job/x", "Workday"),
    ("https://career5.successfactors.eu/career?company=acme", "SuccessFactors"),
])
def test_cada_portal_se_reconoce_por_su_direccion(url, portal):
    d = resolver_destino(url, seguir=_sin_red)
    assert d == Destino(portal=portal, automatico=True, exige_cuenta=d.exige_cuenta, url_final=url)


@pytest.mark.parametrize("url,portal", [
    ("https://www.infojobs.net/madrid/dev/of-i123", "InfoJobs"),
    ("https://www.welcometothejungle.com/es/companies/acme/jobs/dev", "Welcome to the Jungle"),
])
def test_infojobs_y_wttj_dan_su_canal_y_exigen_cuenta(url, portal):
    d = resolver_destino(url, seguir=_sin_red)
    assert (d.portal, d.automatico, d.exige_cuenta) == (portal, True, True)


@pytest.mark.parametrize("url,portal", [
    ("https://www.linkedin.com/jobs/view/123", "LinkedIn"),
    ("https://es.indeed.com/viewjob?jk=abc", "Indeed"),
    ("https://www.glassdoor.es/job-listing/x", "Glassdoor"),
])
def test_linkedin_e_indeed_dan_siempre_no_automatico(url, portal):
    d = resolver_destino(url, seguir=_sin_red)
    assert d.automatico is False and d.portal is None and portal in d.motivo


def test_una_redireccion_se_sigue_hasta_el_portal_final():
    vistas = []

    def seguir(url):
        vistas.append(url)
        return "https://boards.greenhouse.io/acme/jobs/1"

    d = resolver_destino("https://empresa.example/ofertas/dev", seguir=seguir)
    assert vistas == ["https://empresa.example/ofertas/dev"]
    assert d.portal == "Greenhouse" and d.automatico and d.url_final.endswith("/jobs/1")


def test_una_redireccion_a_un_portal_vetado_da_no_automatico():
    d = resolver_destino("https://lnkd.in/abc", seguir=_sin_red)
    assert d.automatico is False and "LinkedIn" in d.motivo
    d2 = resolver_destino("https://acme.example/x", seguir=lambda u: "https://www.linkedin.com/jobs/view/9")
    assert d2.automatico is False and "LinkedIn" in d2.motivo


def test_sin_portal_conocido_da_no_automatico_y_un_fallo_no_rompe():
    d = resolver_destino("https://acme.example/empleo/dev", seguir=lambda u: u)
    assert d.portal is None and d.automatico is False and d.motivo

    def roto(u):
        raise httpx.ConnectError("sin red")

    d2 = resolver_destino("https://acme.example/empleo/dev", seguir=roto)
    assert d2.portal is None and d2.automatico is False and "No se pudo" in d2.motivo
    assert resolver_destino("", seguir=_sin_red).automatico is False
    assert resolver_destino(None, seguir=_sin_red).automatico is False


def test_seguir_redireccion_solo_hace_get_y_se_detiene_ante_lo_no_publico():
    metodos = []

    def manejador(req: httpx.Request) -> httpx.Response:
        metodos.append(req.method)
        if req.url.host == "a.example":
            return httpx.Response(302, headers={"location": "https://b.example/x"})
        if req.url.host == "b.example" and req.url.path != "/final":
            return httpx.Response(301, headers={"location": "/final"})
        return httpx.Response(200, text="hola")

    publico = lambda host: ["93.184.216.34"]  # noqa: E731
    final = seguir_redireccion("https://a.example/x", transporte=httpx.MockTransport(manejador),
                               resolver=publico)
    assert final == "https://b.example/final" and set(metodos) == {"GET"} and len(metodos) == 3

    # A una dirección interna no se pide nada: se devuelve tal cual.
    interno = lambda host: ["10.0.0.5"]  # noqa: E731
    metodos.clear()
    assert seguir_redireccion("https://a.example/x", transporte=httpx.MockTransport(manejador),
                              resolver=interno) == "https://a.example/x" and metodos == []


def test_seguir_redireccion_corta_los_bucles():
    def bucle(req):
        return httpx.Response(302, headers={"location": str(req.url)})

    seguir_redireccion("https://a.example/x", transporte=httpx.MockTransport(bucle),
                       resolver=lambda h: ["93.184.216.34"], max_saltos=3)
