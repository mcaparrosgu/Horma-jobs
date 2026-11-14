"""Fase 2 · T04: normalizar_oferta (país, contrato, idiomas, sueldo anual) y rasgos_personales."""
import pytest

from horma.schemas.oferta import OfertaExtraida, Salario
from horma.tools.normalizar_oferta import normalizar_oferta
from horma.tools.rasgos_personales import rasgos_personales


def _o(**campos):
    return OfertaExtraida(titulo="Puesto", **campos)


# --- país --------------------------------------------------------------------------------------
@pytest.mark.parametrize("ubicacion, remoto, esperado", [
    ("Berlin, Germany", None, "DE"),
    ("Valencia", False, "ES"),
    ("Madrid, España", None, "ES"),
    ("München", None, "DE"),
    ("Lisboa, Portugal", None, "PT"),
    ("London", None, "GB"),
    ("Remote", True, "REMOTO"),
    ("Worldwide", True, "REMOTO"),
    ("Remote (Spain)", True, "ES"),
    (None, True, "REMOTO"),
    (None, None, None),
    ("Algún sitio raro", None, None),
])
def test_pais(ubicacion, remoto, esperado):
    assert normalizar_oferta(_o(ubicacion=ubicacion, remoto=remoto)).pais == esperado


# --- contrato ----------------------------------------------------------------------------------
@pytest.mark.parametrize("contrato, esperado", [
    ("Contrato indefinido", "indefinido"),
    ("Permanent", "indefinido"),
    ("Temporal", "temporal"),
    ("Contrato de obra y servicio determinado", "temporal"),
    ("Full-time", "jornada_completa"),
    ("Vollzeit", "jornada_completa"),
    ("Jornada completa", "jornada_completa"),
    ("Part-time", "media_jornada"),
    ("Media jornada", "media_jornada"),
    ("Internship", "practicas"),
    ("Prácticas", "practicas"),
    ("Freelance", "freelance"),
    ("Contrato indefinido a jornada completa", "indefinido"),
    ("Algo desconocido", "otro"),
    (None, None),
    ("", None),
])
def test_contrato(contrato, esperado):
    assert normalizar_oferta(_o(contrato=contrato)).tipo_contrato == esperado


# --- idiomas -----------------------------------------------------------------------------------
def test_idiomas_a_codigos_iso():
    n = normalizar_oferta(_o(idiomas=["Inglés B2", "Deutsch", "français", "English", "Español nativo"]))
    assert n.idiomas == ["en", "de", "fr", "es"]  # sin duplicados y en orden de aparición


def test_idiomas_desconocidos_se_ignoran_y_los_de_fuera_de_lista_son_otro():
    n = normalizar_oferta(_o(idiomas=["Klingon", "Japonés"]))
    assert n.idiomas == ["otro"]
    assert normalizar_oferta(_o()).idiomas == []


# --- sueldo anual en euros ---------------------------------------------------------------------
def test_sueldo_anual_se_deja_como_esta():
    n = normalizar_oferta(_o(salario=Salario(minimo=35000, maximo=40000, moneda="EUR")))
    assert (n.salario_anual_eur_min, n.salario_anual_eur_max) == (35000, 40000)


def test_sueldo_mensual_se_multiplica_por_12_por_el_texto():
    o = _o(salario=Salario(minimo=2000, moneda="EUR"))
    n = normalizar_oferta(o, texto="Salario: 2.000 €/mes brutos")
    assert n.salario_anual_eur_min == 24000 and n.salario_anual_eur_max is None


def test_sueldo_mensual_por_magnitud_si_el_texto_no_dice_nada():
    n = normalizar_oferta(_o(salario=Salario(minimo=1800, maximo=2200, moneda="EUR")))
    assert (n.salario_anual_eur_min, n.salario_anual_eur_max) == (21600, 26400)


def test_el_texto_manda_sobre_la_magnitud():
    o = _o(salario=Salario(minimo=3000, moneda="EUR"))
    assert normalizar_oferta(o, texto="3.000 euros anuales").salario_anual_eur_min == 3000


def test_sueldo_por_hora_otra_moneda_o_sin_dato_no_es_comparable():
    assert normalizar_oferta(_o(salario=Salario(minimo=15, moneda="EUR"))).salario_anual_eur_min is None
    assert normalizar_oferta(
        _o(salario=Salario(minimo=20000, moneda="EUR")), texto="12 €/hora").salario_anual_eur_min is None
    assert normalizar_oferta(_o(salario=Salario(minimo=60000, moneda="USD"))).salario_anual_eur_min is None
    assert normalizar_oferta(_o(salario=Salario(minimo=30000))).salario_anual_eur_min is None
    assert normalizar_oferta(_o()).salario_anual_eur_min is None


def test_moneda_en_simbolo_o_palabra():
    for moneda in ("€", "euros", "eur", "EUR"):
        n = normalizar_oferta(_o(salario=Salario(minimo=30000, moneda=moneda)))
        assert n.salario_anual_eur_min == 30000, moneda


# --- rasgos personales (RT-09) -----------------------------------------------------------------
@pytest.mark.parametrize("texto", [
    "Lleva tres años de experiencia como camarera.",
    "La oferta pide 2 años de experiencia en sala.",
    "Trabajó 5 años en un Centro de Salud como administrativa.",
    "Perfil senior con inglés B2.",
    "Su formación en hostelería encaja con el puesto.",
    "",
])
def test_sin_rasgos_personales(texto):
    assert rasgos_personales(texto) == []


@pytest.mark.parametrize("texto, categoria", [
    ("Tiene 35 años y mucha experiencia.", "edad"),
    ("Es mayor de 45 años.", "edad"),
    ("Fecha de nacimiento: 12/03/1990", "edad"),
    ("Una candidata joven y dinámica.", "edad"),
    ("Nacionalidad: española", "nacionalidad"),
    ("Al ser extranjera necesitará permiso.", "nacionalidad"),
    ("Es una mujer con experiencia en sala.", "sexo"),
    ("Está casada y tiene hijos.", "familia"),
    ("Estado civil: soltera", "familia"),
    ("Padece una discapacidad reconocida.", "salud"),
    ("Es católica practicante.", "religion"),
    ("Su origen étnico no importa.", "origen_etnico"),
    ("Su orientación sexual es privada.", "orientacion"),
    ("Tiene afiliación sindical.", "politica_sindical"),
])
def test_detecta_rasgos_personales(texto, categoria):
    r = rasgos_personales(texto)
    assert r, texto
    assert any(x.startswith(categoria + ":") for x in r), r


def test_rasgos_ignora_mayusculas_y_tildes():
    assert rasgos_personales("NACIONALIDAD: ESPAÑOLA")
    assert rasgos_personales("nacionalidad: espanola")
