"""Suelos y topes de la nota del `matcher` (spec 012, RF-12.35; D-080, D-081 y D-085). Código puro, sin IA.

El modelo marca cada requisito y la relación con el puesto, y da su nota; aquí se acota. Solo cuentan las
marcas que aplican. «Pide menos de lo que tienes» no resta (D-081): ninguna regla baja la nota porque la
oferta sea de un nivel inferior. Los valores se ajustan solo sobre respuestas grabadas, de 5 en 5."""
import re
import unicodedata

from horma.schemas.match import Marca
from horma.tools.nivel_pedido import por_encima

SUELO_TODO_CUBIERTO = 90   # regla 1
SUELO_SIN_EXIGIDOS = 80    # regla 2
SUELO_FALTA_VALORABLE = 85  # regla 3: manda sobre la 1
SUELO_TITULACION = 70      # regla 4
TOPE_SIN_LO_EXIGIDO = 30   # regla 5
TOPE_ADEMAS_LEJOS = 20     # regla 5, nivel superior u otro oficio
OTRO_OFICIO = (30, 55)     # regla 6

_TITULACION = re.compile(r"(grado|master|licenciatura|ingenieria|diplomatura|doctorado|ciclo|bachillerato|"
                         r"fp|titulo)\b")


def _es_titulacion(requisito: str) -> bool:
    plano = unicodedata.normalize("NFKD", requisito.casefold())
    return bool(_TITULACION.match("".join(c for c in plano if not unicodedata.combining(c)).strip()))


def acotar_nota(nota: int, marcas: list[Marca], relacion: str, requisitos: list[str],
                nivel_oferta: str | None, nivel_perfil: str | None) -> int:
    exigidos = [m for m in marcas if m.tipo == "exigido"]
    cercano = relacion in ("mismo_puesto", "afin")
    todo = bool(exigidos) and all(m.cubierto == "si" for m in exigidos)
    sin_cubrir = sum(m.cubierto == "no" for m in exigidos)
    if cercano and not exigidos:
        nota = max(nota, SUELO_SIN_EXIGIDOS)
    if cercano and todo:
        falta = any(m.tipo == "valorable" and m.cubierto == "no" for m in marcas)
        nota = max(nota, SUELO_FALTA_VALORABLE if falta else SUELO_TODO_CUBIERTO)
    if relacion == "mismo_puesto" and not sin_cubrir and any(
            m.cubierto == "si" and _es_titulacion(requisitos[m.requisito - 1]) for m in exigidos):
        nota = max(nota, SUELO_TITULACION)
    if sin_cubrir * 2 > len(exigidos):
        lejos = relacion == "otro_oficio" or por_encima(nivel_oferta, nivel_perfil)
        nota = min(nota, TOPE_ADEMAS_LEJOS if lejos else TOPE_SIN_LO_EXIGIDO)
    if relacion == "otro_oficio" and todo:
        minimo, maximo = OTRO_OFICIO
        nota = min(max(nota, minimo), maximo)
    return nota
