# ruff: noqa: F811
"""S8, T43: detectar CV o carta con reglas (RF-10.14b)."""
from pathlib import Path

import pytest

from horma.tools.clasificar_documento import clasificar_documento
from horma.tools.convertir_cv import convertir_cv

PASADA = Path(__file__).resolve().parent.parent / "pruebas-manuales" / "pasada-22nov"
SUELTOS = Path(__file__).resolve().parent.parent / "pruebas-manuales"


@pytest.mark.parametrize("ruta, tipo, esperado", [
    (PASADA / "CV-Irene-Navarro-Hosteleria.pdf", "pdf", "cv"),
    (PASADA / "CV-Irene-Navarro-Administracion.docx", "docx", "cv"),
    (PASADA / "Carta-Irene-Navarro-Levante-Frio.pdf", "pdf", "carta"),
    (SUELTOS / "cv-lucia.md", "md", "cv"),
    (SUELTOS / "carta-lucia.md", "md", "carta"),
])
def test_los_documentos_de_la_pasada_se_clasifican_bien(ruta, tipo, esperado):
    if not ruta.exists():   # carpeta gitignorada: solo está en el equipo de Mar
        pytest.skip("documento de prueba local no disponible")
    assert clasificar_documento(convertir_cv(ruta.read_bytes(), tipo)) == esperado


CV = """Lucía Ferrer
EXPERIENCIA
Camarera en Bar Sol, Valencia, 2021-2024
Ayudante de cocina en La Barca, Valencia, 2019-2021
FORMACIÓN
Técnico en Restauración, IES Ausiàs March, 2017-2019
IDIOMAS
Inglés B1
"""
CARTA = """Hola equipo de La Marina:
Os escribo por el puesto de camarera de sala. Llevo tres años en Bar Sol, en Valencia, y casi todos los \
turnos eran de fin de semana.
En ese tiempo aprendí a cobrar rápido y a avisar a cocina antes de que se acumule el problema, y me \
gustaría seguir aprendiendo.
Un saludo,
Lucía
"""


def test_un_cv_y_una_carta_sinteticos():
    assert clasificar_documento(CV) == "cv"
    assert clasificar_documento(CARTA) == "carta"


@pytest.mark.parametrize("texto", [
    "",
    "Notas de la reunión del lunes\nHablamos del presupuesto\nQueda pendiente revisar los plazos",
    "Lucía Ferrer\nCamarera con experiencia en sala\nDisponible para empezar ya",
    # saludo y periodos con fechas a la vez: no se puede decir
    "Hola equipo:\nAdjunto mi trayectoria: camarera en Bar Sol, 2021-2024 y ayudante, 2019-2021.\n"
    "Experiencia en sala.",
])
def test_un_texto_ambiguo_da_duda(texto):
    assert clasificar_documento(texto) == "duda"


# --- subida y cambio de clase por la API --------------------------------------------------------------
from sqlalchemy import text  # noqa: E402

from tests.test_f2_t15_t19_api import app, archivos, entrar  # noqa: E402,F401  (fixtures y ayudante)


def _subir(c, h, texto: str, nombre="doc.md", **datos):
    return c.post("/api/cv", headers=h, files={"archivo": (nombre, texto.encode())}, data=datos)


def _clase(motor, cv_id):
    with motor.connect() as c:
        return c.execute(text("select clase from cv_archivos where id=:i"), {"i": cv_id}).scalar_one()


@pytest.mark.bd
def test_subir_sin_clase_detecta_y_si_duda_no_guarda(app, motor_migrador):
    c, h, _ = entrar(app)
    r = _subir(c, h, CV)
    assert r.status_code == 201 and r.json()["clase"] == "fuente" and r.json()["perfil_id"]
    r = _subir(c, h, CARTA, nombre="carta.md")
    assert r.status_code == 201 and r.json()["clase"] == "carta" and r.json()["perfil_id"] is None
    r = _subir(c, h, "Notas\nde la reunión\ndel lunes", nombre="otro.md")
    assert r.status_code == 200 and r.json() == {"duda": True}
    assert len(c.get("/api/cv").json()) == 2          # lo dudoso no se guarda
    assert _subir(c, h, "Notas\nde la reunión\ndel lunes", nombre="otro.md", clase="carta").status_code == 201


@pytest.mark.bd
def test_cambiar_la_clase_de_carta_a_cv_encola_perfilar(app, motor_migrador):
    c, h, _ = entrar(app)
    _subir(c, h, CV, nombre="cv.md")
    carta = _subir(c, h, CARTA, nombre="carta.md").json()["id"]
    with motor_migrador.connect() as cx:
        antes = cx.execute(text("select count(*) from tareas where tipo='perfilar'")).scalar_one()
    r = c.patch(f"/api/cv/{carta}/clase", json={"clase": "fuente"}, headers=h)
    assert r.status_code == 200 and _clase(motor_migrador, carta) == "fuente"
    with motor_migrador.connect() as cx:
        assert cx.execute(text("select count(*) from tareas where tipo='perfilar'")).scalar_one() == antes + 1
    assert c.patch(f"/api/cv/{carta}/clase", json={"clase": "otra"}, headers=h).status_code == 422
    assert c.patch("/api/cv/999/clase", json={"clase": "carta"}, headers=h).status_code == 404
    otra, h2, _ = entrar(app, "google-B")
    assert otra.patch(f"/api/cv/{carta}/clase", json={"clase": "carta"}, headers=h2).status_code == 404


def test_el_selector_de_clase_ya_no_esta_en_subir_archivo():
    html = (Path(__file__).resolve().parent.parent / "horma" / "web" / "static" / "perfil.html").read_text(
        encoding="utf-8")
    assert 'id="clase-doc"' not in html
