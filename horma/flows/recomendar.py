"""Flujo recomendar (RF-2.12, RF-2.14, RF-8.7): candidatas → puntuar_tanda (con la revisión de rasgos
personales y de las citas dentro de cada tanda) → (otra tanda) → componer. El `matcher` recibe la copia
ciega del perfil y no recibe las condiciones (spec 012, RF-12.30 y 12.31). Las ofertas con una cita que no
existe se piden otra vez, una sola; si vuelven a fallar, se retira la explicación y se conserva la nota
(RF-12.19). Después el código acota cada nota
(RF-12.35). Sin acceso a la base de datos: el
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
import logging
import math
from collections.abc import Callable

from horma.agents.matcher.agent import Matcher
from horma.agents.matcher.schemas import MAX_OFERTAS, EntradaMatcher, OfertaCandidata
from horma.flows.plain import PlainFlow
from horma.llm.proveedor import Proveedor
from horma.schemas.match import SIN_COMPROBAR, Marca, Match, frase_de_franja, sin_frase_de_franja
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias
from horma.tools.acotar_nota import acotar_nota
from horma.tools.copia_ciega import copia_ciega
from horma.tools.evaluar_condiciones import evaluar_condiciones
from horma.tools.rasgos_personales import rasgos_personales
from horma.tools.verificar_citas import citas_que_no_existen

log = logging.getLogger("horma.recomendar")
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
        perfil = copia_ciega(Perfil.model_validate(e["perfil"]), con_taxonomia=True)
        lote_modelo = [OfertaCandidata.model_validate(c) for c in lote]
        r = Matcher.run(EntradaMatcher(perfil=perfil, ofertas=lote_modelo), proveedor=proveedor)
        pedidas = {c["oferta_id"] for c in lote}
        hechas = {m["oferta_id"] for m in e["matches"]}
        nuevas = []
        for m in r.matches:
            if m.oferta_id in pedidas and m.oferta_id not in hechas:  # sin ids inventados ni repetidos
                oferta = next(c.oferta for c in lote_modelo if c.oferta_id == m.oferta_id)
                if not _marcada(m, oferta):
                    continue  # queda «sin puntuar»: nunca una nota a medias (RF-12.23 y 12.34)
                hechas.add(m.oferta_id)
                # Las condiciones no las decide el modelo: se calculan con código (RF-2.12).
                m.condiciones = evaluar_condiciones(oferta, prefs)
                nuevas.append(_revisada(m.model_dump(mode="json")))
        _comprobar_citas(nuevas, perfil, lote_modelo, prefs, e.setdefault("citas_fallidas", {}))
        ofertas = {c.oferta_id: c.oferta for c in lote_modelo}
        for m in nuevas:
            # RF-12.35: el código acota; RF-12.18: la frase de franja, con la nota ya acotada.
            oferta = ofertas[m["oferta_id"]]
            m["nota_modelo"] = m["nota"]
            m["nota"] = acotar_nota(
                m["nota"], [Marca.model_validate(x) for x in m["marcas"]], m["relacion"], oferta.requisitos,
                oferta.taxonomia.nivel, perfil.taxonomia.nivel if perfil.taxonomia else None)
            if not m["retirada"]:
                m["explicacion"] = f"{frase_de_franja(m['nota'])} {sin_frase_de_franja(m['explicacion'])}"
        e["matches"] += nuevas
        e["tandas"] += 1
        e["en_rango"] = any(prefs.rango_min <= m["nota"] <= prefs.rango_max for m in nuevas)
        if al_tanda is not None:
            al_tanda(nuevas, e["tandas"], max(e["previstas"], e["tandas"]))
        return e

    def _marcada(m, oferta) -> bool:
        """RF-12.34: una marca por cada requisito. Un rasgo personal no aplica, lo marque como lo marque el
        modelo; las condiciones las aparta el prompt."""
        if sorted(x.requisito for x in m.marcas) != list(range(1, len(oferta.requisitos) + 1)):
            return False
        for x in m.marcas:
            if rasgos_personales(oferta.requisitos[x.requisito - 1]):
                x.tipo = "no_aplica"
        return True

    def _revisada(m: dict) -> dict:
        """RT-09: una explicación que menciona un rasgo personal se retira y se marca. Se hace en cada tanda,
        antes de entregarla: lo que se guarda nunca lleva un rasgo personal (RF-8.7c)."""
        if rasgos_personales(" ".join([m["explicacion"], m["cita_perfil"], m["cita_oferta"]])):
            m.update(explicacion="", cita_perfil="", cita_oferta="", retirada=True)
        return m

    def _comprobar_citas(nuevas: list[dict], perfil, lote: list, prefs: Preferencias,
                         fallidas: dict) -> None:
        """RF-12.19: las citas existen en la copia y en la oferta, o se piden otra vez, una sola.
        `fallidas` guarda las de cada intento solo para la traza del eval: no van a la base."""
        ofertas = {c.oferta_id: c for c in lote}
        copia = perfil.model_dump(mode="json")

        def mal(m: dict) -> bool:
            oferta = ofertas[m["oferta_id"]].oferta.model_dump(mode="json")
            falla = not m["retirada"] and bool(
                citas_que_no_existen(m["cita_perfil"], m["cita_oferta"], copia, oferta))
            if falla:
                fallidas.setdefault(m["oferta_id"], []).append(
                    {"cita_perfil": m["cita_perfil"], "cita_oferta": m["cita_oferta"]})
            return falla

        malas = {m["oferta_id"]: m for m in nuevas if mal(m)}
        if not malas:
            return
        try:
            r = Matcher.run(EntradaMatcher(perfil=perfil, ofertas=[ofertas[i] for i in malas]),
                            proveedor=proveedor)
        except Exception as error:  # noqa: BLE001 - las notas ya calculadas no se pierden (RF-12.23)
            log.warning("No se pudieron volver a pedir las citas (%s)", type(error).__name__)
        else:
            for otra in r.matches:
                if otra.oferta_id not in malas or not _marcada(otra, ofertas[otra.oferta_id].oferta):
                    continue
                otra.condiciones = evaluar_condiciones(ofertas[otra.oferta_id].oferta, prefs)
                nueva = _revisada(otra.model_dump(mode="json"))
                if not mal(nueva):
                    malas.pop(otra.oferta_id).update(nueva)
        for m in malas.values():
            m.update(explicacion=SIN_COMPROBAR, cita_perfil="", cita_oferta="", retirada=True)

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
