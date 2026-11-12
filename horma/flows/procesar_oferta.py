"""Flujo procesar_oferta (RF-1.4): extraer → verificar_origen → auditar → comprobar_empresa →
clasificar → componer. Sin bucle y sin acceso a la base de datos: recibe el estado y lo devuelve.

Estado de entrada: {"texto": str, "fuente"?: str, "url"?: str, "repetida"?: bool}.
Estado de salida: además, "oferta" (Oferta completa) y "origenes" ([[campo, línea], ...]).
"""
from horma.agents.auditor_oferta.agent import AuditorOferta
from horma.agents.auditor_oferta.schemas import EntradaAuditor, SalidaAuditor
from horma.agents.clasificador_oferta.agent import ClasificadorOferta
from horma.agents.clasificador_oferta.schemas import EntradaClasificador
from horma.agents.extractor_oferta.agent import ExtractorOferta
from horma.agents.extractor_oferta.schemas import TextoOferta
from horma.flows.plain import PlainFlow
from horma.llm.proveedor import Proveedor
from horma.schemas.oferta import Auditoria, Oferta, OfertaExtraida
from horma.schemas.taxonomia import Taxonomia
from horma.tools import dominio, origen_oferta
from horma.tools.dominio import Resolvedor


def _numero(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)


def _rango(oferta: OfertaExtraida) -> str | None:
    s = oferta.salario
    if not s or (s.minimo is None and s.maximo is None):
        return None
    valores = "–".join(_numero(v) for v in (s.minimo, s.maximo) if v is not None)
    return f"{valores} {s.moneda}".strip() if s.moneda else valores


def crear(proveedor: Proveedor | None = None,
          resolver: Resolvedor | None = dominio.resuelve) -> PlainFlow:
    """`resolver=None` no comprueba el DNS (consola en simulado y evals)."""

    def extraer(e: dict) -> dict:
        bruta = ExtractorOferta.run(TextoOferta(texto=e["texto"], fuente=e.get("fuente"),
                                                url=e.get("url")), proveedor=proveedor)
        e["extraida_bruta"] = bruta.model_dump(mode="json")
        return e

    def verificar_origen(e: dict) -> dict:
        limpia, origenes = origen_oferta.con_origen(
            e["texto"], OfertaExtraida.model_validate(e["extraida_bruta"]))
        e["extraida"] = limpia.model_dump(mode="json")
        e["origenes"] = [list(o) for o in origenes]
        return e

    def auditar(e: dict) -> dict:
        r = AuditorOferta.run(EntradaAuditor(oferta=OfertaExtraida.model_validate(e["extraida"]),
                                             texto=e["texto"]), proveedor=proveedor)
        e["auditoria_modelo"] = r.model_dump(mode="json")
        return e

    def comprobar_empresa(e: dict) -> dict:
        citado = e["auditoria_modelo"].get("dominio_empresa")
        linea = origen_oferta.linea_con(e["texto"], citado) if citado else None
        e["dominio_empresa"] = dominio.normalizar(citado) if linea else None
        e["empresa_validada"] = dominio.comprobar(e["dominio_empresa"], resolver)
        if e["dominio_empresa"]:
            e["origenes"].append(["dominio_empresa", linea])
        return e

    def clasificar(e: dict) -> dict:
        oferta = OfertaExtraida.model_validate(e["extraida"]).model_copy(
            update={"instrucciones_embebidas": []})
        r = ClasificadorOferta.run(EntradaClasificador(oferta=oferta), proveedor=proveedor)
        e["taxonomia_modelo"] = r.model_dump(mode="json")
        return e

    def componer(e: dict) -> dict:
        """Lo determinista: fantasma, citas con origen, salario y la oferta completa."""
        texto = e["texto"]
        extraida = OfertaExtraida.model_validate(e["extraida"])
        modelo = SalidaAuditor.model_validate(e["auditoria_modelo"])
        tax = Taxonomia.model_validate(e["taxonomia_modelo"])

        senales, o_senales = origen_oferta.literales(texto, modelo.senales_fraude, "senales_fraude")
        instr, o_instr = origen_oferta.literales(texto, modelo.instrucciones_embebidas,
                                                 "instrucciones_embebidas")
        stack, o_stack = origen_oferta.literales(texto, tax.stack, "stack")
        motivos = [m for m, si in (("sin_fecha", not extraida.fecha_publicacion),
                                   ("repetida", bool(e.get("repetida"))),
                                   ("generica", modelo.generica)) if si]
        publicado = _rango(extraida) is not None
        auditoria = Auditoria(
            fantasma=bool(motivos), motivos_fantasma=motivos,
            fraude=modelo.fraude and bool(senales), senales_fraude=senales,
            dominio_empresa=e["dominio_empresa"], empresa_validada=e["empresa_validada"],
            salario_publicado=publicado, salario_rango=_rango(extraida),
            frase_pedir_salario=None if publicado else (
                f"¿Podríais indicarme la banda salarial prevista para el puesto de "
                f"{extraida.titulo}?"))
        todas = list(dict.fromkeys(extraida.instrucciones_embebidas + instr))
        oferta = Oferta(**extraida.model_dump(exclude={"instrucciones_embebidas"}),
                        instrucciones_embebidas=todas, auditoria=auditoria,
                        taxonomia=tax.model_copy(update={"stack": stack}))
        ya = {tuple(o) for o in e["origenes"]}
        e["origenes"] += [list(o) for o in o_senales + o_instr + o_stack if o not in ya]
        e["oferta"] = oferta.model_dump(mode="json")
        return e

    pasos = {"extraer": extraer, "verificar_origen": verificar_origen, "auditar": auditar,
             "comprobar_empresa": comprobar_empresa, "clasificar": clasificar, "componer": componer}
    aristas = {"extraer": "verificar_origen", "verificar_origen": "auditar",
               "auditar": "comprobar_empresa", "comprobar_empresa": "clasificar",
               "clasificar": "componer"}
    return PlainFlow("procesar_oferta", pasos=pasos, aristas=aristas, inicio="extraer",
                     finales={"componer"})
