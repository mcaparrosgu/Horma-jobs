"""Regla de origen para ofertas (RT-08): solo se conserva lo que se localiza literalmente en el texto."""
import re

from horma.schemas.oferta import OfertaExtraida, Salario

Origenes = list[tuple[str, str]]  # (campo, línea del texto donde aparece)


def linea_con(texto: str, aguja: str) -> str | None:
    aguja = aguja.strip().casefold()
    if not aguja:
        return None
    for linea in texto.splitlines():
        if aguja in linea.casefold():
            return linea.strip()
    return None


def literales(texto: str, items: list[str], campo: str) -> tuple[list[str], Origenes]:
    """Los elementos que aparecen en el texto, con la línea que los respalda."""
    conservados: list[str] = []
    origenes: Origenes = []
    for item in items:
        if (linea := linea_con(texto, item)):
            conservados.append(item)
            origenes.append((campo, linea))
    return conservados, origenes


def _formas_numero(n: float) -> list[str]:
    entero = int(n) if float(n).is_integer() else n
    formas = [str(entero)]
    if isinstance(entero, int):
        formas += [f"{entero:,}".replace(",", "."), f"{entero:,}"]
    return formas


def _linea_numero(texto: str, n: float) -> str | None:
    for forma in _formas_numero(n):
        if (linea := linea_con(texto, forma)):
            return linea
    return None


def con_origen(texto: str, o: OfertaExtraida) -> tuple[OfertaExtraida, Origenes]:
    """Conserva solo los datos que se pueden localizar en el texto; el resto se descarta."""
    origenes: Origenes = []
    datos: dict = {}

    primera = next((ln.strip() for ln in texto.splitlines() if ln.strip()), texto.strip())
    datos["titulo"] = o.titulo
    origenes.append(("titulo", linea_con(texto, o.titulo) or primera))

    for campo in ("empresa", "ubicacion", "contrato", "fecha_publicacion"):
        valor = getattr(o, campo)
        if valor and (linea := linea_con(texto, valor)):
            datos[campo] = valor
            origenes.append((campo, linea))
    if o.url and (linea := linea_con(texto, str(o.url).rstrip("/"))):
        datos["url"] = o.url
        origenes.append(("url", linea))

    if o.remoto is not None:
        marca = re.search(r"remot|teletrabajo|presencial|híbrid|hibrid", texto, re.I)
        if marca and (linea := linea_con(texto, marca.group(0))):
            datos["remoto"] = o.remoto
            origenes.append(("remoto", linea))

    if o.salario:
        s = o.salario
        lmin = _linea_numero(texto, s.minimo) if s.minimo is not None else None
        lmax = _linea_numero(texto, s.maximo) if s.maximo is not None else None
        if lmin or lmax:
            datos["salario"] = Salario(minimo=s.minimo if lmin else None,
                                       maximo=s.maximo if lmax else None, moneda=s.moneda)
            if lmin:
                origenes.append(("salario_minimo", lmin))
            if lmax:
                origenes.append(("salario_maximo", lmax))
            origenes.append(("salario_moneda", lmin or lmax))

    for campo in ("idiomas", "requisitos", "instrucciones_embebidas"):
        datos[campo], o_campo = literales(texto, getattr(o, campo), campo)
        origenes += o_campo
    return OfertaExtraida(**datos), origenes
