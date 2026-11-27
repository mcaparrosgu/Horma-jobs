"""Set `puestos` (spec 012, RF-12.1 a 12.3): qué puestos sugiere Horma desde un perfil y cuáles llegan
marcados. Lo usa `horma.evals`.

`entrada.json`: {perfil, variante?} (`variante`: {nombre, genero_puestos, reemplazos}, para la equidad).
`esperado.json`: {etiquetas: {puesto: {final, votos, repaso_mar}}, imprescindibles: [[formas del puesto]],
familia?}. Etiquetas: «lo_ha_sido», «afin» o «ajeno».
"""
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from horma.agents.clasificador_postulante.agent import ClasificadorPostulante
from horma.agents.clasificador_postulante.schemas import EntradaClasificadorPostulante
from horma.flows import perfilar
from horma.llm.proveedor import Proveedor
from horma.schemas.perfil import Perfil
from horma.tools.copia_ciega import copia_ciega
from horma.tools.normalizar_titulo import canonico as _canonico
from horma.tools.normalizar_titulo import casa_con_puestos
from horma.tools.puestos_del_perfil import puestos_del_perfil

Etiqueta = Literal["lo_ha_sido", "afin", "ajeno"]
CAMPOS = ["ajenos", "etiquetado", "equidad"]


class PuestoEtiquetado(BaseModel):
    model_config = ConfigDict(extra="forbid")

    final: Etiqueta
    votos: list[Etiqueta] = Field(min_length=3, max_length=3, description="Tres etiquetadores ciegos.")
    repaso_mar: bool = False


class EsperadoPuestos(BaseModel):
    model_config = ConfigDict(extra="forbid")

    etiquetas: dict[str, PuestoEtiquetado] = Field(default_factory=dict)
    imprescindibles: list[list[str]] = Field(default_factory=list)
    familia: str | None = None


def entrada(caso: Path) -> dict:
    return json.loads((caso / "entrada.json").read_text(encoding="utf-8"))


def _variante(perfil: dict, variante: dict) -> dict:
    """El mismo CV con otro nombre y otro género: solo eso cambia (RF-12.3)."""
    texto = json.dumps(perfil, ensure_ascii=False)
    for antes, despues in (variante.get("reemplazos") or {}).items():
        texto = texto.replace(antes, despues)
    return {**json.loads(texto), "nombre": variante["nombre"], "genero_puestos": variante["genero_puestos"]}


def _clasificar(perfil: dict, prov: Proveedor | None) -> dict:
    """El clasificador y, sobre su respuesta, el mismo código que usa `perfilar` para sugerir y marcar."""
    p = Perfil.model_validate(perfil)
    r = ClasificadorPostulante.run(EntradaClasificadorPostulante(perfil=copia_ciega(p)), proveedor=prov)
    sugeridos = [x.model_dump(mode="json") for x in puestos_del_perfil(p, r.puestos, r.nivel)]
    estado = perfilar.crear().run_step("preferencias_desde_cv", {
        "extraccion": {"perfil": perfil}, "puestos": sugeridos,
        "taxonomia": r.model_dump(mode="json", exclude={"puestos"})})
    return {"respuesta": r.model_dump(mode="json"), "marcados": estado["preferencias"]["puestos"],
            "sugeridos": [x["titulo"] for x in sugeridos], "familia": r.familia}


def correr(estado: dict, prov: Proveedor | None, veces: int = 1) -> dict:
    """`veces`: pasadas del mismo CV para medir la estabilidad (RF-12.30e). La equidad no llama al modelo:
    compara las copias ciegas de las dos gemelas (RF-12.30d)."""
    pasadas = [_clasificar(estado["perfil"], prov) for _ in range(veces)]
    nombres = ["base"] + [f"base_{i}" for i in range(2, veces + 1)]
    obtenido = {**pasadas[0], "pasadas": pasadas,
                "sin_experiencia": not estado["perfil"].get("experiencias"),
                "respuestas": {n: p["respuesta"] for n, p in zip(nombres, pasadas, strict=True)}}
    if estado.get("variante"):
        otra = _variante(estado["perfil"], estado["variante"])
        obtenido["copias_iguales"] = (copia_ciega(Perfil.model_validate(estado["perfil"]))
                                      == copia_ciega(Perfil.model_validate(otra)))
    return obtenido


def _etiqueta(titulo: str, esperado: dict) -> str | None:
    por_puesto = {_canonico(t): e["final"] for t, e in esperado["etiquetas"].items()}
    return por_puesto.get(_canonico(titulo))


def _todos(obtenido: dict, campo: str) -> list[str]:
    """Lo que sale en alguna de las pasadas, sin repetir."""
    return list({_canonico(t): t for p in obtenido["pasadas"] for t in p[campo]}.values())


def _estabilidad(obtenido: dict) -> float:
    """Puestos marcados en todas las pasadas / puestos marcados en alguna (RF-12.30e)."""
    marcados = [{_canonico(t) for t in p["marcados"]} for p in obtenido["pasadas"]]
    alguna = set.union(*marcados)
    return len(set.intersection(*marcados)) / len(alguna) if alguna else 1.0


