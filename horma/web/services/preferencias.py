"""Preferencias de búsqueda y contadores de las casillas (RF-2.8, RF-2.8b)."""
from sqlalchemy import Engine

from horma.schemas.preferencias import GRUPOS_CON_ORIGEN, Preferencias
from horma.web.db import sesion_de
from horma.web.repositories import ofertas as repo_ofertas
from horma.web.repositories import perfiles


def ver(engine: Engine, usuaria_id: int) -> Preferencias:
    with sesion_de(engine, usuaria_id) as s:
        return perfiles.preferencias(s)


def guardar(engine: Engine, usuaria_id: int, nuevas: Preferencias) -> Preferencias:
    """Lo que ella cambia pasa a ser suyo: el origen de ese grupo es «usuaria» y el CV ya no lo pisa."""
    with sesion_de(engine, usuaria_id) as s:
        actual = perfiles.preferencias(s)
        origen = dict(actual.origen)
        for grupo in GRUPOS_CON_ORIGEN:
            if getattr(nuevas, grupo) != getattr(actual, grupo):
                origen[grupo] = "usuaria"
        # Los puestos sugeridos salen del CV: ella marca o quita, no los reescribe.
        nuevas = nuevas.model_copy(update={"origen": origen, "puestos_sugeridos": actual.puestos_sugeridos})
        perfiles.guardar_preferencias(s, usuaria_id, nuevas)
    return nuevas


def titulos(engine: Engine, usuaria_id: int, q: str) -> list[str]:
    """Títulos reales de las ofertas que contienen lo escrito."""
    with sesion_de(engine, usuaria_id) as s:
        return repo_ofertas.titulos_que_contienen(s, q[:80])


def _puestos_con_cuenta(s, prefs: Preferencias) -> list[dict]:
    """Los sugeridos (con el dato que los justifica) y los que escribió ella, con cuántas ofertas casan."""
    dato = {p.titulo: p.dato for p in prefs.puestos_sugeridos}
    titulos = list(dict.fromkeys([*dato, *prefs.puestos]))
    fila = perfiles.vigente(s)
    cuentas = repo_ofertas.contar_por_puesto(s, titulos, fila and fila["familia"])
    return [{"valor": t, "dato": dato.get(t), "n": cuentas.get(t, 0), "marcado": t in prefs.puestos}
            for t in titulos]


def contadores(engine: Engine, usuaria_id: int) -> tuple[int, dict, list[dict]]:
    """(total de ofertas recomendables, cuentas por casilla, puestos con su cuenta)."""
    with sesion_de(engine, usuaria_id) as s:
        total, cuentas = repo_ofertas.contadores(s)
    with sesion_de(engine, usuaria_id) as s:
        puestos = _puestos_con_cuenta(s, perfiles.preferencias(s))
    return total, cuentas, puestos
