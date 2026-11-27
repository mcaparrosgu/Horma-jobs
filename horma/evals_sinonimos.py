"""Set `sinonimos-puestos` (spec 012, RF-12.4e; D-068 y D-071): las otras formas que da el modelo de cada
puesto. Lo usa `horma.evals`.

`entrada.json`: {puesto}. `esperado.json`: {titulos, otros_puestos, etiquetas}. `titulos` y
`otros_puestos` salen de los pares firmados por Mar (`tests/fixtures/titulos_puestos.json`): anuncios que
son de ese puesto y que el texto solo no encuentra, y anuncios de otro puesto. `etiquetas`: {forma:
«mismo» | «otro»}, para las formas que ya ha dado el modelo.

Se mide solo lo que da el modelo, sin la tabla fija. Una forma es otro puesto si está etiquetada así o si
trae un anuncio de `otros_puestos`; el máximo es 0. La cobertura es la parte de `titulos` que encuentran
sus formas (mínimo 0,55). Una forma sin etiqueta no deja aprobar."""
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from horma.agents.sinonimos_puestos.agent import SinonimosPuestos
from horma.agents.sinonimos_puestos.schemas import EntradaSinonimos
from horma.llm.proveedor import Proveedor
from horma.tools.normalizar_titulo import canonico, normalizar_titulo, variantes_genero

CAMPOS = ["otro_puesto", "etiquetado"]


class EsperadoSinonimos(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulos: list[str] = Field(min_length=1)
    otros_puestos: list[str] = Field(default_factory=list)
    etiquetas: dict[str, Literal["mismo", "otro"]] = Field(default_factory=dict)


def entrada(caso: Path) -> dict:
    return json.loads((caso / "entrada.json").read_text(encoding="utf-8"))


def correr(estado: dict, prov: Proveedor | None) -> dict:
    r = SinonimosPuestos.run(EntradaSinonimos(puestos=[estado["puesto"]]), proveedor=prov)
    formas = [f.strip() for p in r.puestos if canonico(p.puesto) == canonico(estado["puesto"])
              for f in p.otras if f.strip()]
    return {"puesto": estado["puesto"], "formas": formas, "respuestas": {"base": r.model_dump(mode="json")}}


def _encuentra(formas: list[str], titulo: str) -> bool:
    """La misma regla que la búsqueda: la forma (o su otro género) sale como frase en el anuncio."""
    t = f" {normalizar_titulo(titulo)} "
    return any(f" {v} " in t for f in formas for v in variantes_genero(normalizar_titulo(f)))


def _etiqueta(forma: str, esperado: dict) -> str | None:
    por_forma = {canonico(f): e for f, e in esperado["etiquetas"].items()}
    de_siempre = {canonico(t): "mismo" for t in esperado["titulos"]}
    if any(_encuentra([forma], t) for t in esperado["otros_puestos"]):
        return "otro"
    return por_forma.get(canonico(forma)) or de_siempre.get(canonico(forma))


def _nuevas(obtenido: dict) -> list[str]:
    """Las formas que no son el propio puesto."""
    return [f for f in obtenido["formas"] if canonico(f) != canonico(obtenido["puesto"])]


def comparar(obtenido: dict, esperado: dict) -> list[str]:
    etiquetas = [_etiqueta(f, esperado) for f in _nuevas(obtenido)]
    return [campo for campo, mal in (("otro_puesto", "otro" in etiquetas), ("etiquetado", None in etiquetas))
            if mal]


def medir(casos: list[tuple[str, dict, dict]]) -> dict:
    otros = encontrados = titulos = 0
    sin_etiquetar: list[str] = []
    for nombre, o, e in casos:
        for forma in _nuevas(o):
            etiqueta = _etiqueta(forma, e)
            otros += etiqueta == "otro"
            if etiqueta is None:
                sin_etiquetar.append(f"{nombre}: {forma}")
        titulos += len(e["titulos"])
        encontrados += sum(_encuentra([o["puesto"], *o["formas"]], t) for t in e["titulos"])
    return {"otros": otros, "cobertura": round(encontrados / titulos, 4) if titulos else None,
            "sin_etiquetar": sin_etiquetar}


def cumple(metricas: dict, umbrales: dict) -> bool:
    return (not metricas["sin_etiquetar"] and metricas["otros"] <= umbrales["otros"]
            and (metricas["cobertura"] is None or metricas["cobertura"] >= umbrales["cobertura"]))


def simuladas(esperado: EsperadoSinonimos, datos: dict) -> list[dict]:
    """Un modelo que da justo los anuncios firmados como formas del puesto."""
    return [{"puestos": [{"puesto": datos["puesto"], "otras": esperado.titulos}]}]
