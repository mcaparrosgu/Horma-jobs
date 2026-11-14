"""Flujo generar_cv_base (RF-2.9): elegir_destinos → generar → verificar → (reintento) →
cerrar_destino → … → componer. Sin acceso a la base de datos.

Estado de entrada: {"perfil": Perfil, "cv_maestro": str, "preferencias"?: Preferencias}.
Estado de salida: además, "cv_base" = {"guardados": [{destino, contenido, traza, intentos}],
"rechazados": [{destino, motivo, errores}]}.

Hasta 4 destinos (sector y familia) de la taxonomía del perfil y de las preferencias. Cada CV se
genera como máximo 2 veces: el segundo intento recibe los errores del primero. Un CV que no pasa
`verificar_trazabilidad` no se guarda y deja el motivo (RT-08)."""
from horma.agents.generador_cv_base.agent import GeneradorCvBase
from horma.agents.generador_cv_base.schemas import Destino, EntradaGeneradorCvBase
from horma.flows.plain import PlainFlow
from horma.llm.proveedor import Proveedor
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias
from horma.tools.verificar_trazabilidad import verificar_trazabilidad

MAX_DESTINOS = 4
MAX_INTENTOS = 2


def crear(proveedor: Proveedor | None = None) -> PlainFlow:

    def elegir_destinos(e: dict) -> dict:
        perfil = Perfil.model_validate(e["perfil"])
        prefs = Preferencias.model_validate(e.get("preferencias") or {})
        tax = perfil.taxonomia
        sector = tax.sector if tax else "otros"
        familia = tax.familia if tax else "otros"
        candidatos = ([(sector, familia)] if tax else [])
        candidatos += [(sector, f) for f in prefs.familias]
        candidatos += [(s, familia) for s in prefs.sectores]
        destinos = list(dict.fromkeys(candidatos))[:MAX_DESTINOS]
        if not destinos:
            raise ValueError("el perfil no tiene taxonomía ni hay preferencias: no hay destino")
        e.update(destinos=[Destino(sector=s, familia=f).model_dump(mode="json") for s, f in destinos],
                 indice=0, intento=0, errores=[], guardados=[], rechazados=[])
        return e

    def generar(e: dict) -> dict:
        e["intento"] += 1
        r = GeneradorCvBase.run(EntradaGeneradorCvBase(
            cv_maestro=e["cv_maestro"], perfil=Perfil.model_validate(e["perfil"]).model_copy(
                update={"instrucciones_embebidas": []}),
            destino=Destino.model_validate(e["destinos"][e["indice"]]),
            errores_previos=e["errores"]), proveedor=proveedor)
        e["borrador"] = r.model_dump(mode="json")
        return e

    def verificar(e: dict) -> dict:
        b = e["borrador"]
        e["errores"] = verificar_trazabilidad(b["contenido"], b["traza"], e["cv_maestro"])
        return e

    def cerrar_destino(e: dict) -> dict:
        destino, b = e["destinos"][e["indice"]], e.pop("borrador")
        if e["errores"]:
            e["rechazados"].append({"destino": destino, "motivo": " | ".join(e["errores"]),
                                    "errores": e["errores"]})
        else:
            e["guardados"].append({"destino": destino, "contenido": b["contenido"],
                                   "traza": b["traza"], "intentos": e["intento"]})
        e.update(indice=e["indice"] + 1, intento=0, errores=[])
        return e

    def componer(e: dict) -> dict:
        e["cv_base"] = {"guardados": e["guardados"], "rechazados": e["rechazados"]}
        return e

    def tras_verificar(e: dict) -> str:
        return "generar" if e["errores"] and e["intento"] < MAX_INTENTOS else "cerrar_destino"

    def tras_cerrar(e: dict) -> str:
        return "generar" if e["indice"] < len(e["destinos"]) else "componer"

    pasos = {"elegir_destinos": elegir_destinos, "generar": generar, "verificar": verificar,
             "cerrar_destino": cerrar_destino, "componer": componer}
    aristas = {"elegir_destinos": "generar", "generar": "verificar", "verificar": tras_verificar,
               "cerrar_destino": tras_cerrar}
    return PlainFlow("generar_cv_base", pasos=pasos, aristas=aristas, inicio="elegir_destinos",
                     finales={"componer"})
