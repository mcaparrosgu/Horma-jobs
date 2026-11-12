"""Flujo calificar_fuente (RF-1.7): regla_exclusion → descargar → auditar → robots → decidir.

Estado de entrada: {"url": str, "condiciones_url"?: str, "condiciones"?: str, "robots"?: str|None}.
Si "condiciones" y "robots" vienen en la entrada, no se descarga nada (evals y consola).
Estado de salida: además, "calificacion" (CalificacionFuente).
"""
from horma.agents.auditor_fuentes.agent import AuditorFuentes
from horma.agents.auditor_fuentes.schemas import EntradaAuditorFuentes, SalidaAuditorFuentes
from horma.flows.plain import PlainFlow
from horma.llm.proveedor import Proveedor
from horma.schemas.fuente import CalificacionFuente
from horma.tools import descargar as desc
from horma.tools import dominio, origen_oferta, robots
from horma.tools.normalizar import html_a_texto

MAX_CONDICIONES = 40000


def crear(proveedor: Proveedor | None = None,
          descargador: desc.Descargador = desc.descargar_http) -> PlainFlow:

    def regla_exclusion(e: dict) -> dict:
        if (portal := dominio.excluida_por_regla(e["url"])):
            e["calificacion"] = CalificacionFuente(
                url=e["url"], apta=False, excluida_por_regla=True,
                motivos=[f"Excluida por regla: {portal} nunca se usa como fuente."],
            ).model_dump(mode="json")
        return e

    def descargar(e: dict) -> dict:
        if "condiciones" not in e:
            destino = e.get("condiciones_url")
            if not destino:
                destino = desc.enlace_condiciones(descargador(e["url"]), e["url"])
            e["condiciones_url"] = destino
            e["condiciones"] = html_a_texto(descargador(destino))[:MAX_CONDICIONES] if destino else ""
        if "robots" not in e:
            try:
                e["robots"] = descargador(desc.url_robots(e["url"]))
            except desc.NoEncontrada:
                e["robots"] = ""  # sin robots.txt: no hay restricciones
            except Exception:  # noqa: BLE001 - no se pudo leer: queda como desconocido
                e["robots"] = None
        return e

    def auditar(e: dict) -> dict:
        if not e["condiciones"].strip():
            e["auditoria_modelo"] = {"permite_uso_automatizado": None, "requiere_clave": False,
                                     "motivos": ["No se encontraron las condiciones de uso."]}
            return e
        r = AuditorFuentes.run(EntradaAuditorFuentes(url=e["url"], condiciones=e["condiciones"],
                                                     robots=e["robots"]), proveedor=proveedor)
        e["auditoria_modelo"] = r.model_dump(mode="json")
        return e

    def comprobar_robots(e: dict) -> dict:
        e["robots_permite"] = robots.permite(e["robots"], e["url"])
        return e

    def decidir(e: dict) -> dict:
        if "calificacion" in e:  # excluida por regla
            return e
        m = SalidaAuditorFuentes.model_validate(e["auditoria_modelo"])
        citas, _ = origen_oferta.literales(e["condiciones"], m.citas, "citas")
        instr, _ = origen_oferta.literales(e["condiciones"] + "\n" + (e["robots"] or ""),
                                           m.instrucciones_embebidas, "instrucciones")
        motivos = list(m.motivos)
        if e["robots_permite"] is False:
            motivos.append("El robots.txt no permite el acceso automático a esta URL.")
        elif e["robots_permite"] is None:
            motivos.append("No se pudo leer el robots.txt.")
        e["calificacion"] = CalificacionFuente(
            url=e["url"], apta=m.permite_uso_automatizado is True and e["robots_permite"] is True,
            permite_uso_automatizado=m.permite_uso_automatizado, robots_permite=e["robots_permite"],
            requiere_clave=m.requiere_clave, motivos=motivos, citas=citas,
            instrucciones_embebidas=instr,
        ).model_dump(mode="json")
        return e

    pasos = {"regla_exclusion": regla_exclusion, "descargar": descargar, "auditar": auditar,
             "robots": comprobar_robots, "decidir": decidir}
    aristas = {"regla_exclusion": lambda e: "decidir" if "calificacion" in e else "descargar",
               "descargar": "auditar", "auditar": "robots", "robots": "decidir"}
    return PlainFlow("calificar_fuente", pasos=pasos, aristas=aristas, inicio="regla_exclusion",
                     finales={"decidir"})