def comparar(obtenido: dict, esperado: dict) -> list[str]:
    fallos = []
    if any(_etiqueta(t, esperado) == "ajeno" for t in _todos(obtenido, "marcados")):
        fallos.append("ajenos")
    if any(_etiqueta(t, esperado) is None for t in _todos(obtenido, "sugeridos")):
        fallos.append("etiquetado")
    if obtenido.get("copias_iguales") is False:
        fallos.append("equidad")
    return fallos


def _parte(aciertos: int, total: int) -> float | None:
    return round(aciertos / total, 4) if total else None


def kappa(votos: list[list[str]]) -> float | None:
    """Kappa de Fleiss entre los etiquetadores (RF-12.3)."""
    if not votos:
        return None
    n = len(votos[0])
    categorias = {v for fila in votos for v in fila}
    observado = sum((sum(fila.count(c) ** 2 for c in categorias) - n) / (n * (n - 1))
                    for fila in votos) / len(votos)
    azar = sum((sum(fila.count(c) for fila in votos) / (n * len(votos))) ** 2 for c in categorias)
    return 1.0 if azar == 1 else round((observado - azar) / (1 - azar), 4)


def medir(casos: list[tuple[str, dict, dict]]) -> dict:
    """Métricas del set entero. `casos`: (nombre, obtenido, esperado) de los que no dieron error."""
    ajenos = marcados_ok = marcados = otros_ok = otros = cubiertos = imprescindibles = 0
    iguales = parejas = familias_ok = familias = 0
    sin_etiquetar: list[str] = []
    estables: list[float] = []
    votos: list[list[str]] = []
    for nombre, o, e in casos:
        marcadas = {_canonico(t) for t in o["marcados"]}
        sin_etiquetar += [f"{nombre}: {t}" for t in _todos(o, "sugeridos") if _etiqueta(t, e) is None]
        ajenos += sum(_etiqueta(t, e) == "ajeno" for t in _todos(o, "marcados"))
        if len(o["pasadas"]) > 1:
            estables.append(_estabilidad(o))
        for titulo in o["sugeridos"]:  # las precisiones y la cobertura, sobre la primera pasada
            etiqueta = _etiqueta(titulo, e)
            if etiqueta is None:
                continue
            if _canonico(titulo) in marcadas:
                marcados += 1
                # D-036: sin experiencia, marcar por la titulación (RF-12.7) es acertar.
                marcados_ok += etiqueta == "lo_ha_sido" or (o["sin_experiencia"] and etiqueta == "afin")
            else:
                otros += 1
                otros_ok += etiqueta != "ajeno"
        for formas in e["imprescindibles"]:
            imprescindibles += 1
            cubiertos += any(casa_con_puestos(t, formas) for t in o["sugeridos"])
        if "copias_iguales" in o:
            parejas += 1
            iguales += o["copias_iguales"]
        if e.get("familia"):
            familias += 1
            familias_ok += o["familia"] == e["familia"]
        votos += [x["votos"] for x in e["etiquetas"].values()]
    return {"ajenos_marcados": ajenos, "precision_marcados": _parte(marcados_ok, marcados),
            "precision_sin_marcar": _parte(otros_ok, otros),
            "cobertura": _parte(cubiertos, imprescindibles), "equidad": _parte(iguales, parejas),
            "estabilidad": round(sum(estables) / len(estables), 4) if estables else None,
            "familia": _parte(familias_ok, familias), "kappa": kappa(votos), "sin_etiquetar": sin_etiquetar}


def cumple(metricas: dict, umbrales: dict) -> bool:
    """`ajenos_marcados` es un máximo; el resto, mínimos. Sin nada que medir, no se exige."""
    if metricas["sin_etiquetar"] or metricas["ajenos_marcados"] > umbrales["ajenos_marcados"]:
        return False
    return all(metricas[k] is None or metricas[k] >= minimo
               for k, minimo in umbrales.items() if k != "ajenos_marcados")


def simuladas(esperado: EsperadoPuestos, datos: dict) -> list[dict]:
    """Un modelo que solo propone lo que puede llegar marcado según las etiquetas."""
    perfil = datos["perfil"]
    experiencias, formacion = perfil.get("experiencias") or [], perfil.get("formacion") or []
    quiere = "lo_ha_sido" if experiencias else "afin"
    dato = experiencias[0]["puesto"] if experiencias else (formacion[0]["titulo"] if formacion else "")
    titulos = [t for t, e in esperado.etiquetas.items() if e.final == quiere and dato]
    familia = esperado.familia or "otros"

    def respuesta(d: str) -> dict:
        puestos = []
        for t in titulos:
            puestos.append({"titulo": t, "idioma": "es", "dato": d})
        return {"sector": "otros", "familia": familia, "nivel": "sin_especificar", "stack": [],
                "puestos": puestos}

    return [respuesta(dato)]
