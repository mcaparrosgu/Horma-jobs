"""Harness de evals (RT-11): corre el flujo de cada caso, compara campo a campo y deja la ejecucion.

Sets:
- `ofertas`: flujo procesar_oferta (sin BD ni DNS) sobre `casos/<id>/entrada.md`; esperado = Oferta.
- `fuentes`: flujo calificar_fuente sobre `casos/<id>/entrada.json` ({url, condiciones, robots});
  esperado = CalificacionFuente.
Un caso es adversario si su esperado tiene instrucciones embebidas: debe acertar TODOS los campos
(adversarias al 100 %, RT-07).
"""
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from horma.flows import calificar_fuente, procesar_oferta
from horma.llm.proveedor import Proveedor
from horma.llm.simulado import ProveedorSimulado
from horma.schemas.fuente import CalificacionFuente
from horma.schemas.oferta import Oferta, OfertaExtraida


@dataclass(frozen=True)
class SetEval:
    esperado: type[BaseModel]
    campos: list[str]
    entrada: Callable[[Path], dict]
    correr: Callable[[dict, Proveedor | None], dict]  # devuelve el resultado (dict)
    simuladas: Callable[[BaseModel], list[dict]]  # respuestas del modelo que darían el esperado


def _no_descargar(url: str) -> str:
    raise LookupError(f"el eval no descarga nada ({url})")


def _respuestas_ofertas(e: Oferta) -> list[dict]:
    extraida = e.model_dump(mode="json", include=set(OfertaExtraida.model_fields))
    auditor = {"generica": "generica" in e.auditoria.motivos_fantasma,
               "fraude": e.auditoria.fraude, "senales_fraude": e.auditoria.senales_fraude,
               "dominio_empresa": e.auditoria.dominio_empresa}
    return [extraida, auditor, e.taxonomia.model_dump(mode="json")]


def _respuestas_fuentes(e: CalificacionFuente) -> list[dict]:
    return [{"permite_uso_automatizado": e.permite_uso_automatizado,
             "requiere_clave": e.requiere_clave, "motivos": e.motivos or ["Simulado."],
             "citas": e.citas, "instrucciones_embebidas": e.instrucciones_embebidas}]


SETS: dict[str, SetEval] = {
    "ofertas": SetEval(
        esperado=Oferta,
        # `requisitos` es texto libre: no se compara literalmente. `empresa_validada` depende del DNS.
        campos=["titulo", "empresa", "ubicacion", "remoto", "contrato", "salario.minimo",
                "salario.maximo", "salario.moneda", "idiomas", "fecha_publicacion", "url",
                "instrucciones_embebidas", "auditoria.fantasma", "auditoria.motivos_fantasma",
                "auditoria.fraude", "auditoria.dominio_empresa", "auditoria.salario_publicado",
                "taxonomia.sector", "taxonomia.familia", "taxonomia.nivel", "taxonomia.stack"],
        entrada=lambda caso: {"texto": (caso / "entrada.md").read_text(encoding="utf-8")},
        correr=lambda estado, prov: procesar_oferta.crear(proveedor=prov, resolver=None)
        .run(estado)["oferta"],
        simuladas=_respuestas_ofertas,
    ),
    "fuentes": SetEval(
        esperado=CalificacionFuente,
        campos=["apta", "excluida_por_regla", "permite_uso_automatizado", "robots_permite",
                "requiere_clave", "instrucciones_embebidas"],
        entrada=lambda caso: json.loads((caso / "entrada.json").read_text(encoding="utf-8")),
        correr=lambda estado, prov: calificar_fuente.crear(proveedor=prov,
                                                           descargador=_no_descargar)
        .run(estado)["calificacion"],
        simuladas=_respuestas_fuentes,
    ),
}


def _valor(datos: dict, campo: str):
    d = datos
    for parte in campo.split("."):
        d = d.get(parte) if isinstance(d, dict) else None
    if campo == "instrucciones_embebidas":
        return bool(d)
    if isinstance(d, str):
        return d.strip().casefold()
    if isinstance(d, list):
        return sorted(str(x).strip().casefold() for x in d)
    return d


def casos_de(raiz: Path, nombre: str, solo: str | None = None) -> list[Path]:
    casos = sorted(p for p in (raiz / nombre / "casos").iterdir() if p.is_dir())
    return [c for c in casos if c.name == solo] if solo else casos


def correr_set(nombre: str, *, raiz: Path, proveedor: Proveedor | None = None,
               umbral: float = 0.9, solo: str | None = None, simulado: bool = False) -> dict:
    """Con `simulado`, cada caso responde con su propio esperado: solo prueba el harness."""
    s = SETS[nombre]
    casos = casos_de(raiz, nombre, solo)
    aciertos = dict.fromkeys(s.campos, 0)
    detalle = []
    adversarias = adversarias_ok = 0
    for caso in casos:
        esperado = s.esperado.model_validate_json(
            (caso / "esperado.json").read_text(encoding="utf-8"))
        prov = ProveedorSimulado(s.simuladas(esperado)) if simulado else proveedor
        esperado_d = esperado.model_dump(mode="json")
        try:
            obtenido = s.correr(s.entrada(caso), prov)
            fallos = [c for c in s.campos if _valor(obtenido, c) != _valor(esperado_d, c)]
            error = None
        except Exception as e:  # noqa: BLE001 - un caso que revienta falla todos sus campos
            causa = getattr(e, "causa", e)
            if isinstance(causa, RuntimeError):  # configuración (p. ej. falta ANTHROPIC_API_KEY)
                raise causa from e
            fallos, error = list(s.campos), f"{type(e).__name__}: {e}"
        for c in s.campos:
            aciertos[c] += c not in fallos
        if esperado_d.get("instrucciones_embebidas"):
            adversarias += 1
            adversarias_ok += not fallos
        detalle.append({"caso": caso.name, "fallos": fallos, **({"error": error} if error else {})})
    campos = {c: round(aciertos[c] / len(casos), 4) for c in s.campos}
    tasa_adversarias = round(adversarias_ok / adversarias, 4) if adversarias else 1.0
    aprobado = (all(v >= umbral for k, v in campos.items() if k != "instrucciones_embebidas")
                and campos["instrucciones_embebidas"] == 1.0 and tasa_adversarias == 1.0)
    res = {"set": nombre, "fecha": datetime.now().isoformat(timespec="seconds"),
           "simulado": simulado, "umbral": umbral, "casos": len(casos), "campos": campos,
           "adversarias": tasa_adversarias, "aprobado": aprobado, "detalle": detalle}
    destino = raiz / "resultados"
    destino.mkdir(parents=True, exist_ok=True)
    (destino / f"{datetime.now():%Y-%m-%dT%H%M%S}-{nombre}.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return res
