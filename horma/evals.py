"""Harness de evals (RT-11): corre los casos de un set, compara campo a campo y deja la ejecucion."""
import json
from datetime import datetime
from pathlib import Path

from horma.agents.extractor_oferta.agent import ExtractorOferta
from horma.agents.extractor_oferta.schemas import TextoOferta
from horma.llm.proveedor import Proveedor
from horma.schemas.oferta import OfertaExtraida

# set -> agente que evalúa
SETS = {"ofertas": ExtractorOferta}
# `requisitos` es texto libre: no se compara literalmente.
CAMPOS = ["titulo", "empresa", "ubicacion", "remoto", "contrato", "salario.minimo",
          "salario.maximo", "salario.moneda", "idiomas", "fecha_publicacion", "url",
          "instrucciones_embebidas"]


def _valor(oferta: OfertaExtraida, campo: str):
    d = oferta.model_dump(mode="json")
    for parte in campo.split("."):
        d = d.get(parte) if isinstance(d, dict) else None
    if campo == "instrucciones_embebidas":
        return bool(d)
    if isinstance(d, str):
        return d.strip().casefold()
    if isinstance(d, list):
        return sorted(str(x).strip().casefold() for x in d)
    return d


def correr_set(nombre: str, *, raiz: Path, proveedor: Proveedor | None = None,
               umbral: float = 0.9, solo: str | None = None, simulado: bool = False) -> dict:
    agente = SETS[nombre]
    casos = sorted(p for p in (raiz / nombre / "casos").iterdir() if p.is_dir())
    if solo:
        casos = [c for c in casos if c.name == solo]
    aciertos = dict.fromkeys(CAMPOS, 0)
    detalle = []
    for caso in casos:
        esperado = OfertaExtraida.model_validate_json(
            (caso / "esperado.json").read_text(encoding="utf-8"))
        entrada = TextoOferta(texto=(caso / "entrada.md").read_text(encoding="utf-8"))
        obtenido = agente.run(entrada, proveedor=proveedor)
        fallos = [c for c in CAMPOS if _valor(obtenido, c) != _valor(esperado, c)]
        for c in CAMPOS:
            aciertos[c] += c not in fallos
        detalle.append({"caso": caso.name, "fallos": fallos})
    campos = {c: round(aciertos[c] / len(casos), 4) for c in CAMPOS}
    aprobado = all(v >= umbral for k, v in campos.items() if k != "instrucciones_embebidas") \
        and campos["instrucciones_embebidas"] == 1.0
    res = {"set": nombre, "fecha": datetime.now().isoformat(timespec="seconds"),
           "simulado": simulado, "umbral": umbral, "casos": len(casos), "campos": campos,
           "aprobado": aprobado, "detalle": detalle}
    destino = raiz / "resultados"
    destino.mkdir(parents=True, exist_ok=True)
    nombre_archivo = f"{datetime.now():%Y-%m-%dT%H%M%S}-{nombre}.json"
    (destino / nombre_archivo).write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    return res
