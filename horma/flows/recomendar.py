"""Flujo recomendar (RF-2.12, RF-2.14, RF-8.7): candidatas → puntuar_tanda (con la revisión de rasgos
personales dentro de cada tanda) → (otra tanda) → componer. Sin acceso a la base de datos: el
worker carga las candidatas con
`buscar_ofertas` y guarda los resultados.

Estado de entrada: {"perfil": Perfil, "preferencias": Preferencias,
"candidatas": [{"oferta_id": int, "oferta": Oferta}, ...] (ya filtradas y en orden),
"ya_puntuadas"?: [oferta_id, ...] (con nota para esta versión del perfil: no se vuelven a puntuar)}.
Estado de salida: además, "recomendaciones" ([Match]), "tandas" y "quedan_sin_puntuar".

`al_tanda(nuevas, hechas, previstas)` (opcional) se llama al terminar cada tanda, con sus notas ya revisadas
(RT-09): el worker las guarda y avanza la barra (RF-8.7). Sigue sin tocar la base de datos.

Se puntúa por tandas de 30 en el orden recibido. Se pide otra tanda solo si la anterior dejó alguna
nota dentro del rango de la usuaria y quedan candidatas, con tope de 5 tandas (coste, RT-14)."""
import math
from collections.abc import Callable

from horma.agents.matcher.agent import Matcher
from horma.agents.matcher.schemas import MAX_OFERTAS, EntradaMatcher, OfertaCandidata
from horma.flows.plain import PlainFlow
from horma.llm.proveedor import Proveedor
from horma.schemas.match import Match
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias
from horma.tools.evaluar_condiciones import evaluar_condiciones
from horma.tools.rasgos_personales import rasgos_personales

TANDA = MAX_OFERTAS
MAX_TANDAS = 5


def crear(proveedor: Proveedor | None = None,
          al_tanda: Callable[[list[dict], int, int], None] | None = None) -> PlainFlow:

    def candidatas(e: dict) -> dict:
        ya = set(e.get("ya_puntuadas") or [])
        vistas: set[int] = set()
        pendientes = []
        for c in e["candidatas"]:
            if c["oferta_id"] not in ya and c["oferta_id"] not in vistas:
                vistas.add(c["oferta_id"])
                pendientes.append(c)
        previstas = min(MAX_TANDAS, math.ceil(len(pendientes) / TANDA))
        e.update(pendientes=pendientes, matches=[], tandas=0, en_rango=False, previstas=previstas)
        return e

    def puntuar_tanda(e: dict) -> dict:
        lote, e["pendientes"] = e["pendientes"][:TANDA], e["pendientes"][TANDA:]
        prefs = Preferencias.model_validate(e["preferencias"])
        perfil = Perfil.model_validate(e["perfil"]).model_copy(update={"instrucciones_embebidas": []})
        lote_modelo = [OfertaCandidata.model_validate(c) for c in lote]
        r = Matcher.run(EntradaMatcher(
            perfil=perfil, condiciones=prefs,
            ofertas=lote_modelo), proveedor=proveedor)
        pedidas = {c["oferta_id"] for c in lote}
        hechas = {m["oferta_id"] for m in e["matches"]}
        nuevas = []
        for m in r.matches:
            if m.oferta_id in pedidas and m.oferta_id not in hechas:  # sin ids inventados ni repetidos
                hechas.add(m.oferta_id)
                # Las condiciones no las decide el modelo: se calculan con código (RF-2.12).
                oferta = next(c.oferta for c in lote_modelo if c.oferta_id == m.oferta_id)
                m.condiciones = evaluar_condiciones(oferta, prefs)
                nuevas.append(_revisada(m.model_dump(mode="json")))
        e["matches"] += nuevas
        e["tandas"] += 1
        e["en_rango"] = any(prefs.rango_min <= m["nota"] <= prefs.rango_max for m in nuevas)
        if al_tanda is not None:
            al_tanda(nuevas, e["tandas"], max(e["previstas"], e["tandas"]))
        return e

    def _revisada(m: dict) -> dict:
        """RT-09: una explicación que menciona un rasgo personal se retira y se marca. Se hace en cada tanda,
        antes de entregarla: lo que se guarda nunca lleva un rasgo personal (RF-8.7c)."""
        if rasgos_personales(" ".join([m["explicacion"], m["cita_perfil"], m["cita_oferta"]])):
            m.update(explicacion="", cita_perfil="", cita_oferta="", retirada=True)
        return m

    def componer(e: dict) -> dict:
        e["recomendaciones"] = [Match.model_validate(m).model_dump(mode="json") for m in e["matches"]]
        e["quedan_sin_puntuar"] = len(e["pendientes"])
        return e

    def tras_candidatas(e: dict) -> str:
        return "puntuar_tanda" if e["pendientes"] else "componer"

    def tras_tanda(e: dict) -> str:
        otra = e["pendientes"] and e["en_rango"] and e["tandas"] < MAX_TANDAS
        return "puntuar_tanda" if otra else "componer"

    pasos = {"candidatas": candidatas, "puntuar_tanda": puntuar_tanda, "componer": componer}
    aristas = {"candidatas": tras_candidatas, "puntuar_tanda": tras_tanda}
    return PlainFlow("recomendar", pasos=pasos, aristas=aristas, inicio="candidatas",
                     finales={"componer"})
