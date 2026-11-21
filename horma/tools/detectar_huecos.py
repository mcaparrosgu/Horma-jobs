"""Huecos del CV: periodos de seis meses o más sin trabajo, formación ni nada que los cubra (RF-9.1).

Código puro, sin modelo. Cuentan los intervalos de experiencias, formación, actividades y periodos
cubiertos. `AAAA` va de enero a diciembre; `AAAA-MM` es ese mes; «actual» llega hasta hoy; una entrada
sin fecha de inicio no cuenta. Se funden los solapados y se mide desde el primer inicio hasta hoy."""
import re
from dataclasses import dataclass
from datetime import date

from horma.schemas.perfil import Perfil

MESES_MINIMOS = 6
_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
          "octubre", "noviembre", "diciembre")
_FECHA = re.compile(r"^\s*(\d{4})(?:-(\d{1,2}))?\s*$")


@dataclass(frozen=True)
class Hueco:
    inicio: str  # AAAA-MM
    fin: str  # AAAA-MM
    meses: int

    @property
    def clave(self) -> str:
        return f"hueco:{self.inicio}:{self.fin}"

    @property
    def texto(self) -> str:
        return f"Entre {_largo(self.inicio)} y {_largo(self.fin)} no consta trabajo ni formación."


def _largo(aaaa_mm: str) -> str:
    a, m = aaaa_mm.split("-")
    return f"{_MESES[int(m) - 1]} de {a}"


def _indice(valor: str | None, *, fin: bool, hoy: date) -> int | None:
    """Mes como año*12+mes0, o None si no hay fecha utilizable."""
    if not valor:
        return None
    if valor.strip().casefold() in ("actual", "presente", "hoy"):
        return hoy.year * 12 + hoy.month - 1
    m = _FECHA.match(valor)
    if not m:
        return None
    año, mes = int(m.group(1)), m.group(2)
    if mes is None:
        return año * 12 + (11 if fin else 0)
    if not 1 <= int(mes) <= 12:
        return None
    return año * 12 + int(mes) - 1


def _texto(i: int) -> str:
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def _intervalos(perfil: Perfil, hoy: date) -> list[tuple[int, int]]:
    fuentes = [*perfil.experiencias, *perfil.formacion, *perfil.actividades, *perfil.periodos_cubiertos]
    salida = []
    for x in fuentes:
        ini = _indice(x.inicio, fin=False, hoy=hoy)
        if ini is None:
            continue
        fin = _indice(x.fin, fin=True, hoy=hoy) if x.fin else _indice(x.inicio, fin=True, hoy=hoy)
        if fin is None or fin < ini:
            fin = ini
        salida.append((ini, fin))
    return sorted(salida)


def detectar_huecos(perfil: Perfil, hoy: date | None = None) -> list[Hueco]:
    hoy = hoy or date.today()
    intervalos = _intervalos(perfil, hoy)
    if not intervalos:
        return []
    fundidos: list[list[int]] = []
    for ini, fin in intervalos:
        if fundidos and ini <= fundidos[-1][1] + 1:
            fundidos[-1][1] = max(fundidos[-1][1], fin)
        else:
            fundidos.append([ini, fin])
    huecos = []
    for (_, fin_a), (ini_b, _) in zip(fundidos, fundidos[1:], strict=False):
        meses = ini_b - fin_a - 1
        if meses >= MESES_MINIMOS:
            huecos.append(Hueco(_texto(fin_a + 1), _texto(ini_b - 1), meses))
    ultimo = fundidos[-1][1]
    meses = (hoy.year * 12 + hoy.month - 1) - ultimo - 1  # el mes en curso no cuenta
    if meses >= MESES_MINIMOS:
        huecos.append(Hueco(_texto(ultimo + 1), _texto(hoy.year * 12 + hoy.month - 2), meses))
    return huecos
