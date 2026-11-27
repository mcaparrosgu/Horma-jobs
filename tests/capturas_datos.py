"""Datos inventados para `tests/capturas.js`. Corre dentro del contenedor `api`; no llama al modelo.
Imprime «id cookie candidatura ruta_del_pdf». Los textos son largos a propósito, para ver si desbordan."""
import base64
import json
import os

from fpdf import FPDF
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine, text

from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias
from horma.web.db import sesion_de, sesion_sin_usuaria
from horma.web.repositories import cv, matches, perfiles
from horma.web.services.cv import carpeta

CV = "## Experiencia\nCamarera de sala y barra en Bar Sol, 2020-2023\nManejo de TPV y arqueo de caja"
CARTA = "Hola equipo,\nTrabajé en Bar Sol desde 2020 atendiendo sala y barra.\nUn saludo"

motor = create_engine(os.environ["DATABASE_URL"])
with sesion_sin_usuaria(motor) as s:
    u = s.execute(text("select obtener_o_crear_usuaria('prueba-capturas')")).scalar_one()

pdf = FPDF()
for hoja in (1, 2):
    pdf.add_page()
    pdf.set_font("Helvetica", size=22)
    pdf.cell(0, 12, f"Ana Prueba - Curriculum (hoja {hoja})", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 7, "Camarera de sala y barra en Bar Sol, 2020-2023. Manejo de TPV.\n" * 8)
carpeta().mkdir(parents=True, exist_ok=True)
fichero = carpeta() / f"capturas-{u}.pdf"
fichero.write_bytes(bytes(pdf.output()))

with sesion_de(motor, u) as s:
    cv_id = cv.crear(s, u, nombre="Currículum de hostelería y atención al público 2026",
                     nombre_original="curriculum-ana-prueba-hosteleria-2026.pdf", ruta=fichero.name,
                     tipo="pdf", clase="fuente", tamano=fichero.stat().st_size, texto=CV,
                     escrito_por_ella=False)
    pid, version = perfiles.nueva_version(s, u)
    origen = {"fuente": "cv", "cv_id": cv_id, "fragmento": "Camarera de sala y barra en Bar Sol"}
    perfil = {
        "version": version,
        "taxonomia": {"sector": "hosteleria_turismo", "familia": "hosteleria_restauracion",
                      "nivel": "junior", "stack": []},
        "experiencias": [{"puesto": "Camarera de sala y barra", "empresa": "Restaurante Bar Sol de la Plaza",
                          "origen": origen}],
        "preguntas_pendientes": [{"campo": "idiomas", "motivo": "ambiguo",
                                  "pregunta": "¿Qué nivel de inglés tienes?"}],
    }
    perfiles.guardar_perfil(s, u, pid, Perfil.model_validate(perfil), "# Ana Prueba\n\n" + CV)
    perfiles.guardar_preferencias(s, u, Preferencias(
        puestos=["Camarera de sala y barra"], sinonimos={"Camarera de sala y barra": ["Waitress", "Mesera"]},
        puestos_sugeridos=[
            {"titulo": "Camarera de sala y barra", "dato": "Camarera de sala y barra", "nivel": 1,
             "tipo_dato": "puesto", "marcado": True},
            {"titulo": "Responsable de atención al cliente en establecimientos de restauración",
             "dato": "Grado Superior en Dirección de Servicios de Restauración", "tipo_dato": "titulacion"}]))
    ofertas = list(s.execute(text(
        "select id from ofertas where estado = 'procesada' order by id desc limit 6")).scalars())
    matches.guardar(s, u, version, [
        {"oferta_id": o, "nota": 88 - 9 * i, "condiciones": "medio",
         "explicacion": "Tu experiencia en sala encaja con lo que piden. Falta acreditar el inglés.",
         "cita_perfil": "Camarera de sala y barra", "cita_oferta": "camarera", "retirada": False}
        for i, o in enumerate(ofertas)])
    candidatura = 0
    for oferta in ofertas[:3]:
        candidatura = s.execute(text(
            "insert into candidaturas (usuaria_id, oferta_id, perfil_version, preparacion, cv_contenido,"
            " carta_contenido, cv_traza, carta_traza) values (:u, :o, :v, 'lista', :c, :k, '[]', '[]')"
            " returning id"), {"u": u, "o": oferta, "v": version, "c": CV, "k": CARTA}).scalar_one()

sesion = {"usuaria_id": u, "sub": "prueba-capturas", "csrf": "prueba"}
datos = base64.b64encode(json.dumps(sesion).encode())
print(u, TimestampSigner(os.environ["SESSION_SECRET"]).sign(datos).decode(), candidatura, fichero)
