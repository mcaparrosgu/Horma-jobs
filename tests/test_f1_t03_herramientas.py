"""Fase 1 · T03: herramientas deterministas (origen, dominio, robots, normalizar, descargar)."""
from horma.schemas.oferta import OfertaExtraida
from horma.tools import descargar, dominio, normalizar, origen_oferta, robots

TEXTO = "Camarera en Bar Sol, Valencia.\nEscribe a empleo@barsol.es\nSalario: 1.200 euros al mes."


# --- origen ------------------------------------------------------------------------------------
def test_con_origen_descarta_lo_que_no_esta_en_el_texto():
    o = OfertaExtraida(titulo="Camarera", empresa="Inventada SA", ubicacion="Valencia")
    limpia, origenes = origen_oferta.con_origen(TEXTO, o)
    assert limpia.empresa is None and limpia.ubicacion == "Valencia"
    assert ("ubicacion", "Camarera en Bar Sol, Valencia.") in origenes


def test_literales_filtra_y_da_la_linea():
    conservados, origenes = origen_oferta.literales(TEXTO, ["empleo@barsol.es", "inventado"], "x")
    assert conservados == ["empleo@barsol.es"] and origenes == [("x", "Escribe a empleo@barsol.es")]


# --- dominio -----------------------------------------------------------------------------------
def test_normalizar_dominio():
    assert dominio.normalizar("empleo@BarSol.es") == "barsol.es"
    assert dominio.normalizar("https://www.barsol.es/empleo") == "barsol.es"
    assert dominio.normalizar("no es un dominio") is None


def test_comprobar_dominio_con_resolvedor_inyectado():
    assert dominio.comprobar("barsol.es", resolver=lambda d: True) is True
    assert dominio.comprobar("barsol.es", resolver=lambda d: False) is False
    assert dominio.comprobar("gmail.com", resolver=lambda d: True) is False  # correo gratuito
    assert dominio.comprobar(None, resolver=lambda d: True) is None


def test_exclusion_por_regla_de_linkedin_e_indeed():
    assert dominio.excluida_por_regla("https://es.linkedin.com/jobs") == "LinkedIn"
    assert dominio.excluida_por_regla("https://www.indeed.es") == "Indeed"
    assert dominio.excluida_por_regla("https://es.indeed.com/ofertas") == "Indeed"
    assert dominio.excluida_por_regla("https://www.arbeitnow.com") is None


def test_dominio_registrable():
    assert dominio.registrable("https://api.arbeitnow.com/x") == "arbeitnow.com"
    assert dominio.registrable("https://www.empresa.co.uk") == "empresa.co.uk"


# --- robots ------------------------------------------------------------------------------------
def test_robots():
    assert robots.permite("User-agent: *\nDisallow: /", "https://x.test/empleo") is False
    assert robots.permite("User-agent: *\nDisallow: /privado", "https://x.test/empleo") is True
    assert robots.permite("", "https://x.test/") is True  # sin robots.txt = sin restricciones
    assert robots.permite(None, "https://x.test/") is None  # no se pudo leer


# --- normalizar --------------------------------------------------------------------------------
MAPEO = {"lista": "data", "id": "slug", "titulo": "title", "empresa": "company.name",
         "ubicacion": "location", "remoto": "remote", "fecha": "created_at", "url": "url",
         "descripcion": "description"}
RESPUESTA = {"data": [{"slug": "dev-1", "title": "Backend Developer", "company": {"name": "Acme"},
                       "location": "Berlin", "remote": True, "created_at": 1767225600,
                       "url": "https://x.test/dev-1",
                       "description": "<p>Python &amp; <b>SQL</b></p><script>x()</script>"}]}


def test_normalizar_oferta_a_texto_crudo():
    items = normalizar.items(RESPUESTA, MAPEO)
    n = normalizar.oferta_a_texto(items[0], MAPEO)
    assert n.id_externo == "dev-1" and n.url == "https://x.test/dev-1"
    assert n.texto.splitlines()[0] == "Backend Developer"
    assert "Empresa: Acme" in n.texto and "Remoto: sí" in n.texto
    assert "Publicada: 2026-01-01" in n.texto
    assert "Python & SQL" in n.texto and "<" not in n.texto and "x()" not in n.texto


def test_huella_ignora_mayusculas_y_espacios():
    assert normalizar.huella("Hola  Mundo\n") == normalizar.huella("hola mundo")
    assert normalizar.huella("a") != normalizar.huella("b")


def test_html_a_texto_y_enlace_de_condiciones():
    html = ('<a href="/precios">Precios</a><a href="/legal/terminos">Términos y condiciones</a>'
            '<a href="/impressum">Impressum</a>')
    assert descargar.enlace_condiciones(html, "https://x.test/") == "https://x.test/legal/terminos"
    assert descargar.enlace_condiciones("<p>nada</p>", "https://x.test/") is None
    assert normalizar.html_a_texto("<h1>Uno</h1><p>dos &lt;3</p>") == "Uno\ndos <3"
