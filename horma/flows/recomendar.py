"""Flujo recomendar (RF-2.12, RF-2.14): candidatas → puntuar_tanda → (otra tanda) →
revisar_explicaciones → componer. Sin acceso a la base de datos: el worker carga las candidatas con
`buscar_ofertas` y guarda los resultados.

Estado de entrada: {"perfil": Perfil, "preferencias": Preferencias,
"candidatas": [{"oferta_id": int, "oferta": Oferta}, ...] (ya filtradas y en orden),
"ya_puntuadas"?: [oferta_id, ...] (con nota para esta versión del perfil: no se vuelven a puntuar)}.
Estado de salida: además, "recomendaciones" ([Match]), "tandas" y "quedan_sin_puntuar".

Se puntúa por tandas de 30 en el orden recibido. Se pide otra tanda solo si la anterior dejó alguna
nota dentro del rango de la usuaria y quedan candidatas, con tope de 5 tandas (coste, RT-14)."""
from horma.agents.matcher.agent import Matcher
from horma.agents.matcher.schemas import MAX_OFERTAS, EntradaMatcher, OfertaCandidata
from horma.flows.plain import PlainFlow
from horma.llm.proveedor import Proveedor
from horma.schemas.match import Match
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias
from horma.tools.rasgos_personales import rasgos_personales

TANDA = MAX_OFERTAS
MAX_TANDAS = 5


def crear(proveedor: Proveedor | None = None) -> PlainFlow:

    def candidatas(e: dict) -> dict:
        ya = set(e.get("ya_puntuadas") or [])
        vistas: set[int] = set()
        pendientes = []
        for c in e["candidatas"]:
            if c["oferta_id"] not in ya and c["oferta_id"] not in vistas:
                vistas.add(c["oferta_id"])
                pendientes.append(c)
        e.update(pendientes=pendientes, matches=[], tandas=0, en_rango=False)
        return e

    def puntuar_tanda(e: dict) -> dict:
        lote, e["pendientes"] = e["pendientes"][:TANDA], e["pendientes"][TANDA:]
        prefs = Preferencias.model_validate(e["preferencias"])
        perfil = Perfil.model_validate(e["perfil"]).model_copy(update={"instrucciones_embebidas": []})
        r = Matcher.run(EntradaMatcher(
            perfil=perfil, condiciones=prefs,
            ofertas=[OfertaCandidata.model_validate(c) for c in lote]), proveedor=proveedor)
        pedidas = {c["oferta_id"] for c in lote}
        hechas = {m["oferta_id"] for m in e["matches"]}
        nuevas = []
        for m in r.matches:
            if m.oferta_id in pedidas and m.oferta_id not in hechas:  # sin ids inventados ni repetidos
                hechas.add(m.oferta_id)
                nuevas.append(m.model_dump(mode="json"))
        e["matches"] += nuevas
        e["tandas"] += 1
        e["en_rango"] = any(prefs.rango_min <= m["nota"] <= prefs.rango_max for m in nuevas)
        return e

    def revisar_explicaciones(e: dict) -> dict:
        """RT-09: una explicación que menciona un rasgo personal se retira y se marca."""
        for m in e["matches"]:
            if rasgos_personales(" ".join([m["explicacion"], m["cita_perfil"], m["cita_oferta"]])):
                m.update(explicacion="", cita_perfil="", cita_oferta="", retirada=True)
        return e

    def componer(e: dict) -> dict:
        e["recomendaciones"] = [Match.model_validate(m).model_dump(mode="json") for m in e["matches"]]
        e["quedan_sin_puntuar"] = len(e["pendientes"])
        return e

    def tras_candidatas(e: dict) -> str:
        return "puntuar_tanda" if e["pendientes"] else "componer"

    def tras_tanda(e: dict) -> str:
        otra = e["pendientes"] and e["en_rango"] and e["tandas"] < MAX_TANDAS
        return "puntuar_tanda" if otra else "revisar_explicaciones"

    pasos = {"candidatas": candidatas, "puntuar_tanda": puntuar_tanda,
             "revisar_explicaciones": revisar_explicaciones, "componer": componer}
    aristas = {"candidatas": tras_candidatas, "puntuar_tanda": tras_tanda,
               "revisar_explicaciones": "componer"}
    return PlainFlow("recomendar", pasos=pasos, aristas=aristas, inicio="candidatas",
                     finales={"componer"})
