"""Suelos y topes de la nota del `matcher` (spec 012, RF-12.35; D-080, D-081 y D-085). Código puro, sin IA.

El modelo marca cada requisito y la relación con el puesto, y da su nota; aquí se acota. Solo cuentan las
marcas que aplican. «Pide menos de lo que tienes» no resta (D-081): ninguna regla baja la nota porque la
oferta sea de un nivel inferior. Los valores se ajustan solo sobre respuestas grabadas, de 5 en 5."""
import re
import unicodedata

from horma.schemas.match import Marca
from horma.schemas.preferencias import Preferencias
from horma.tools.nivel_pedido import por_encima
from horma.tools.normalizar_titulo import casa_con_puestos

SUELO_TODO_CUBIERTO = 90   # regla 1
SUELO_CUBIERTO_Y_PIDE_MUCHO = 95  # regla 1, con `MUCHOS_EXIGIDOS` o más (D-092)
MUCHOS_EXIGIDOS = 4
SUELO_SIN_EXIGIDOS = 80    # regla 2
SUELO_FALTA_VALORABLE = 85  # regla 3: manda sobre la 1
SUELO_TITULACION = 70      # regla 4
TOPE_SIN_LO_EXIGIDO = 30   # regla 5
TOPE_ADEMAS_LEJOS = 20     # regla 5, nivel superior u otro oficio
TOPE_SUPERIOR_Y_DISTINTO = 10  # regla 5, nivel superior y no es el mismo puesto (D-091)
OTRO_OFICIO = (30, 55)     # regla 6

_TITULACION = re.compile(r"(grado|master|licenciatura|ingenieria|diplomatura|doctorado|ciclo|bachillerato|"
                         r"fp|titulo)\b")


def _es_titulacion(requisito: str) -> bool:
    plano = unicodedata.normalize("NFKD", requisito.casefold())
    return bool(_TITULACION.match("".join(c for c in plano if not unicodedata.combining(c)).strip()))


def relacion_que_cuenta(relacion: str, titulo: str | None, prefs: Preferencias, familia_perfil: str | None,
                        familia_oferta: str | None) -> str:
    """RF-12.37 (D-085): una oferta que casa con un puesto marcado en «Qué buscas» no es de otro oficio."""
    if relacion == "otro_oficio" and casa_con_puestos(
            titulo, prefs.puestos, familia_perfil=familia_perfil, familia_oferta=familia_oferta,
            sinonimos=prefs.sinonimos):
        return "buscada"
    return relacion


def acotar_nota(nota: int, marcas: list[Marca], relacion: str, requisitos: list[str],
                nivel_oferta: str | None, nivel_perfil: str | None, con_experiencia: bool) -> int:
    exigidos = [m for m in marcas if m.tipo == "exigido"]
    cercano = relacion in ("mismo_puesto", "afin")
    todo = bool(exigidos) and all(m.cubierto == "si" for m in exigidos)
    sin_cubrir = sum(m.cubierto == "no" for m in exigidos)
    mayoria = sin_cubrir * 2 > len(exigidos)
    ninguno = not any(m.cubierto == "si" for m in exigidos)
    # D-093: una oferta sin requisitos no permite comprobar nada; solo sube si ya ha tenido ese puesto.
    if not exigidos and (relacion == "mismo_puesto" or (cercano and requisitos)):
        nota = max(nota, SUELO_SIN_EXIGIDOS)
    if cercano and todo:
        falta = any(m.tipo == "valorable" and m.cubierto == "no" for m in marcas)
        suelo = SUELO_CUBIERTO_Y_PIDE_MUCHO if len(exigidos) >= MUCHOS_EXIGIDOS else SUELO_TODO_CUBIERTO
        nota = max(nota, SUELO_FALTA_VALORABLE if falta else suelo)
    if relacion == "mismo_puesto" and not mayoria and any(
            m.cubierto == "si" and _es_titulacion(requisitos[m.requisito - 1]) for m in exigidos):
        nota = max(nota, SUELO_TITULACION)
    if mayoria or (ninguno and sin_cubrir and sin_cubrir * 2 == len(exigidos)):
        superior = por_encima(nivel_oferta, nivel_perfil)
        if superior and relacion != "mismo_puesto":
            tope = TOPE_SUPERIOR_Y_DISTINTO
        elif superior or relacion == "otro_oficio":
            tope = TOPE_ADEMAS_LEJOS
        else:
            tope = TOPE_SIN_LO_EXIGIDO
        nota = min(nota, tope)
    if relacion == "otro_oficio" and todo and con_experiencia:
        minimo, maximo = OTRO_OFICIO
        nota = min(max(nota, minimo), maximo)
    return nota
